from flask import jsonify, render_template, request, send_file
from mysql.connector import Error as DatabaseError

from db import cursor
from document_parser import MAX_BYTES
from document_service import (DocumentError, upload_document, list_documents, get_document,
                              process_document, save_review, publish_document, stored_path, _load)
from security import require_permission, permissions


def document_request_limits():
    if request.endpoint == 'document_upload':
        request.max_content_length = MAX_BYTES + 1024 * 1024
    elif request.endpoint == 'document_review':
        request.max_content_length = 80 * 1024


def register_documents(app):
    @app.errorhandler(DocumentError)
    def rejected(error):
        return jsonify(error='document-rejected', message=str(error)), error.status

    @app.errorhandler(413)
    def oversized(error):
        return jsonify(error='file-too-large', message='Yêu cầu quá lớn. Mỗi file tối đa 10 MB; nội dung hiệu đính tối đa 60.000 byte UTF-8.'), 413

    @app.get('/documents')
    @require_permission('document:manage')
    def document_page():
        return render_template('documents.html')

    @app.get('/api/documents/lookups')
    @require_permission('document:manage')
    def document_lookups():
        with cursor() as cur:
            cur.execute('SELECT c.id,c.name,p.code FROM kb_categories c JOIN permissions p ON p.id=c.required_permission_id ORDER BY c.id')
            categories = [row for row in cur.fetchall() if row['code'] in permissions() and permissions()[row['code']]['scope'] != 'own']
            cur.execute('SELECT id,code,name FROM branches ORDER BY id')
            grant = permissions()['document:manage']
            branches = [row for row in cur.fetchall() if grant['scope'] != 'branch' or row['id'] == grant['branch']]
        return jsonify(categories=categories, branches=branches, all_branches=grant['scope'] == 'all', max_bytes=MAX_BYTES)

    @app.get('/api/documents')
    @require_permission('document:manage')
    def documents_list():
        try:
            page = max(1, min(100000, int(request.args.get('page', 1))))
        except ValueError:
            raise DocumentError('Số trang không hợp lệ.') from None
        return jsonify(list_documents(page))

    @app.post('/api/documents')
    @require_permission('document:manage')
    def document_upload():
        try:
            result = upload_document(request.files.get('file'), request.form.get('title'),
                                     request.form.get('category_id'), request.form.get('branch_id'))
        except (OSError, DatabaseError):
            raise DocumentError('Chưa lưu được tài liệu. Hãy kiểm tra nơi lưu file và kết nối database rồi thử lại.', 503) from None
        return jsonify(result), 201

    @app.get('/api/documents/<int:document_id>')
    @require_permission('document:manage')
    def document_detail(document_id):
        return jsonify(get_document(document_id))

    @app.get('/api/documents/<int:document_id>/file')
    @require_permission('document:manage')
    def document_original(document_id):
        with cursor() as cur:
            row = _load(cur, document_id)
        path = stored_path(row)
        if not path.is_file():
            raise DocumentError('File gốc không còn trong nơi lưu trữ.', 404)
        return send_file(path, as_attachment=True, download_name=row['original_name'])

    @app.post('/api/documents/<int:document_id>/process')
    @require_permission('document:manage')
    def document_process(document_id):
        return jsonify(process_document(document_id))

    @app.put('/api/documents/<int:document_id>/review')
    @require_permission('document:manage')
    def document_review(document_id):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise DocumentError('Nội dung hiệu đính không hợp lệ.')
        return jsonify(save_review(document_id, data))

    @app.post('/api/documents/<int:document_id>/publish')
    @require_permission('document:manage')
    def document_publish(document_id):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise DocumentError('Yêu cầu xuất bản không hợp lệ.')
        return jsonify(publish_document(document_id, data))
