# File này quản lý file, metadata, duyệt và phân quyền tài liệu.
from __future__ import annotations

import hashlib  # Tính SHA-256 và kích thước file nhận tải lên.
import json  # Lưu kết quả parser và payload danh sách khách dưới dạng JSON.
import subprocess  # Chạy parser trong tiến trình riêng với timeout.
import sys  # Dùng đúng trình thông dịch Python hiện tại cho subprocess.
import uuid  # Tạo tên file lưu trữ không trùng với tên người dùng.
from pathlib import Path  # Tạo, kiểm tra và bảo vệ đường dẫn file tài liệu.

from flask import current_app, g  # Tạo request, response hoặc client Flask.

from db import cursor  # Mở cursor hoặc connection MySQL.
from dashboard_service import scope_filter  # Dùng truy vấn widget và scope quyền.
from document_parser import MAX_BYTES, ParseError, clean, validate_file  # Dùng parser và giới hạn xử lý file.
from security import permissions, audit  # Dùng xác thực, permission hoặc audit của backend.


# Lỗi nghiệp vụ tài liệu mang HTTP status để route phản hồi đúng mã.
class DocumentError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def storage_root():
    # Dùng thư mục cấu hình hoặc instance/documents và tạo nếu chưa có.
    root = Path(current_app.config.get('DOCUMENT_STORAGE', Path(current_app.instance_path) / 'documents')).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def stored_path(row):
    root = storage_root()
    path = (root / row['stored_name']).resolve()
    if path.parent != root:
        raise DocumentError('Không tìm thấy tài liệu trong phạm vi được xem.', 404)
    return path


# Xác thực tiêu đề, danh mục, permission danh mục và scope chi nhánh.
def check_metadata(title, category_id, branch_id):
    if not isinstance(title, str) or not 1 <= len(clean(title)) <= 255:
        raise DocumentError('Tiêu đề bắt buộc, tối đa 255 ký tự.')
    try:
        category_id = int(category_id)
        branch_id = int(branch_id) if branch_id not in (None, '') else None
    except (TypeError, ValueError):
        raise DocumentError('Danh mục hoặc chi nhánh không hợp lệ.') from None
    with cursor() as cur:
        cur.execute('SELECT p.code FROM kb_categories c JOIN permissions p ON p.id=c.required_permission_id WHERE c.id=%s', (category_id,))
        category = cur.fetchone()
        if not category or category['code'] not in permissions():
            raise DocumentError('Bạn không được sử dụng danh mục này.', 403)
        management = permissions()['document:manage']
        for grant in (management, permissions()[category['code']]):
            if grant['scope'] == 'branch':
                if branch_id is None:
                    branch_id = grant['branch']
                if branch_id != grant['branch']:
                    raise DocumentError('Chi nhánh nằm ngoài phạm vi được cấp.', 403)
            elif grant['scope'] == 'own' and grant is not management:
                raise DocumentError('Quyền danh mục chưa đủ để quản lý tài liệu.', 403)
        if branch_id is not None:
            cur.execute('SELECT id FROM branches WHERE id=%s', (branch_id,))
            if not cur.fetchone():
                raise DocumentError('Chi nhánh không hợp lệ.')
    return clean(title), category_id, branch_id


def _scope():
    where, params = scope_filter('document:manage', 'd.branch_id', 'd.uploaded_by')
    codes = tuple(code for code, grant in permissions().items() if grant['scope'] != 'own')
    if not codes:
        return '1=0', ()
    return where + ' AND p.code IN (' + ','.join('%s' for _ in codes) + ')', (*params, *codes)


def _load(cur, document_id, lock=False):
    # Lấy file trong scope quản lý rồi kiểm tra lại quyền đọc của danh mục.
    where, params = _scope()
    cur.execute("SELECT d.*,c.name AS category_name,c.code AS category_code,b.code AS branch_code,EXISTS(SELECT 1 FROM customer_input_batches cb WHERE cb.document_id=d.id AND cb.status='committed') AS customer_synced FROM document_uploads d "
                'JOIN kb_categories c ON c.id=d.category_id JOIN permissions p ON p.id=c.required_permission_id '
                'LEFT JOIN branches b ON b.id=d.branch_id WHERE d.id=%s AND ' + where
                + (' FOR UPDATE' if lock else ''), (document_id, *params))
    row = cur.fetchone()
    if not row:
        raise DocumentError('Không tìm thấy tài liệu trong phạm vi được xem.', 404)
    # Kiểm tra lại scope của quyền đọc danh mục, không chỉ quyền quản lý.
    _, _, authorized_branch = check_metadata(row['title'], row['category_id'], row['branch_id'])
    if authorized_branch != row['branch_id']:
        raise DocumentError('Không tìm thấy tài liệu trong phạm vi được xem.', 404)
    return row


