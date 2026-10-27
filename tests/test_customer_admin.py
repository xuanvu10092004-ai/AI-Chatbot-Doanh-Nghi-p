import pytest

from db import cursor
from test_customer_input import clean_customer_input,customer,stage_client,commit_client
from test_document_uploads import document_storage
from test_chat_tools_imports import no_live_model,tool_cleanup,chat,confirm


@pytest.fixture
def target(auth_client):
    auth_client.login(3)
    draft=stage_client(auth_client,[customer()]).json
    result=commit_client(auth_client,draft)
    assert result.status_code==200,result.json
    return result.json['customer_ids'][0]


def test_admin_partial_edit_and_stale_version(auth_client,target):
    auth_client.login(1)
    record=auth_client.get(f'/api/customers/{target}').json['customer']
    response=auth_client.patch(f'/api/customers/{target}',json={'version':record['version'],'full_name':'Tên đã sửa'})
    assert response.status_code==200,response.json
    changed=response.json['customer']
    assert changed['full_name']=='Tên đã sửa' and changed['phone']==record['phone'] and changed['address']==record['address']
    assert changed['version']>record['version']
    assert auth_client.patch(f'/api/customers/{target}',json={'version':record['version'],'phone':'0909999999'}).status_code==409


@pytest.mark.parametrize('user',[None,2,3,4,5,6,8])
def test_non_admin_routes_and_import_cannot_edit(auth_client,target,user):
    auth_client.login(user)
    for method in ('get','patch','delete'):
        reply=getattr(auth_client,method)(f'/api/customers/{target}',**({'json':{'version':1,'confirmed':True}} if method!='get' else {}))
        assert reply.status_code==403
    if user in (2,3,4):
        reply=stage_client(auth_client,[customer(full_name='Không được sửa')])
        assert reply.status_code==403,reply.json
        assert auth_client.put(f'/api/admin/users/{target}',json={'full_name':'Không được sửa'}).status_code==403
    with cursor() as cur:
        cur.execute('SELECT full_name FROM users WHERE id=%s',(target,));assert cur.fetchone()['full_name']=='Khách kiểm thử'


def test_soft_delete_idempotent_restore_and_active_filters(auth_client,target):
    auth_client.login(1)
    record=auth_client.get(f'/api/customers/{target}').json['customer']
    assert auth_client.delete(f'/api/customers/{target}',json={'version':record['version']}).status_code==400
    deleted=auth_client.delete(f'/api/customers/{target}',json={'version':record['version'],'confirmed':True})
    assert deleted.status_code==200 and deleted.json['customer']['deleted_at']
    assert auth_client.delete(f'/api/customers/{target}',json={'version':record['version'],'confirmed':True}).json['already_deleted']
    assert auth_client.get('/api/customers?q=new@customer-input.test').json['total']==0
    with cursor() as cur:
        cur.execute('SELECT customer_id FROM v_ai_customers WHERE customer_id=%s',(target,));assert cur.fetchone() is None
    assert auth_client.patch(f'/api/customers/{target}',json={'version':deleted.json['customer']['version'],'full_name':'Không được sửa'}).status_code==409
    restored=auth_client.post(f'/api/customers/{target}/restore',json={'version':deleted.json['customer']['version'],'confirmed':True})
    assert restored.status_code==200 and not restored.json['customer']['deleted_at']
    assert auth_client.get('/api/customers?q=new@customer-input.test').json['total']==1


def test_grant_alone_does_not_make_manager_super_admin(auth_client,target):
    with cursor() as cur:
        cur.execute("SELECT id FROM permissions WHERE code='customer:admin:manage'");permission=cur.fetchone()['id']
        cur.execute("INSERT INTO role_permissions(role_id,permission_id,data_scope) VALUES(2,%s,'all')",(permission,))
    try:
        auth_client.login(2)
        assert auth_client.patch(f'/api/customers/{target}',json={'version':1,'full_name':'Giả quyền'}).status_code==403
    finally:
        with cursor() as cur:cur.execute('DELETE FROM role_permissions WHERE role_id=2 AND permission_id=%s',(permission,))


