import json  # Lưu cảnh báo trích xuất cạnh bản nháp nhập khách.
import re  # Tách header và dòng văn bản có nhãn từ nội dung tài liệu.
from flask import g  # Lấy user nhân viên sở hữu batch nhập file.
from db import cursor, transaction  # Khóa nguồn và ghi batch trong cùng transaction.
from customer_input import FIELDS, REQUIRED, MAX_ROWS, CustomerInputError, today, stage, get_batch, read_customer_workbook, normalize_row, _existing  # Dùng chung quy tắc kiểm tra và lưu khách.
from document_service import _load, stored_path  # Kiểm tra quyền tài liệu và lấy file gốc đã lưu.
from question_language import normalize  # So khớp tiêu đề cột dù người nhập dùng dấu khác nhau.
from security import permissions  # Chặn nhập file khi thiếu quyền khách hàng/tài liệu.


def header_key(value):
    label=normalize(str(value or ''))
    label=re.sub(r'\s*\*\s*$','',label)
    aliases={normalize(v):k for k,v in FIELDS.items()}
    aliases.update({'ho ten':'full_name','ten khach hang':'full_name','sdt':'phone','dien thoai':'phone',
                    'ma khach hang':'customer_code','ma sp da mua':'purchased_sku','ma san pham':'purchased_sku',
                    'gia tri mua':'purchase_amount','chi nhanh':'branch_code','ngay dang ky':'registered_at'})
    return aliases.get(label)


# Chuẩn hóa đầu vào trong bước extracted_rows để các phép so khớp phía sau dùng cùng một dạng.
def extracted_rows(extraction,branch_code=None):
    output=[];warnings=[]
    mapping=None
    for block in extraction.get('blocks',[]):
        if block.get('kind')!='table':continue
        for cells in block.get('rows',[]):
            keys=[header_key(c) for c in cells]
            if 'full_name' in keys and ('phone' in keys or 'email' in keys):
                populated=[k for k in keys if k]
                if len(populated)!=len(set(populated)):raise CustomerInputError('Bảng khách có tiêu đề cột trùng.')
                mapping=keys;continue
            if mapping is None or not any(str(c or '').strip() for c in cells):continue
            if len(cells)!=len(mapping):
                raise CustomerInputError('Bảng có số cột không khớp tiêu đề; cần sửa/đối chiếu file trước khi đồng bộ.')
            row={key:str(value or '').strip() for key,value in zip(mapping,cells) if key}
            row['_source_columns']=list(row)
            if not any(row.get(k) for k in ('full_name','phone','email')):continue
            output.append(row)
    if not output:
        # Hỗ trợ khối có nhãn; không suy diễn cột từ văn bản PDF mất cấu trúc.
        from customer_chat import parse_customer_values  # Phân tích thông tin khách gửi qua chat.
        current={}
        for block in extraction.get('blocks',[]):
            if block.get('kind')!='text':continue
            for line in block.get('text','').splitlines():
                values=parse_customer_values(line)
                if values.get('full_name') and current.get('full_name'):
                    output.append(current);current={}
                current.update(values)
        if current:output.append(current)
    if not output:raise CustomerInputError('Không nhận diện được danh sách khách. PDF cần lớp văn bản/bảng rõ ràng; bản scan cần OCR hoặc nhập thủ công. Dùng cột Họ và tên, Số điện thoại, Email, Chi nhánh.')
    if len(output)>MAX_ROWS:raise CustomerInputError(f'Mỗi lần đồng bộ tối đa {MAX_ROWS} khách hàng.')
    for row in output:
        row.setdefault('_source_columns',list(row))
        if not row.get('registered_at'):row['registered_at']=today().isoformat();warnings.append('Ngày đăng ký trống được đặt là ngày nhập hiện tại.')
        if not row.get('status'):row['status']='Tiềm năng';warnings.append('Trạng thái trống được đặt là Tiềm năng.')
        if not row.get('branch_code') and branch_code:row['branch_code']=branch_code;warnings.append('Chi nhánh trống lấy từ phạm vi file/người nhập.')
    warnings.extend(extraction.get('quality',{}).get('warnings',[]))
    return output,list(dict.fromkeys(warnings))


# Chỉ nhân viên có quyền đọc/ghi được staging danh sách khách từ tài liệu đã trích xuất.
def stage_document(document_id,chat_session_id=None):
    if not g.user or g.user['user_type']!='staff' or not {'customer:write','document:manage'}<=permissions().keys():
        raise CustomerInputError('Bạn không có quyền thực hiện yêu cầu này.',403)
    with transaction():
        with cursor() as cur:
            document=_load(cur,document_id,True)
            if document['category_code']!='customers':raise CustomerInputError('Chọn danh mục Thông tin / Danh sách khách hàng.')
            cur.execute("SELECT cb.id,cb.status FROM customer_input_batches cb JOIN customer_import_sources s ON s.batch_id=cb.id WHERE cb.document_id=%s AND cb.created_by=%s AND cb.status IN ('draft','committed') AND s.document_version=%s ORDER BY cb.id DESC LIMIT 1",(document_id,g.user['id'],document['version']))
            existing=cur.fetchone()
            if existing:
                if chat_session_id is not None and existing['status']=='draft':
                    cur.execute('UPDATE customer_input_batches SET chat_session_id=%s WHERE id=%s',(chat_session_id,existing['id']))
                return get_batch(existing['id'])
            if document['status'] not in {'ready','needs_review'} or not document.get('result_json'):
                raise CustomerInputError('File chưa trích xuất thành công; hãy kiểm tra file gốc hoặc nhập thủ công.')
            extraction=json.loads(document['result_json'])
            branch=document['branch_code']
            grant=permissions()['customer:write']
            if not branch and grant['scope']=='branch':
                cur.execute('SELECT code FROM branches WHERE id=%s',(grant['branch'],));branch=cur.fetchone()['code']
        if document['file_format']=='xlsx':
            try:rows=read_customer_workbook(stored_path(document));warnings=[]
            except CustomerInputError as error:
                if 'sheet Khach_hang' not in str(error) and 'File thiếu cột bắt buộc:' not in str(error):raise
                rows,warnings=extracted_rows(extraction,branch)
        else:rows,warnings=extracted_rows(extraction,branch)
        # Không xóa thông tin đã có chỉ vì file cập nhật không có cột đó.
        with cursor() as cur:
            for row in rows:
                provided=set(row.pop('_source_columns',row.keys()))
                canonical,_=normalize_row(row)
                try:existing=_existing(cur,canonical)
                except ValueError as error:raise CustomerInputError(str(error)) from None
                if existing:
                    for key in FIELDS:
                        if key not in provided and key in existing:row[key]=existing[key] if existing[key] is not None else ''
        batch=stage(rows,document_id=document_id,chat_session_id=chat_session_id)
        with cursor() as cur:
            cur.execute('INSERT INTO customer_import_sources(batch_id,document_version,warnings_json) VALUES(%s,%s,%s)',(batch['id'],document['version'],json.dumps(warnings,ensure_ascii=False)))
        return get_batch(batch['id'])
