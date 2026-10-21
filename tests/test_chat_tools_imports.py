"""MySQL thật: công cụ chat, nhập kho, phân luồng và nhập ba định dạng khách hàng."""
import json  # Đọc hoặc ghi dữ liệu JSON trong luồng xử lý của file.
from io import BytesIO  # Tạo stream trong bộ nhớ cho upload hoặc PDF.
from datetime import datetime,timedelta  # Tạo, so sánh hoặc định dạng ngày giờ.
from pathlib import Path  # Tạo và kiểm tra đường dẫn file trong dự án.
from zoneinfo import ZoneInfo  # Tính thời gian theo múi giờ Việt Nam.
import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.
from db import cursor  # Mở cursor hoặc connection MySQL.
from test_customer_input import clean_customer_input,BATCHES  # Dùng fixture và helper tạo/dọn batch nhập khách.
from test_document_uploads import document_storage  # Dùng fixture lưu trữ và helper upload tài liệu.


@pytest.fixture(autouse=True)
def no_live_model(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    monkeypatch.setenv('APP_ENV','dev')


@pytest.fixture
def tool_cleanup():
    with cursor() as cur:
        cur.execute('SELECT branch_id,variant_id,quantity FROM inventory');inventory=cur.fetchall()
        cur.execute('SELECT MAX(id) AS id FROM stock_receipts');receipt_max=cur.fetchone()['id'] or 0
        cur.execute('SELECT MAX(id) AS id FROM chat_action_drafts');action_max=cur.fetchone()['id'] or 0
        cur.execute('SELECT MAX(id) AS id FROM appointment_requests');appointment_max=cur.fetchone()['id'] or 0
    yield
    with cursor() as cur:
        cur.execute("DELETE FROM rbac_audit_log WHERE target_type='stock_receipt' AND target_id>%s",(receipt_max,))
        cur.execute('DELETE FROM stock_receipt_items WHERE receipt_id>%s',(receipt_max,));cur.execute('DELETE FROM stock_receipts WHERE id>%s',(receipt_max,))
        cur.execute('DELETE FROM chat_action_drafts WHERE id>%s',(action_max,))
        cur.execute("DELETE FROM rbac_audit_log WHERE target_type='appointment' AND target_id>%s",(appointment_max,))
        cur.execute('DELETE FROM appointment_requests WHERE id>%s',(appointment_max,))
        for row in inventory:cur.execute('UPDATE inventory SET quantity=%s WHERE branch_id=%s AND variant_id=%s',(row['quantity'],row['branch_id'],row['variant_id']))


def chat(client,question,**extra):
    response=client.post('/chat',json={'question':question,**extra})
    assert response.status_code==200,response.get_json()
    return response.get_json()


def command(client,title,data):return chat(client,title+': '+json.dumps(data,ensure_ascii=False))


def confirm(client,reply,**extra):
    draft=reply['action_draft']
    return chat(client,'Xác nhận lệnh '+str(draft['id']),action_id=draft['id'],action_version=draft['version'],**extra)


def test_receive_chat_preview_atomic_confirm_and_replay(auth_client,tool_cleanup):
    auth_client.login(2)
    with cursor() as cur:cur.execute('SELECT quantity FROM inventory WHERE branch_id=1 AND variant_id=14');before=cur.fetchone()['quantity']
    draft=chat(auth_client,'Nhập hàng: Nhà cung cấp: Kho kiểm thử; Mã chứng từ: TOOL-RECEIVE-001; Mã SP: SP014; Số lượng: 3')
    assert draft['action_draft']['arguments']['branch_id']==1
    with cursor() as cur:cur.execute('SELECT quantity FROM inventory WHERE branch_id=1 AND variant_id=14');assert cur.fetchone()['quantity']==before
    result=confirm(auth_client,draft);assert result['result']['received_quantity']==3
    assert confirm(auth_client,draft)['result']==result['result']
    with cursor() as cur:
        cur.execute('SELECT quantity FROM inventory WHERE branch_id=1 AND variant_id=14');assert cur.fetchone()['quantity']==before+3
        cur.execute('SELECT COUNT(*) AS n FROM stock_receipts WHERE reference_code=%s',('TOOL-RECEIVE-001',));assert cur.fetchone()['n']==1
        cur.execute("SELECT COUNT(*) AS n FROM chatbot_audit_log WHERE session_id=%s AND decision='allowed'",(draft['session_id'],));assert cur.fetchone()['n']>=2


def test_multi_variant_receipt_does_not_drop_any_requested_sku(auth_client,tool_cleanup):
    auth_client.login(2)
    reply=chat(auth_client,'Nhập hàng: Nhà cung cấp: Kho kiểm thử; SP014: 3; SP015: 2')
    assert reply['action_draft']['arguments']['items']==[{'variant_id':14,'quantity':3},{'variant_id':15,'quantity':2}]
    result=confirm(auth_client,reply)
    with cursor() as cur:
        cur.execute('SELECT variant_id,quantity FROM stock_receipt_items WHERE receipt_id=%s ORDER BY variant_id',(result['result']['id'],))
        assert cur.fetchall()==[{'variant_id':14,'quantity':3},{'variant_id':15,'quantity':2}]


def test_receipt_api_scope_duplicates_and_all_or_nothing(auth_client,tool_cleanup):
    auth_client.login(2)
    data=dict(branch_id=1,supplier='Kho kiểm thử',reference_code='API-RECEIVE-001',confirmed=True,items=[{'variant_id':14,'quantity':2},{'variant_id':15,'quantity':4}])
    assert auth_client.post('/api/stock-receipts',json={**data,'confirmed':False}).status_code==400
    assert auth_client.post('/api/stock-receipts',json={**data,'branch_id':2}).status_code==403
    assert auth_client.post('/api/stock-receipts',json=data).status_code==201
    assert auth_client.post('/api/stock-receipts',json=data).status_code==409
    with cursor() as cur:cur.execute('SELECT quantity FROM inventory WHERE branch_id=1 AND variant_id=14');before=cur.fetchone()['quantity']
    bad={**data,'reference_code':'BAD-RECEIVE','items':[{'variant_id':14,'quantity':8},{'variant_id':999999,'quantity':1}]}
    assert auth_client.post('/api/stock-receipts',json=bad).status_code==400
    with cursor() as cur:
        cur.execute('SELECT quantity FROM inventory WHERE branch_id=1 AND variant_id=14');assert cur.fetchone()['quantity']==before
        cur.execute('SELECT COUNT(*) AS n FROM stock_receipts WHERE reference_code=%s',('BAD-RECEIVE',));assert cur.fetchone()['n']==0
    assert all(r['branch_code']=='NT01' for r in auth_client.get('/api/stock-receipts').json['rows'])


def test_confirm_transaction_rolls_back_and_preserves_draft(auth_client,tool_cleanup):
    auth_client.login(2)
    with cursor() as cur:cur.execute('SELECT quantity FROM inventory WHERE branch_id=1 AND variant_id=14');before=cur.fetchone()['quantity']
    draft=command(auth_client,'Nhập hàng',dict(branch_id=1,supplier='Kho kiểm thử',reference_code='ROLLBACK-RECEIVE',items=[{'variant_id':14,'quantity':10},{'variant_id':999999,'quantity':1}]))
    result=confirm(auth_client,draft);assert 'không hợp lệ' in result['answer']
    with cursor() as cur:
        cur.execute('SELECT quantity FROM inventory WHERE branch_id=1 AND variant_id=14');assert cur.fetchone()['quantity']==before
        cur.execute('SELECT status FROM chat_action_drafts WHERE id=%s',(draft['action_draft']['id'],));assert cur.fetchone()['status']=='draft'


@pytest.mark.parametrize('user',[None,8,3,5])
def test_restricted_people_cannot_receive_or_impersonate(auth_client,tool_cleanup,user):
    auth_client.login(user)
    result=chat(auth_client,'Nhập hàng: Chi nhánh: NT01; Nhà cung cấp: Kho kiểm thử; Mã SP: SP014; Số lượng: 3',user_id=1)
    assert result['access_denied']
    with cursor() as cur:
        cur.execute('SELECT decision FROM chatbot_audit_log WHERE session_id=%s ORDER BY id DESC LIMIT 1',(result['session_id'],));assert cur.fetchone()['decision']=='denied'
    assert auth_client.post('/api/stock-receipts',json={'confirmed':True}).status_code==403


def test_permission_revocation_after_preview_and_other_session(auth_client,tool_cleanup):
    auth_client.login(2)
    draft=command(auth_client,'Nhập hàng',dict(branch_id=1,supplier='Kho kiểm thử',items=[{'variant_id':14,'quantity':1}]))
    other=auth_client.__class__(auth_client.application);other.login(1)
    assert confirm(other,draft)['access_denied']
    with cursor() as cur:
        cur.execute("SELECT rp.permission_id,rp.data_scope FROM role_permissions rp JOIN permissions p ON p.id=rp.permission_id WHERE rp.role_id=2 AND p.code='inventory:receive'");grant=cur.fetchone()
        cur.execute('DELETE FROM role_permissions WHERE role_id=2 AND permission_id=%s',(grant['permission_id'],))
    try:assert confirm(auth_client,draft)['access_denied']
    finally:
        with cursor() as cur:cur.execute('INSERT INTO role_permissions(role_id,permission_id,data_scope) VALUES(2,%s,%s)',(grant['permission_id'],grant['data_scope']))


@pytest.mark.parametrize('user',[None,8])
def test_guests_and_customers_book_consultation_in_chat(auth_client,tool_cleanup,user):
    auth_client.login(user)
    day=(datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))+timedelta(days=12)).replace(hour=10,minute=0,second=0,microsecond=0,tzinfo=None)
    draft=command(auth_client,'Đặt lịch tư vấn',dict(branch_code='NT01',full_name='Khách kiểm thử',phone='0901234567',scheduled_at=day.isoformat()))
    assert 'action_draft' in draft,draft
    out=confirm(auth_client,draft);assert out['result']['status']=='scheduled'
    with cursor() as cur:
        cur.execute('SELECT customer_id,kind FROM appointment_requests WHERE id=%s',(out['result']['id'],));row=cur.fetchone()
        assert row['customer_id']==user and row['kind']=='consultation'
    tools=auth_client.get('/api/chat/tools').json
    assert tools['mode']=='customer' and all(not t['name'].startswith(('stock','user','catalog','role','document')) for t in tools['tools'])
    assert chat(auth_client,'Tạo tài khoản: Họ tên: Giả mạo; Email: fake@example.test')['access_denied']


