from pathlib import Path  # Tạo và kiểm tra đường dẫn file trong dự án.
import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.

from db import cursor  # Mở cursor hoặc connection MySQL.
from customer_input import read_customer_workbook,normalize_row  # Dùng quy tắc kiểm tra và lưu batch nhập khách.
from test_document_uploads import document_storage  # Dùng fixture lưu trữ và helper upload tài liệu.

BATCHES=set()


@pytest.fixture(autouse=True)
def clean_customer_input(document_storage):
    BATCHES.clear()
    yield
    with cursor() as cur:
        for batch_id in BATCHES:cur.execute('DELETE FROM customer_input_batches WHERE id=%s',(batch_id,))
        cur.execute('SELECT id FROM users WHERE email LIKE %s',('%@customer-input.test',));users=cur.fetchall()
        for row in users:
            cur.execute('DELETE FROM orders WHERE customer_id=%s',(row['id'],))
            cur.execute("DELETE FROM rbac_audit_log WHERE target_type='user' AND target_id=%s",(row['id'],))
            cur.execute('DELETE FROM user_roles WHERE user_id=%s',(row['id'],))
            cur.execute('DELETE FROM customer_profiles WHERE user_id=%s',(row['id'],))
            cur.execute('DELETE FROM users WHERE id=%s',(row['id'],))


def customer(email='new@customer-input.test',**values):
    return {'full_name':'Khách kiểm thử','phone':'0901234567','email':email,'branch_code':'NT01','registered_at':'2026-10-10','status':'Tiềm năng',
            'gender':'Nữ','birth_date':'2000-01-01','province':'Khánh Hòa','district':'Nha Trang','address':'Địa chỉ mô phỏng',
            'occupation':'Nhân viên','lead_source':'Website','interested_model':'Air Blade 125','payment_preference':'Trả thẳng',**values}


def stage_client(client,rows):
    response=client.post('/api/customer-input',json={'rows':rows})
    if response.status_code==201:BATCHES.add(response.get_json()['id'])
    return response


def commit_client(client,batch,**values):
    return client.post(f"/api/customer-input/{batch['id']}/commit",json={'version':batch['version'],'confirmed':True,**values})


def test_original_workbook_maps_all_customers_and_detects_existing_orders(auth_client):
    rows=read_customer_workbook(Path('data/source/honda_dataset_khach_hang_san_pham.xlsx'))
    assert len(rows)==80
    canonical=[normalize_row(row)[0] for row in rows]
    assert all(not normalize_row(row)[1] for row in rows)
    auth_client.login(1);response=stage_client(auth_client,canonical);assert response.status_code==201
    preview=response.get_json();assert preview['valid']
    assert len(preview['rows'])==80 and {row['action'] for row in preview['rows']}=={'update'}
    assert sum(row['order_action']=='existing' for row in preview['rows'])==30


def test_create_update_and_repeated_confirmation_are_atomic_and_idempotent(auth_client):
    auth_client.login(3)
    batch=stage_client(auth_client,[customer(status='Đã mua',purchased_sku='SP014',purchase_amount=56500000)]).get_json()
    assert batch['valid'] and batch['rows'][0]['order_action']=='create_pending'
    assert commit_client(auth_client,batch,confirmed=False).status_code==400
    response=commit_client(auth_client,batch);assert response.status_code==200
    result=response.get_json();assert result['created']==1 and result['orders_created']==1
    assert commit_client(auth_client,batch).get_json()==result
    with cursor() as cur:
        cur.execute('SELECT u.full_name,u.is_active,cp.customer_code,cp.gender,cp.province,cp.interested_product_id FROM users u JOIN customer_profiles cp ON cp.user_id=u.id WHERE u.id=%s',(result['customer_ids'][0],))
        row=cur.fetchone();assert row['full_name']=='Khách kiểm thử' and row['is_active']==0 and row['gender']=='Nữ' and row['province']=='Khánh Hòa'
        cur.execute('SELECT status,approved_by FROM orders WHERE id=%s',(result['order_ids'][0],));assert cur.fetchone()=={'status':'pending','approved_by':None}
        cur.execute('SELECT quantity,unit_price FROM order_items WHERE order_id=%s',(result['order_ids'][0],));assert cur.fetchone()=={'quantity':1,'unit_price':56500000}
    auth_client.login(1)  # Staff tạo được khách; chỉ super_admin sửa hồ sơ đã tồn tại.
    second=stage_client(auth_client,[customer(full_name='Tên đã sửa',status='Đã mua',purchased_sku='SP014',purchase_amount=56500000)]).get_json()
    assert second['valid'] and second['rows'][0]['action']=='update'
    assert second['rows'][0]['changes']['full_name']=={'before':'Khách kiểm thử','after':'Tên đã sửa'}
    assert second['rows'][0]['data']['customer_code']==row['customer_code'] and 'customer_code' not in second['rows'][0]['changes']
    assert second['rows'][0]['order_action']=='existing'
    changed=commit_client(auth_client,second).get_json();assert changed['updated']==1 and changed['orders_created']==0