def test_chat_uses_same_service_preview_confirmation_and_replay(auth_client,target,tool_cleanup):
    auth_client.login(1)
    draft=chat(auth_client,f'Sửa khách hàng #{target}: Số điện thoại: 0909999999')
    assert draft['action_draft']['arguments']['id']==target
    assert auth_client.get(f'/api/customers/{target}').json['customer']['phone']=='0901234567'
    out=confirm(auth_client,draft)
    assert out['result']['customer']['phone']=='0909999999'
    assert confirm(auth_client,draft)['result']==out['result']
    deleted=chat(auth_client,f'Xóa khách hàng #{target}')
    assert not auth_client.get(f'/api/customers/{target}').json['customer']['deleted_at']
    confirm(auth_client,deleted)
    assert auth_client.get(f'/api/customers/{target}').json['customer']['deleted_at']
    restored=chat(auth_client,f'Khôi phục khách hàng #{target}')
    assert not confirm(auth_client,restored)['result']['customer']['deleted_at']


@pytest.mark.parametrize('user',[None,2,3,5,6,8])
def test_chat_denies_existing_customer_edits_for_non_admin(auth_client,target,tool_cleanup,user):
    auth_client.login(user)
    result=chat(auth_client,f'Cập nhật khách hàng #{target}: Họ tên: Không được sửa')
    assert result['access_denied'] and 'action_draft' not in result
    with cursor() as cur:
        cur.execute('SELECT full_name FROM users WHERE id=%s',(target,));assert cur.fetchone()['full_name']=='Khách kiểm thử'
        cur.execute('SELECT decision FROM chatbot_audit_log WHERE session_id=%s ORDER BY id DESC LIMIT 1',(result['session_id'],));assert cur.fetchone()['decision']=='denied'


def test_direct_sql_invalidates_admin_snapshot(auth_client,target):
    auth_client.login(1)
    before=auth_client.get(f'/api/customers/{target}').json['customer']
    with cursor() as cur:cur.execute('UPDATE customer_profiles SET address=%s WHERE user_id=%s',('Địa chỉ SQL mới',target))
    result=auth_client.patch(f'/api/customers/{target}',json={'version':before['version'],'phone':'0909999999'})
    assert result.status_code==409
    after=auth_client.get(f'/api/customers/{target}').json['customer']
    assert after['address']=='Địa chỉ SQL mới' and after['phone']==before['phone']


def test_delete_preserves_order_and_invoice(auth_client):
    auth_client.login(3)
    draft=stage_client(auth_client,[customer(status='Đã mua',purchased_sku='SP014',purchase_amount=56500000)]).json
    result=commit_client(auth_client,draft).json;target=result['customer_ids'][0];order=result['order_ids'][0]
    auth_client.login(1)
    before=auth_client.get(f'/api/customers/{target}').json['customer']
    assert auth_client.delete(f'/api/customers/{target}',json={'version':before['version'],'confirmed':True}).status_code==200
    with cursor() as cur:
        cur.execute('SELECT customer_id FROM orders WHERE id=%s',(order,));assert cur.fetchone()['customer_id']==target
        cur.execute('SELECT quantity,unit_price FROM order_items WHERE order_id=%s',(order,));assert cur.fetchone()=={'quantity':1,'unit_price':56500000}
    pdf=auth_client.get(f'/api/orders/{order}/invoice.pdf')
    assert pdf.status_code==200 and pdf.data.startswith(b'%PDF')


def test_read_pages_never_export_or_touch_source(auth_client,monkeypatch):
    def forbidden(*a,**kw):pytest.fail('GET không được xuất Excel')
    monkeypatch.setattr('excel_sync._write_workbook',forbidden)
    auth_client.login(1)
    for path in ('/customers','/inventory','/api/customers','/api/excel-sync'):
        assert auth_client.get(path).status_code==200