def test_customer_cannot_gain_staff_tools_even_with_dynamic_grant(auth_client,tool_cleanup):
    with cursor() as cur:cur.execute('INSERT INTO user_roles(user_id,role_id,granted_by) VALUES(8,1,1)')
    try:
        auth_client.login(8)
        assert auth_client.get('/api/admin/users').status_code==403
        assert chat(auth_client,'Danh sách tài khoản')['access_denied']
        assert auth_client.get('/').location=='/chat'
    finally:
        with cursor() as cur:cur.execute('DELETE FROM user_roles WHERE user_id=8 AND role_id=1')


def test_catalog_update_in_chat_reads_current_price(auth_client,tool_cleanup):
    auth_client.login(1)
    with cursor() as cur:
        cur.execute('SELECT pv.list_price,p.model_name FROM product_variants pv JOIN products p ON p.id=pv.product_id WHERE pv.id=14');original=cur.fetchone();before=original['list_price']
    try:
        draft=chat(auth_client,'Cập nhật giá xe SP014: Giá: 57.500.000')
        assert draft['action_draft']['arguments']['list_price']==57500000
        assert not confirm(auth_client,draft).get('access_denied')
        rows=chat(auth_client,'Giá '+original['model_name'])['rows']
        assert any(r['variant_id']==14 and r['list_price']==57500000 for r in rows)
    finally:
        with cursor() as cur:cur.execute('UPDATE product_variants SET list_price=%s WHERE id=14',(before,))


