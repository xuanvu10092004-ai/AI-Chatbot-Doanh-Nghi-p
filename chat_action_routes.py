from flask import g,jsonify,request,session
from db import cursor
from security import require_permission
from access_control import create_session,resume_session,record_message
from customer_file_import import stage_document
from customer_input import CustomerInputError
from document_service import upload_document
from chat_tools import staff,available_tools
from dashboard_service import scope_filter


def register_chat_actions(app):
    @app.get('/api/chat/tools')
    @require_permission('kb:public:read')
    def chat_tools_list():
        return jsonify(mode='staff' if staff() else 'customer',tools=[{'name':name,'description':spec[0],'requires_confirmation':spec[3],'fields':spec[4].split()} for name,spec in available_tools().items()])

    @app.post('/api/chat/customer-file')
    @require_permission('customer:write','document:manage')
    def chat_customer_upload():
        if not staff():raise CustomerInputError('Bạn không có quyền thực hiện yêu cầu này.',403)
        chat_id=session.get('chat_session_id')
        if chat_id is None or not resume_session(chat_id,g.user['id']):
            chat_id=create_session(g.user['id']);session['chat_session_id']=chat_id
        with cursor() as cur:cur.execute("SELECT id FROM kb_categories WHERE code='customers'");category=cur.fetchone()['id']
        file=request.files.get('file')
        title=request.form.get('title') or 'Danh sách khách hàng qua chat'
        document=upload_document(file,title,category,request.form.get('branch_id'))
        record_message(chat_id,'user','Đã tải file danh sách khách hàng #'+str(document['id']))
        batch=stage_document(document['id'],chat_id)
        message='Đã đọc '+str(len(batch['rows']))+' dòng khách hàng. Chưa ghi CSDL; hãy kiểm tra và xác nhận lưu.'
        record_message(chat_id,'bot',message)
        return jsonify(type='customer-input',answer=message,customer_draft=batch,document_id=document['id'],session_id=chat_id,rows=[]),201

    @app.get('/api/customer-imports')
    @require_permission('customer:read')
    def customer_import_history():
        where,params=scope_filter('customer:read','u.home_branch_id','u.id')
        with cursor() as cur:
            cur.execute('''SELECT cb.id,du.title,du.original_name,du.file_format,cb.updated_at,
                        COUNT(*) AS customer_count,SUM(cir.action='create') AS created,SUM(cir.action='update') AS updated
                        FROM customer_input_batches cb JOIN document_uploads du ON du.id=cb.document_id
                        JOIN customer_import_rows cir ON cir.batch_id=cb.id JOIN users u ON u.id=cir.customer_id
                        WHERE cb.status='committed' AND '''+where+''' GROUP BY cb.id,du.title,du.original_name,du.file_format,cb.updated_at
                        ORDER BY cb.updated_at DESC,cb.id DESC LIMIT 100''',params)
            return jsonify(rows=cur.fetchall())

    @app.get('/api/appointments')
    @require_permission('booking:read')
    def appointments_list():
        from appointment_service import list_appointments
        return jsonify(rows=list_appointments())

    @app.patch('/api/appointments/<int:target_id>')
    @require_permission('booking:read')
    def appointments_update(target_id):
        from appointment_service import update_appointment
        from operations_routes import OperationRejected
        data=request.get_json(silent=True)
        if not isinstance(data,dict):raise OperationRejected('Dữ liệu không hợp lệ.')
        return jsonify(update_appointment({**data,'id':target_id},session.get('chat_session_id')))
