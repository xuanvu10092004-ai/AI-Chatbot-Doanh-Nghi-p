import os
from datetime import datetime,timedelta
from db import cursor
from app import app


def email(user_id):
    with cursor() as c:
        c.execute('SELECT email FROM users WHERE id=%s',(user_id,));return c.fetchone()['email']


def test_unauthenticated_redirect_and_api_401(auth_client):
    assert auth_client.get('/chat').status_code==302
    assert '/login?next=' in auth_client.get('/dashboard').location
    assert auth_client.get('/api/dashboard').status_code==401


def test_login_logout_and_csrf(auth_client):
    auth_client.login(3)
    assert auth_client.get('/chat').status_code==200
    assert auth_client.post('/logout',without_csrf=True).status_code==403
    assert auth_client.post('/logout').status_code==302
    with auth_client.session_transaction() as state:assert 'user_id' not in state


def test_safe_next_and_session_fixation(auth_client):
    auth_client.get('/login?next=https://evil.com')
    with auth_client.session_transaction() as s:s['old_marker']='old'
    response=auth_client.post('/login',data={'email':email(3),'password':os.environ['DEMO_ACCOUNT_PASSWORD'],'next':'https://evil.com'})
    assert response.location=='/dashboard'
    with auth_client.session_transaction() as s:assert 'old_marker' not in s


def test_failed_login_lock_and_invalid_hash(auth_client):
    with cursor() as c:c.execute('UPDATE users SET failed_login_count=0,locked_until=NULL WHERE id=%s',(9,))
    try:
        auth_client.get('/login')
        for _ in range(5):
            response=auth_client.post('/login',data={'email':email(9),'password':'wrong-password'})
            assert response.status_code==401
            assert 'Email hoặc mật khẩu không đúng' in response.get_data(as_text=True)
        with cursor() as c:
            c.execute('SELECT failed_login_count,locked_until FROM users WHERE id=9');row=c.fetchone()
            assert row['failed_login_count']==5 and row['locked_until']>datetime.now()
        assert auth_client.post('/login',data={'email':email(9),'password':os.environ['DEMO_ACCOUNT_PASSWORD']}).status_code==401
        assert auth_client.post('/login',data={'email':email(101),'password':'anything'}).status_code==401
    finally:
        with cursor() as c:c.execute('UPDATE users SET failed_login_count=0,locked_until=NULL WHERE id IN (9,101)')


def test_expired_role_is_not_effective(auth_client):
    auth_client.login(3)
    with cursor() as c:c.execute('UPDATE user_roles SET expires_at=%s WHERE user_id=3',(datetime.now()-timedelta(days=1),))
    try:assert auth_client.get('/chat').status_code==403
    finally:
        with cursor() as c:c.execute('UPDATE user_roles SET expires_at=NULL WHERE user_id=3')


def test_permission_revocation_immediate(auth_client):
    auth_client.login(3)
    with cursor() as c:
        c.execute("SELECT permission_id,data_scope FROM role_permissions WHERE role_id=3 AND permission_id=(SELECT id FROM permissions WHERE code='kb:public:read')");row=c.fetchone()
        c.execute('DELETE FROM role_permissions WHERE role_id=3 AND permission_id=%s',(row['permission_id'],))
    try:assert auth_client.get('/chat').status_code==403
    finally:
        with cursor() as c:c.execute('INSERT INTO role_permissions(role_id,permission_id,data_scope) VALUES(3,%s,%s)',(row['permission_id'],row['data_scope']))


def test_security_headers(auth_client):
    response=auth_client.get('/login')
    assert response.headers['X-Frame-Options']=='DENY'
    assert "default-src 'self'" in response.headers['Content-Security-Policy']