def test_create_account_secret_not_stored_in_chat_or_draft(auth_client,tool_cleanup):
    auth_client.login(1);target=None
    try:
        draft=command(auth_client,'Tạo tài khoản',dict(email='tool-account@example.test',full_name='Tài khoản công cụ',home_branch_id=1,roles=[]))
        assert draft['action_draft']['requires_password']
        secret='SecureToolPassword123!'
        out=confirm(auth_client,draft,action_secret=secret);target=out['result']['id']
        with cursor() as cur:
            cur.execute('SELECT arguments_json,result_json FROM chat_action_drafts WHERE id=%s',(draft['action_draft']['id'],));assert secret not in str(cur.fetchone())
            cur.execute('SELECT content FROM chat_messages WHERE session_id=%s',(draft['session_id'],));assert secret not in str(cur.fetchall())
            cur.execute('SELECT is_active,must_change_password FROM users WHERE id=%s',(target,));assert cur.fetchone()['must_change_password']==1
    finally:
        if target:
            with cursor() as cur:
                cur.execute("DELETE FROM rbac_audit_log WHERE target_type='user' AND target_id=%s",(target,));cur.execute('DELETE FROM user_roles WHERE user_id=%s',(target,));cur.execute('DELETE FROM users WHERE id=%s',(target,))


