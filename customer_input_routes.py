from flask import jsonify, render_template, request, send_file
from io import BytesIO
from mysql.connector import IntegrityError
from db import cursor
from security import require_permission, permissions
from customer_input import (CustomerInputError,FIELDS,REQUIRED,WORKBOOK_HEADERS,MAX_ROWS,stage,get_batch,revise,commit,read_customer_workbook)
from document_service import _load,stored_path
from customer_file_import import stage_document


def register_customer_input(app):
    @app.errorhandler(CustomerInputError)
    def invalid(error):return jsonify(error='customer-input-rejected',message=str(error)),error.status

    @app.get('/customer-input')
    @require_permission('customer:write')
    def customer_input_page():return render_template('customer_input.html')

    @app.get('/api/customer-input/template')
    @require_permission('customer:write')
    def customer_input_template():
        from openpyxl import Workbook
        book=Workbook();sheet=book.active;sheet.title='Khach_hang';sheet.append(WORKBOOK_HEADERS)
        sheet.freeze_panes='A2';sheet.auto_filter.ref=f'A1:S{MAX_ROWS+1}'
        for number in range(2,MAX_ROWS+2):sheet.cell(number,6).number_format='@'
        guide=book.create_sheet('Huong_dan')
        for text in [f'Dữ liệu mô phỏng. Mỗi lần nhập tối đa {MAX_ROWS} khách hàng.',
                     'Bắt buộc: Họ và tên, Số điện thoại, Email, Chi nhánh phụ trách, Ngày đăng ký, Trạng thái.',
                     'Giữ số 0 đầu điện thoại. Ngày dạng dd/MM/yyyy. Tuổi tự tính, không nhập vào CSDL.',
                     'Đã mua: điền Mã SP đã mua (SP001…) và Giá trị mua (số nguyên VNĐ).',
                     'Một dòng mô tả một khách và tối đa một lần mua, số lượng 1. Đơn mới chờ duyệt.',
                     'Xem trước và xác nhận cập nhật hồ sơ; email/mã KH nhận diện bản ghi hiện có.']:guide.append([text])
        output=BytesIO();book.save(output);output.seek(0)
        return send_file(output,as_attachment=True,download_name='mau_danh_sach_khach_hang.xlsx')

    @app.get('/api/customer-input/lookups')
    @require_permission('customer:write')
    def customer_input_lookups():
        grant=permissions()['customer:write']
        with cursor() as cur:
            cur.execute('SELECT id,code FROM branches ORDER BY id');branches=[r for r in cur.fetchall() if grant['scope']=='all' or grant['scope']=='branch' and r['id']==grant['branch']]
            cur.execute('SELECT model_name FROM products ORDER BY model_name');models=[r['model_name'] for r in cur.fetchall()]
            cur.execute('SELECT id,variant_name,list_price FROM product_variants ORDER BY id');variants=[{'sku':f"SP{r['id']:03d}",'name':r['variant_name'],'list_price':r['list_price']} for r in cur.fetchall()]
        return jsonify(fields=FIELDS,required=REQUIRED,branches=branches,models=models,variants=variants,can_export_invoice='invoice:export' in permissions())

    @app.post('/api/customer-input')
    @require_permission('customer:write')
    def customer_input_stage():
        data=request.get_json(silent=True)
        if not isinstance(data,dict):raise CustomerInputError('Dữ liệu không hợp lệ.')
        if 'document_id' in data:
            return jsonify(stage_document(data['document_id'])),201
        return jsonify(stage(data.get('rows'))),201

    @app.get('/api/customer-input/<int:batch_id>')
    @require_permission('customer:write')
    def customer_input_detail(batch_id):return jsonify(get_batch(batch_id))

    @app.put('/api/customer-input/<int:batch_id>')
    @require_permission('customer:write')
    def customer_input_revise(batch_id):
        data=request.get_json(silent=True)
        if not isinstance(data,dict):raise CustomerInputError('Dữ liệu không hợp lệ.')
        return jsonify(revise(batch_id,data.get('rows'),data.get('version')))

    @app.post('/api/customer-input/<int:batch_id>/commit')
    @require_permission('customer:write')
    def customer_input_commit(batch_id):
        data=request.get_json(silent=True)
        if not isinstance(data,dict):raise CustomerInputError('Yêu cầu xác nhận không hợp lệ.')
        try:return jsonify(commit(batch_id,data.get('version'),data.get('confirmed')))
        except IntegrityError:raise CustomerInputError('Dữ liệu bị xung đột. Chưa lưu thay đổi; hãy kiểm tra lại bản nháp.',409) from None