@pytest.mark.parametrize('invalid',[
    {'email':'invalid'},{'phone':'123'},{'registered_at':'31/02/2026'},
    {'status':'Đã mua','purchased_sku':'SP999999','purchase_amount':10},
    {'status':'Đã mua','purchased_sku':'SP014','purchase_amount':'=1+1'},
    {'full_name':''},{'interested_model':'Mẫu không tồn tại'},
])
def test_invalid_row_blocks_entire_batch_without_partial_writes(auth_client,invalid):
    auth_client.login(3)
    batch=stage_client(auth_client,[customer('valid@customer-input.test'),{**customer('invalid@customer-input.test'),**invalid}]).get_json()
    assert not batch['valid']
    assert commit_client(auth_client,batch).status_code==400
    with cursor() as cur:cur.execute('SELECT COUNT(*) AS n FROM users WHERE email LIKE %s',('%@customer-input.test',));assert cur.fetchone()['n']==0


def test_duplicate_and_branch_mismatches_are_blocked(auth_client):
    auth_client.login(3)
    duplicate=stage_client(auth_client,[customer(),customer()]).get_json();assert not duplicate['valid']
    outside=stage_client(auth_client,[customer(branch_code='NT02')]).get_json();assert not outside['valid']
    assert commit_client(auth_client,outside).status_code==400
    auth_client.login(4);assert auth_client.get(f"/api/customer-input/{outside['id']}").status_code==404


@pytest.mark.parametrize('user_id',[None,5,8])
def test_customer_writes_are_backend_permission_checked(auth_client,user_id):
    auth_client.login(user_id)
    assert stage_client(auth_client,[customer()]).status_code==403
    data=auth_client.post('/chat',json={'question':'Thêm khách hàng'}).get_json()
    assert data['access_denied'] is True
    with cursor() as cur:
        cur.execute('SELECT decision FROM chatbot_audit_log WHERE session_id=%s ORDER BY id DESC LIMIT 1',(data['session_id'],));assert cur.fetchone()['decision']=='denied'


def test_chat_collects_fields_and_requires_latest_explicit_confirmation(auth_client):
    auth_client.login(3)
    first=auth_client.post('/chat',json={'question':'Thêm khách hàng'}).get_json();draft=first['customer_draft'];BATCHES.add(draft['id'])
    assert 'Họ và tên' in first['answer']
    complete=auth_client.post('/chat',json={'question':'Họ và tên: Khách hội thoại; Email: chat@customer-input.test; Số điện thoại: 0901234567; Giới tính: Nam; Ngày sinh: 01/01/2000; Nghề nghiệp: Kỹ sư'}).get_json()
    latest=complete['customer_draft'];assert latest['valid']
    with cursor() as cur:cur.execute('SELECT COUNT(*) AS n FROM users WHERE email=%s',('chat@customer-input.test',));assert cur.fetchone()['n']==0
    stale=auth_client.post('/chat',json={'question':'Xác nhận lưu khách hàng','customer_batch_id':draft['id'],'customer_batch_version':draft['version']}).get_json()
    assert 'đã thay đổi' in stale['answer']
    saved=auth_client.post('/chat',json={'question':'Xác nhận lưu khách hàng','customer_batch_id':latest['id'],'customer_batch_version':latest['version']}).get_json()
    assert saved['result']['created']==1