def make_customer_file(fmt,email='file@customer-input.test'):
    headers=['Họ và tên','Số điện thoại','Email','Chi nhánh','Ngày đăng ký','Trạng thái']
    values=['Khách Tệp Kiểm Thử','0901234567',email,'NT01','10/10/2026','Tiềm năng']
    out=BytesIO()
    if fmt=='xlsx':
        from openpyxl import Workbook  # Đọc hoặc tạo workbook Excel.
        book=Workbook();sheet=book.active;sheet.title='Danh_sach';sheet.append(headers);sheet.append(values);book.save(out)
    elif fmt=='docx':
        from docx import Document  # Tạo tài liệu Word mẫu có bảng và nội dung.
        doc=Document();table=doc.add_table(rows=1,cols=len(headers))
        for cell,value in zip(table.rows[0].cells,headers):cell.text=value
        for cell,value in zip(table.add_row().cells,values):cell.text=value
        doc.save(out)
    else:
        from reportlab.platypus import SimpleDocTemplate,Table,TableStyle  # Dựng bảng khách trong PDF upload.
        from reportlab.lib.pagesizes import A4,landscape  # Chọn trang ngang để vừa các cột.
        from reportlab.pdfbase import pdfmetrics  # Đăng ký font tiếng Việt cho PDF.
        from reportlab.pdfbase.ttfonts import TTFont  # Nạp font cục bộ dùng trong fixture.
        from reportlab.lib import colors  # Vẽ lưới bảng để parser nhận diện cột.
        pdfmetrics.registerFont(TTFont('ImportNoto',str(Path('static/vendor/fonts/NotoSans-Regular.ttf'))))
        table=Table([headers,values],colWidths=[130,95,210,70,95,100])
        table.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'ImportNoto'),('FONTSIZE',(0,0),(-1,-1),9),('GRID',(0,0),(-1,-1),1,colors.black),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        SimpleDocTemplate(out,pagesize=landscape(A4),leftMargin=20,rightMargin=20).build([table])
    out.seek(0);return out


@pytest.mark.parametrize('fmt',['pdf','docx','xlsx'])
def test_three_formats_import_to_customers_and_history(auth_client,clean_customer_input,fmt):
    auth_client.login(3)
    with cursor() as cur:cur.execute("SELECT id FROM kb_categories WHERE code='customers'");category=cur.fetchone()['id']
    uploaded=auth_client.post('/api/documents',data={'title':'Kiểm thử parser khách '+fmt,'category_id':str(category),'file':(make_customer_file(fmt,fmt+'@customer-input.test'),'customers.'+fmt)})
    assert uploaded.status_code==201,uploaded.json
    document=uploaded.json
    response=auth_client.post('/api/customer-input',json={'document_id':document['id']});assert response.status_code==201,response.json
    batch=response.json;BATCHES.add(batch['id']);assert batch['valid'],batch
    assert auth_client.post('/api/customer-input',json={'document_id':document['id']}).json['id']==batch['id']
    assert auth_client.get('/api/customers?q='+fmt+'@customer-input.test').json['total']==0
    committed=auth_client.post('/api/customer-input/'+str(batch['id'])+'/commit',json={'version':batch['version'],'confirmed':True});assert committed.status_code==200,committed.json
    assert committed.json['created']==1
    listed=auth_client.get('/api/customers?import_batch='+str(batch['id'])).json
    assert listed['total']==1 and listed['rows'][0]['email']==fmt+'@customer-input.test'
    history=auth_client.get('/api/customer-imports').json['rows']
    entry=next(r for r in history if r['id']==batch['id']);assert entry['file_format']==fmt and entry['customer_count']==1
    auth_client.login(4)
    assert auth_client.get('/api/customers?import_batch='+str(batch['id'])).json['total']==0
    assert batch['id'] not in {r['id'] for r in auth_client.get('/api/customer-imports').json['rows']}


def test_chat_attachment_and_commit_without_toolbar(auth_client,clean_customer_input):
    auth_client.login(3)
    response=auth_client.post('/api/chat/customer-file',data={'title':'Kiểm thử parser chat attachment','file':(make_customer_file('docx','attachment@customer-input.test'),'customers.docx')})
    assert response.status_code==201,response.json
    batch=response.json['customer_draft'];BATCHES.add(batch['id']);assert batch['valid']
    out=chat(auth_client,'Xác nhận lưu khách hàng',customer_batch_id=batch['id'],customer_batch_version=batch['version'])
    assert out['result']['created']==1 and out['result']['document_id']==response.json['document_id']
    assert auth_client.get('/api/customers?import_batch='+str(batch['id'])).json['total']==1


