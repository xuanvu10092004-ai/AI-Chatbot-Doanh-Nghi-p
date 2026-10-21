import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.
import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.
from flask.testing import FlaskClient  # Dùng client Flask để gửi request trong kiểm thử.
from app import app  # Dùng ứng dụng Flask đang được kiểm thử.
from db import cursor  # Mở cursor hoặc connection MySQL.


class AuthenticatedClient(FlaskClient):
    def open(self,*args,**kwargs):
        method=kwargs.get('method','GET').upper()
        if method in {'POST','PUT','PATCH','DELETE'} and not kwargs.pop('without_csrf',False):
            with self.session_transaction() as state:token=state.get('csrf_token','')
            headers=dict(kwargs.get('headers') or {})
            headers.setdefault('X-CSRF-Token',token);kwargs['headers']=headers
        return super().open(*args,**kwargs)

    def login(self,user_id=None):
        self.get('/login')
        if user_id is None:
            response=self.post('/guest')
        else:
            with cursor() as cur:
                cur.execute('SELECT email FROM users WHERE id=%s',(user_id,));email=cur.fetchone()['email']
            response=self.post('/login',data={'email':email,'password':os.environ['DEMO_ACCOUNT_PASSWORD']})
        assert response.status_code==302
        return self

    def post_as(self,user_id,*args,**kwargs):
        self.login(user_id)
        return self.post(*args,**kwargs)


app.test_client_class=AuthenticatedClient

@pytest.fixture
def auth_client():
    app.config.update(TESTING=True,SESSION_COOKIE_SECURE=False)
    return app.test_client()