def public_row(row, detail=False):
    keys = ('id', 'title', 'original_name', 'file_format', 'size_bytes', 'sha256', 'status',
            'category_id', 'category_name', 'category_code', 'customer_synced', 'branch_id', 'branch_code', 'created_at', 'updated_at',
            'error_code', 'error_message', 'reviewed_at', 'published_doc_id', 'version')
    result = {key: row.get(key) for key in keys}
    if detail:
        result['extraction'] = json.loads(row['result_json']) if row.get('result_json') else None
        result['review_content'] = row.get('review_content')
        result['review_notes'] = row.get('review_notes')
    return result


# Đếm và phân trang file theo quyền danh mục, chi nhánh và người tải lên.
def list_documents(page=1):
    where, params = _scope()
    # Một quyền quản lý toàn hệ thống không được mở rộng scope danh mục.
    category_filters = []
    category_params = []
    for code, grant in permissions().items():
        if grant['scope'] == 'all':
            category_filters.append('p.code=%s'); category_params.append(code)
        elif grant['scope'] == 'branch':
            category_filters.append('(p.code=%s AND d.branch_id=%s)'); category_params.extend((code, grant['branch']))
    where += ' AND (' + ' OR '.join(category_filters or ['1=0']) + ')'
    source = (' FROM document_uploads d JOIN kb_categories c ON c.id=d.category_id '
              'JOIN permissions p ON p.id=c.required_permission_id LEFT JOIN branches b ON b.id=d.branch_id WHERE ')
    with cursor() as cur:
        cur.execute('SELECT COUNT(*) AS n' + source + where, (*params, *category_params))
        total = cur.fetchone()['n']
        cur.execute("SELECT d.*,c.name AS category_name,c.code AS category_code,b.code AS branch_code,EXISTS(SELECT 1 FROM customer_input_batches cb WHERE cb.document_id=d.id AND cb.status='committed') AS customer_synced" + source + where
                    + ' ORDER BY d.id DESC LIMIT %s OFFSET %s', (*params, *category_params, 25, (page - 1) * 25))
        rows = [public_row(row) for row in cur.fetchall()]
    return {'rows': rows, 'total': total, 'page': page, 'size': 25}


# Trả metadata chi tiết qua bộ lọc trường công khai trước khi gửi route.
def get_document(document_id):
    with cursor() as cur:
        return public_row(_load(cur, document_id), True)


