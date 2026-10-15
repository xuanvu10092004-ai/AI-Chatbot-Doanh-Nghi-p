from db import cursor


def test_dynamic_role_grant_revoke_and_audit(auth_client):
    auth_client.login(1)
    with cursor() as c:c.execute("SELECT id FROM permissions WHERE code='user:manage'");pid=c.fetchone()['id']
    response=auth_client.post('/api/admin/roles',json={'name':'test_dynamic_role','landing_path':'/dashboard','permissions':[{'permission_id':pid,'data_scope':'all'}]})
    assert response.status_code==200;role_id=response.get_json()['id']
    try:
        # Nhân viên không có quyền quản trị; khách nay luôn bị giới hạn ở tra giá/đặt lịch.
        assert auth_client.post('/api/admin/users/7/roles',json={'roles':[{'role_id':role_id}]}).status_code==200
        employee=auth_client.__class__(auth_client.application);employee.login(7)
        assert employee.get('/admin/users').status_code==200
        assert auth_client.put('/api/admin/roles/'+str(role_id),json={'permissions':[]}).status_code==200
        assert employee.get('/admin/users').status_code==403
        with cursor() as c:
            c.execute("SELECT COUNT(*) AS n FROM rbac_audit_log WHERE target_type='role' AND target_id=%s",(role_id,));assert c.fetchone()['n']>=2
        assert auth_client.delete('/api/admin/users/7/roles',json={'role_id':role_id}).status_code==200
        assert auth_client.delete('/api/admin/roles/'+str(role_id),json={}).status_code==200
    finally:
        with cursor() as c:
            c.execute('DELETE FROM user_roles WHERE role_id=%s',(role_id,));c.execute('DELETE FROM role_permissions WHERE role_id=%s',(role_id,));c.execute('DELETE FROM roles WHERE id=%s',(role_id,))


def test_admin_protections_and_permission_denial(auth_client):
    auth_client.login(1)
    assert auth_client.delete('/api/admin/roles/3',json={}).status_code==400
    assert auth_client.put('/api/admin/roles/1',json={'permissions':[]}).status_code==400
    assert auth_client.delete('/api/admin/users/1/roles',json={'role_id':1}).status_code==400
    assert auth_client.put('/api/admin/users/1',json={'is_active':False}).status_code==400
    assert auth_client.post('/api/admin/users/3/roles',json={'roles':[{'role_id':4,'scope_branch_id':2}]}).status_code==400
    auth_client.login(3)
    assert auth_client.get('/admin/roles').status_code==403
    assert auth_client.get('/api/admin/roles').status_code==403
    assert auth_client.post('/api/admin/roles',json={'name':'bad'}).status_code==403


def test_admin_pages_render(auth_client):
    auth_client.login(1)
    for section in ('users','roles','permissions','audit'):
        assert auth_client.get('/admin/'+section).status_code==200
        assert auth_client.get('/api/admin/'+section).status_code==200
