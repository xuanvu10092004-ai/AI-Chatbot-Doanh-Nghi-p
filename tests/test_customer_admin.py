import pytest

from db import cursor
from test_customer_input import clean_customer_input,customer,stage_client,commit_client
from test_document_uploads import document_storage


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