def test_scan_and_missing_required_fields_do_not_create_customers(auth_client,clean_customer_input):
    from customer_file_import import extracted_rows  # Chuyển tài liệu thành bản nháp nhập khách.
    from customer_input import CustomerInputError  # Dùng quy tắc kiểm tra và lưu batch nhập khách.
    with pytest.raises(CustomerInputError):extracted_rows({'blocks':[]})
    auth_client.login(3)
    response=auth_client.post('/api/chat/customer-file',data={'title':'Kiểm thử parser scan khách','file':(BytesIO(Path('data/samples/documents/scan.pdf').read_bytes()),'scan.pdf')})
    assert response.status_code==400


def test_backfill_committed_file_history_is_idempotent(auth_client,clean_customer_input):
    from init_db import get_config,connect  # Dùng cấu hình, script SQL và kiểm tra schema khởi tạo.
    from scripts.backfill_customer_imports import backfill  # Khôi phục lịch sử các dòng khách đã commit.
    auth_client.login(3)
    response=auth_client.post('/api/chat/customer-file',data={'title':'Kiểm thử parser backfill','file':(make_customer_file('xlsx','backfill@customer-input.test'),'old.xlsx')})
    batch=response.json['customer_draft'];BATCHES.add(batch['id'])
    chat(auth_client,'Xác nhận lưu khách hàng',customer_batch_id=batch['id'],customer_batch_version=batch['version'])
    with cursor() as cur:cur.execute('DELETE FROM customer_import_rows WHERE batch_id=%s',(batch['id'],))
    cn=connect(get_config(),True)
    try:assert backfill(cn)==1;assert backfill(cn)==0
    finally:cn.close()
    assert auth_client.get('/api/customers?import_batch='+str(batch['id'])).json['total']==1


def test_existing_customer_contact_update_does_not_erase_purchase_or_optional_data(auth_client,clean_customer_input):
    from test_customer_input import customer,stage_client,commit_client  # Dùng fixture và helper tạo/dọn batch nhập khách.
    auth_client.login(3)
    original=stage_client(auth_client,[customer('preserve@customer-input.test',status='Đã mua',purchased_sku='SP014',purchase_amount=56500000,address='Địa chỉ cần giữ')]).json
    result=commit_client(auth_client,original).json;target=result['customer_ids'][0]
    # File chỉ cập nhật liên hệ, không có cột mua xe/địa chỉ/trạng thái.
    from docx import Document  # Tạo tài liệu Word mẫu có bảng và nội dung.
    doc=Document();table=doc.add_table(rows=2,cols=3)
    for cell,value in zip(table.rows[0].cells,['Họ và tên','Số điện thoại','Email']):cell.text=value
    for cell,value in zip(table.rows[1].cells,['Tên đã cập nhật','0909876543','preserve@customer-input.test']):cell.text=value
    file=BytesIO();doc.save(file);file.seek(0)
    uploaded=auth_client.post('/api/chat/customer-file',data={'title':'Kiểm thử parser giữ thông tin cũ','file':(file,'update.docx')}).json
    batch=uploaded['customer_draft'];BATCHES.add(batch['id']);assert batch['valid'],batch
    assert batch['rows'][0]['data']['address']=='Địa chỉ cần giữ'
    assert batch['rows'][0]['data']['status']=='Đã mua'
    out=chat(auth_client,'Xác nhận lưu khách hàng',customer_batch_id=batch['id'],customer_batch_version=batch['version'])
    assert out['result']['updated']==1 and out['result']['orders_created']==0
    with cursor() as cur:
        cur.execute('SELECT full_name FROM users WHERE id=%s',(target,));assert cur.fetchone()['full_name']=='Tên đã cập nhật'
        cur.execute('SELECT COUNT(*) AS n FROM orders WHERE customer_id=%s',(target,));assert cur.fetchone()['n']==1


