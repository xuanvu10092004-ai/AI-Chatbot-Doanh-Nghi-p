import os
from db import cursor


def test_new_user_must_change_password_and_audit_has_no_hash(auth_client):
    auth_client.login(1)
    response=auth_client.post('/api/admin/users',json={'email':'temporary.portal.test@example.test','full_name':'Temporary Portal Test','home_branch_id':1,'password':'TemporaryPass123!','roles':[{'role_id':3,'scope_branch_id':1}]})
    assert response.status_code==200;user_id=response.get_json()['id']
    try:
        client=auth_client.__class__(auth_client.application);client.get('/login')
        login=client.post('/login',data={'email':'temporary.portal.test@example.test','password':'TemporaryPass123!'})
        assert login.location=='/change-password'
        assert client.get('/dashboard').location=='/change-password'
        assert client.post('/change-password',data={'password':'ReplacementPass123!','confirm':'ReplacementPass123!'}).status_code==302
        assert client.get('/dashboard').status_code==200
        with cursor() as c:
            c.execute("SELECT after_json FROM rbac_audit_log WHERE target_type='user' AND target_id=%s ORDER BY id LIMIT 1",(user_id,));record=c.fetchone()['after_json']
            assert 'roles' in record and 'password_hash' not in record and 'TemporaryPass123!' not in record
    finally:
        with cursor() as c:
            c.execute('DELETE FROM user_roles WHERE user_id=%s',(user_id,));c.execute('DELETE FROM chat_sessions WHERE user_id=%s',(user_id,));c.execute('UPDATE rbac_audit_log SET actor_user_id=NULL WHERE actor_user_id=%s',(user_id,));c.execute('DELETE FROM users WHERE id=%s',(user_id,))


def test_missing_branch_fails_closed_and_own_dashboard(auth_client):
    auth_client.login(3)
    with cursor() as c:
        c.execute('UPDATE user_roles SET scope_branch_id=NULL WHERE user_id=3');c.execute('UPDATE users SET home_branch_id=NULL WHERE id=3')
    try:assert auth_client.get('/api/dashboard/inventory').status_code==403
    finally:
        with cursor() as c:c.execute('UPDATE user_roles SET scope_branch_id=1 WHERE user_id=3');c.execute('UPDATE users SET home_branch_id=1 WHERE id=3')


def test_rbac_changes_increment_version_atomically(auth_client):
    auth_client.login(1)
    with cursor() as c:c.execute('SELECT version FROM rbac_meta WHERE id=1');before=c.fetchone()['version']
    assert auth_client.put('/api/admin/users/1',json={'is_active':False}).status_code==400
    with cursor() as c:c.execute('SELECT version FROM rbac_meta WHERE id=1');assert c.fetchone()['version']==before
    assert auth_client.put('/api/admin/users/3',json={'unlock':True}).status_code==200
    with cursor() as c:c.execute('SELECT version FROM rbac_meta WHERE id=1');assert c.fetchone()['version']==before+1


def test_own_scope_filters_chatbot_views():
    from sql_service import _execute_text_to_sql
    from access_control import permitted_views
    rows=_execute_text_to_sql('SELECT customer_id FROM v_ai_orders',allowed_views=permitted_views(1),own_user_id=101)
    assert all(r['customer_id']==101 for r in rows)
    with cursor() as c:c.execute('SELECT COUNT(*) AS n FROM orders WHERE customer_id=101');expected=c.fetchone()['n']
    assert len(rows)==expected


def test_app_database_user_has_no_ddl():
    from mysql.connector import Error
    import pytest
    with cursor() as c:
        c.execute('SELECT CURRENT_USER() AS who');assert c.fetchone()['who']==f"{os.environ['DB_USER']}@localhost"
        with pytest.raises(Error) as error:c.execute('CREATE TABLE forbidden_test_table(id INT)')
        assert error.value.errno==1142


def test_audit_scope_and_global_rbac_fail_closed(auth_client):
    with cursor() as c:
        c.execute("SELECT id,code FROM permissions WHERE code IN ('audit:read','rbac:manage')");pids={r['code']:r['id'] for r in c.fetchall()}
        for pid in pids.values():c.execute("INSERT INTO role_permissions(role_id,permission_id,data_scope) VALUES(3,%s,'branch')",(pid,))
    try:
        auth_client.login(3)
        data=auth_client.get('/api/admin/audit').get_json()
        with cursor() as c:c.execute('SELECT id FROM users WHERE home_branch_id=1');allowed={r['id'] for r in c.fetchall()}
        assert data['rows'] and all(r['actor_user_id'] in allowed for r in data['rows'])
        assert all(r['user_id'] in allowed for r in data['chatbot'])
        assert auth_client.get('/api/admin/roles').status_code==403
    finally:
        with cursor() as c:
            for pid in pids.values():c.execute('DELETE FROM role_permissions WHERE role_id=3 AND permission_id=%s',(pid,))