def upload_document(file, title, category_id, branch_id):
    # Ghi file theo tên ngẫu nhiên, xác thực định dạng rồi mới lưu metadata vào CSDL.
    title, category_id, branch_id = check_metadata(title, category_id, branch_id)
    if file is None or not file.filename:
        raise DocumentError('Vui lòng chọn file để tải lên.')
    name = clean(file.filename.replace('\\', '/').split('/')[-1])
    if not name or len(name) > 255:
        raise DocumentError('Tên file không hợp lệ hoặc dài quá 255 ký tự.')
    file_format = Path(name).suffix.lower().lstrip('.')
    if file_format not in {'pdf', 'docx', 'xlsx'}:
        raise DocumentError('Chỉ hỗ trợ PDF có văn bản, DOCX và XLSX. Không nhận DOC/XLS cũ hoặc file ảnh.')
    path = storage_root() / (uuid.uuid4().hex + '.' + file_format)
    digest, size, inserted = hashlib.sha256(), 0, False
    try:
        with path.open('xb') as output:
            while chunk := file.stream.read(64 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise DocumentError('File vượt giới hạn 10 MB.', 413)
                output.write(chunk); digest.update(chunk)
        validate_file(path, file_format)
        with cursor() as cur:
            cur.execute('''INSERT INTO document_uploads(uploaded_by,category_id,branch_id,title,original_name,
                           stored_name,file_format,size_bytes,sha256) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                        (g.user['id'], category_id, branch_id, title, name, path.name, file_format, size, digest.hexdigest()))
            document_id = cur.lastrowid
            audit(cur, 'document_uploaded', 'document', document_id, after={'name': name, 'size': size}, actor=g.user['id'])
        inserted = True
        return process_document(document_id)
    except ParseError as error:
        raise DocumentError(str(error)) from None
    finally:
        if not inserted:
            path.unlink(missing_ok=True)


def process_document(document_id):
    # Khóa file, đổi trạng thái processing, chạy parser có timeout rồi lưu kết quả.
    with cursor() as cur:
        row = _load(cur, document_id, True)
        stale = False
        if row['status'] == 'processing':
            cur.execute('SELECT processing_started_at < DATE_SUB(NOW(), INTERVAL 120 SECOND) AS stale FROM document_uploads WHERE id=%s', (document_id,))
            stale = bool(cur.fetchone()['stale'])
        if row['status'] not in {'uploaded', 'failed'} and not stale:
            raise DocumentError('Tài liệu đang xử lý hoặc đã được trích xuất; hãy tải file mới nếu cần thay thế.', 409)
        cur.execute("UPDATE document_uploads SET status='processing',processing_started_at=NOW(),error_code=NULL,error_message=NULL WHERE id=%s", (document_id,))
    code = message = None
    extraction = None
    try:
        completed = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).with_name('document_parser.py')),
                                    str(stored_path(row)), row['file_format']], capture_output=True, encoding='utf-8',
                                   timeout=current_app.config.get('DOCUMENT_PARSE_TIMEOUT', 45), check=False)
        payload = json.loads(completed.stdout) if completed.returncode == 0 else {}
        if payload.get('ok'):
            extraction = payload['result']
        else:
            code, message = payload.get('code', 'parser_failed'), payload.get('message', 'Không hoàn tất trích xuất. Hãy kiểm tra file hoặc thử lại.')
    except subprocess.TimeoutExpired:
        code, message = 'processing_timeout', 'Trích xuất quá 45 giây. Hãy chia nhỏ tài liệu rồi tải lại.'
    except Exception:
        code, message = 'parser_failed', 'Không hoàn tất trích xuất. Hãy kiểm tra file hoặc thử lại.'
    status = 'failed' if extraction is None else 'needs_review' if extraction['quality']['state'] == 'needs_review' else 'ready'
    with cursor() as cur:
        cur.execute('''UPDATE document_uploads SET status=%s,result_json=%s,error_code=%s,error_message=%s,
                       review_content=NULL,reviewed_by=NULL,reviewed_at=NULL,version=version+1 WHERE id=%s''',
                    (status, json.dumps(extraction, ensure_ascii=False) if extraction else None, code, message, document_id))
        audit(cur, 'document_processed', 'document', document_id, after={'status': status, 'error_code': code}, actor=g.user['id'])
    return get_document(document_id)


# Không nhận nội dung rỗng, quá lớn hoặc còn placeholder công thức/ô lỗi.
def validate_review_content(content):
    if not isinstance(content, str) or not clean(content) or len(clean(content).encode('utf-8')) > 60000:
        raise DocumentError('Nội dung bắt buộc, không rỗng và tối đa 60.000 byte UTF-8 để lưu vào kho tri thức.')
    if any(marker in content for marker in ('[Chưa có kết quả công thức]', '[Ô có lỗi]')):
        raise DocumentError('Nội dung còn ô thiếu kết quả công thức hoặc ô lỗi. Cần sửa hoặc loại bỏ phần không hợp lệ và ghi chú trước khi lưu.')
    return clean(content)


# Lưu nội dung đã đối chiếu theo version; danh sách khách đi qua luồng nhập riêng.
def save_review(document_id, data):
    content = validate_review_content(data.get('content'))
    if data.get('confirmed') is not True:
        raise DocumentError('Bạn cần xác nhận đã đối chiếu nội dung, các ô bảng và cảnh báo với file gốc.')
    notes = data.get('notes', '')
    if not isinstance(notes, str) or len(notes) > 2000:
        raise DocumentError('Ghi chú hiệu đính tối đa 2.000 ký tự.')
    with cursor() as cur:
        row = _load(cur, document_id, True)
        if row['category_code']=='customers':
            raise DocumentError('Dùng luồng kiểm tra và đồng bộ khách hàng để hiệu đính danh sách này.')
        if row['status'] not in {'ready', 'needs_review'} or data.get('version') != row['version']:
            raise DocumentError('Bản nháp đã thay đổi hoặc không thể hiệu đính. Hãy tải lại tài liệu.', 409)
        title, _, _ = check_metadata(data.get('title'), row['category_id'], row['branch_id'])
        if row['status'] == 'needs_review' and not clean(notes):
            raise DocumentError('Tài liệu có phần thiếu/không chắc chắn; cần ghi chú cách kiểm tra hoặc bổ sung nội dung.')
        cur.execute("UPDATE document_uploads SET title=%s,review_content=%s,review_notes=%s,reviewed_by=%s,reviewed_at=NOW(),status='ready',version=version+1 WHERE id=%s",
                    (title, clean(content), clean(notes), g.user['id'], document_id))
        audit(cur, 'document_reviewed', 'document', document_id, after={'corrected': True}, actor=g.user['id'])
    return get_document(document_id)


def publish_document(document_id, data):
    with cursor() as cur:
        row = _load(cur, document_id, True)
        if row['category_code']=='customers':
            raise DocumentError('Dùng luồng kiểm tra và đồng bộ khách hàng; danh sách khách hàng không đưa vào kho tri thức.')
        if row['status'] != 'ready' or not row['reviewed_at'] or not row['review_content'] or data.get('version') != row['version']:
            raise DocumentError('Chỉ xuất bản bản đã hiệu đính và xác nhận; hãy tải lại nếu bản nháp đã thay đổi.', 409)
        title, category_id, branch_id = check_metadata(row['title'], row['category_id'], row['branch_id'])
        content = validate_review_content(row['review_content'])
        cur.execute('INSERT INTO kb_documents(category_id,branch_id,title,content) VALUES(%s,%s,%s,%s)', (category_id, branch_id, title, content))
        published_id = cur.lastrowid
        cur.execute("UPDATE document_uploads SET status='published',published_doc_id=%s,version=version+1 WHERE id=%s", (published_id, document_id))
        audit(cur, 'document_published', 'document', document_id, after={'kb_document_id': published_id}, actor=g.user['id'])
    return get_document(document_id)