def test_edit_after_preview_requires_fresh_confirmation(auth_client):
    auth_client.login(3)
    first=stage_client(auth_client,[customer()]).get_json()
    update=auth_client.put(f"/api/customer-input/{first['id']}",json={'version':first['version'],'rows':[customer(full_name='Tên mới')]}).get_json()
    assert commit_client(auth_client,first).status_code==409
    assert commit_client(auth_client,update).status_code==200


def test_file_customer_category_uses_database_sync_not_rag(auth_client):
    from io import BytesIO  # Tạo stream trong bộ nhớ cho upload hoặc PDF.
    auth_client.login(1)
    with cursor() as cur:cur.execute("SELECT id FROM kb_categories WHERE code='customers'");category=cur.fetchone()['id']
    file=Path('data/source/honda_dataset_khach_hang_san_pham.xlsx')
    document=auth_client.post('/api/documents',data={'title':'Kiểm thử parser khách hàng','category_id':str(category),'file':(BytesIO(file.read_bytes()),file.name)}).get_json()
    response=auth_client.post('/api/customer-input',json={'document_id':document['id']});assert response.status_code==201
    batch=response.get_json();BATCHES.add(batch['id']);assert batch['valid'] and len(batch['rows'])==80
    assert auth_client.post(f"/api/documents/{document['id']}/publish",json={'version':document['version']}).status_code==400


def test_scope_change_blocks_committed_batch_details(auth_client):
    auth_client.login(3);batch=stage_client(auth_client,[customer()]).get_json()
    assert commit_client(auth_client,batch).status_code==200
    with cursor() as cur:
        cur.execute('SELECT scope_branch_id FROM user_roles WHERE user_id=3 AND role_id=3');previous=cur.fetchone()['scope_branch_id']
        cur.execute('UPDATE user_roles SET scope_branch_id=2 WHERE user_id=3 AND role_id=3')
    try:
        assert auth_client.get(f"/api/customer-input/{batch['id']}").status_code==404
        assert commit_client(auth_client,batch).status_code==404
    finally:
        with cursor() as cur:cur.execute('UPDATE user_roles SET scope_branch_id=%s WHERE user_id=3 AND role_id=3',(previous,))


def test_client_cannot_assign_staff_role_or_activate_portal_account(auth_client):
    auth_client.login(3)
    batch=stage_client(auth_client,[customer(user_type='staff',is_active=True,roles=[1])]).get_json()
    outcome=commit_client(auth_client,batch).get_json()
    with cursor() as cur:
        cur.execute('SELECT user_type,is_active FROM users WHERE id=%s',(outcome['customer_ids'][0],));assert cur.fetchone()=={'user_type':'customer','is_active':0}
        cur.execute('SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id=r.id WHERE ur.user_id=%s',(outcome['customer_ids'][0],));assert cur.fetchall()==[{'name':'customer'}]


def test_template_has_source_columns_and_preserves_phone_text(auth_client):
    from openpyxl import load_workbook  # Đọc hoặc tạo workbook Excel.
    from io import BytesIO  # Tạo stream trong bộ nhớ cho upload hoặc PDF.
    auth_client.login(3);response=auth_client.get('/api/customer-input/template');assert response.status_code==200
    book=load_workbook(BytesIO(response.data));sheet=book['Khach_hang']
    original=load_workbook('data/source/honda_dataset_khach_hang_san_pham.xlsx',read_only=True)
    assert [cell.value for cell in sheet[1]]==[cell.value for cell in next(original['Khach_hang'].iter_rows())]
    original.close()
    assert sheet.cell(2,6).number_format=='@'
    book.close()