def test_deleted_profile_cannot_be_imported_and_is_absent_from_export(auth_client,target,tmp_path,monkeypatch):
    from excel_sync_worker import process_sync
    from openpyxl import load_workbook
    auth_client.login(1)
    record=auth_client.get(f'/api/customers/{target}').json['customer']
    old=stage_client(auth_client,[customer(full_name='Bản nháp cũ')]).json
    deleted=auth_client.delete(f'/api/customers/{target}',json={'version':record['version'],'confirmed':True})
    assert deleted.status_code==200
    assert commit_client(auth_client,old).status_code==409
    output=tmp_path/'customers.xlsx';monkeypatch.setattr('excel_sync.SYNCED_WORKBOOK',output)
    assert process_sync(force=True)['status']=='completed'
    book=load_workbook(output,read_only=True,data_only=True)
    try:assert 'new@customer-input.test' not in {row[6] for row in book['Khach_hang'].iter_rows(min_row=2,values_only=True)}
    finally:book.close()


@pytest.mark.parametrize('change',[{'phone':'123'},{'email':'not-an-email'},{'branch_code':'XX99'},{'status':'Không có trạng thái này'},{'interested_model':'Xe không có'},{'full_name':{'sql':'DROP TABLE users'}},{'purchased_sku':'SP014'}])
def test_invalid_partial_edits_never_write(auth_client,target,change):
    auth_client.login(1)
    before=auth_client.get(f'/api/customers/{target}').json['customer']
    response=auth_client.patch(f'/api/customers/{target}',json={'version':before['version'],**change})
    assert response.status_code==400,response.json
    assert auth_client.get(f'/api/customers/{target}').json['customer']==before


def test_two_concurrent_editors_get_success_and_conflict(auth_client,target):
    from concurrent.futures import ThreadPoolExecutor
    auth_client.login(1)
    record=auth_client.get(f'/api/customers/{target}').json['customer']
    clients=[auth_client.__class__(auth_client.application).login(1) for _ in range(2)]
    def save(index):return clients[index].patch(f'/api/customers/{target}',json={'version':record['version'],'full_name':'Người sửa '+str(index)}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(save,range(2)))
    assert sorted(statuses)==[200,409]


def test_export_failure_does_not_report_committed_edit_as_failed(auth_client,target,tmp_path,monkeypatch):
    from excel_sync_worker import process_sync
    auth_client.login(1)
    record=auth_client.get(f'/api/customers/{target}').json['customer']
    def locked(*args):raise PermissionError('Excel đang mở')
    monkeypatch.setattr('excel_sync._write_workbook',locked)
    monkeypatch.setattr('excel_sync.SYNCED_WORKBOOK',tmp_path/'locked.xlsx')
    saved=auth_client.patch(f'/api/customers/{target}',json={'version':record['version'],'full_name':'Đã commit dù Excel khóa'})
    assert saved.status_code==200 and saved.json['excel_sync']['status']=='pending'
    assert process_sync(force=True)['status']=='failed'
    assert auth_client.get(f'/api/customers/{target}').json['customer']['full_name']=='Đã commit dù Excel khóa'
    status=auth_client.get('/api/excel-sync').json
    assert status['status']=='failed' and status['pending']>0 and status['next_retry_at']


def test_generic_user_management_cannot_mask_customer_denial(auth_client,target):
    with cursor() as cur:
        cur.execute("SELECT id FROM permissions WHERE code='user:manage'");permission=cur.fetchone()['id']
        cur.execute('SELECT data_scope FROM role_permissions WHERE role_id=3 AND permission_id=%s',(permission,));prior=cur.fetchone()
        cur.execute("INSERT INTO role_permissions(role_id,permission_id,data_scope) VALUES(3,%s,'all') ON DUPLICATE KEY UPDATE data_scope='all'",(permission,))
    try:
        auth_client.login(3)
        assert auth_client.get('/api/admin/users').status_code==200
        result=auth_client.put(f'/api/admin/users/{target}',json={'full_name':'Không được sửa qua quản trị user'})
        assert result.status_code==403,result.json
        with cursor() as cur:
            cur.execute('SELECT full_name FROM users WHERE id=%s',(target,));assert cur.fetchone()['full_name']=='Khách kiểm thử'
    finally:
        with cursor() as cur:
            if prior:cur.execute('UPDATE role_permissions SET data_scope=%s WHERE role_id=3 AND permission_id=%s',(prior['data_scope'],permission))
            else:cur.execute('DELETE FROM role_permissions WHERE role_id=3 AND permission_id=%s',(permission,))