def test_import_existing_document_from_chat_binds_draft_session(auth_client,clean_customer_input):
    auth_client.login(3)
    with cursor() as cur:cur.execute("SELECT id FROM kb_categories WHERE code='customers'");category=cur.fetchone()['id']
    document=auth_client.post('/api/documents',data={'title':'Kiểm thử parser import document command','category_id':str(category),'file':(make_customer_file('docx','documentcmd@customer-input.test'),'customers.docx')}).json
    first=auth_client.post('/api/customer-input',json={'document_id':document['id']}).json;BATCHES.add(first['id'])
    reply=chat(auth_client,'Đồng bộ khách hàng từ tài liệu #'+str(document['id']))
    assert reply['customer_draft']['id']==first['id']
    saved=chat(auth_client,'Xác nhận lưu khách hàng',customer_batch_id=first['id'],customer_batch_version=first['version'])
    assert saved['result']['created']==1


def test_password_in_command_is_redacted_and_not_sent_to_model(auth_client,tool_cleanup,monkeypatch):
    auth_client.login(1)
    monkeypatch.setenv('GROQ_API_KEY','test-key')
    def forbidden(*args):pytest.fail('Không gửi mật khẩu trong câu lệnh sang model')
    monkeypatch.setattr('chat_tools.model_args',forbidden)
    secret='DoNotPersistPassword123!'
    reply=command(auth_client,'Tạo tài khoản',dict(full_name='Không tạo',email='private@example.test',password=secret))
    assert 'ô bảo mật' in reply['answer']
    with cursor() as cur:
        cur.execute('SELECT content FROM chat_messages WHERE session_id=%s',(reply['session_id'],));assert secret not in str(cur.fetchall())


def test_580_customer_file_commits_all_rows_once_and_creates_no_usable_password(auth_client,clean_customer_input):
    from openpyxl import Workbook  # Đọc hoặc tạo workbook Excel.
    import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.
    auth_client.login(3)
    book=Workbook();sheet=book.active;sheet.title='Khach_hang'
    sheet.append(['Họ và tên','Số điện thoại','Email','Chi nhánh phụ trách','Ngày đăng ký','Trạng thái'])
    for index in range(580):sheet.append(['Khách lô kiểm thử '+str(index),'0901234567',f'bulk580-{index}@customer-input.test','NT01','10/10/2026','Tiềm năng'])
    file=BytesIO();book.save(file);file.seek(0)
    response=auth_client.post('/api/chat/customer-file',data={'title':'Kiểm thử parser 580 khách','file':(file,'customers580.xlsx')})
    assert response.status_code==201,response.json
    batch=response.json['customer_draft'];BATCHES.add(batch['id']);assert batch['valid'] and len(batch['rows'])==580
    outcome=chat(auth_client,'Xác nhận lưu khách hàng',customer_batch_id=batch['id'],customer_batch_version=batch['version'])['result']
    assert outcome['created']==580 and outcome['orders_created']==0
    assert auth_client.get('/api/customers?import_batch='+str(batch['id'])).json['total']==580
    replay=auth_client.post('/api/customer-input/'+str(batch['id'])+'/commit',json={'version':batch['version'],'confirmed':True})
    assert replay.json==outcome
    with cursor() as cur:
        cur.execute('SELECT COUNT(*) AS n FROM users WHERE email LIKE %s',('bulk580-%@customer-input.test',));assert cur.fetchone()['n']==580
        cur.execute('SELECT is_active FROM users WHERE id=%s',(outcome['customer_ids'][0],));assert cur.fetchone()['is_active']==0
        # Kể cả bật hoạt động mà chưa đặt mật khẩu, tài khoản nhập file không đăng nhập được.
        cur.execute('UPDATE users SET is_active=TRUE WHERE id=%s',(outcome['customer_ids'][0],))
    other=auth_client.__class__(auth_client.application);other.get('/login')
    assert other.post('/login',data={'email':'bulk580-0@customer-input.test','password':os.environ['DEMO_ACCOUNT_PASSWORD']}).status_code==401


def test_file_above_1000_rows_still_rejected(tmp_path):
    from openpyxl import Workbook  # Đọc hoặc tạo workbook Excel.
    from customer_input import read_customer_workbook,CustomerInputError  # Dùng quy tắc kiểm tra và lưu batch nhập khách.
    book=Workbook();sheet=book.active;sheet.title='Khach_hang';sheet.append(['Họ và tên'])
    for _ in range(1001):sheet.append(['Quá giới hạn'])
    path=tmp_path/'too-many.xlsx';book.save(path)
    with pytest.raises(CustomerInputError,match='1000'):read_customer_workbook(path)
