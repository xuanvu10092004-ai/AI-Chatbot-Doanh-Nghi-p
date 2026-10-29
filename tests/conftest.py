"""Fixture dùng chung cho ứng dụng Flask, MySQL và dữ liệu kiểm thử."""

import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.
import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.
from pathlib import Path
from uuid import uuid4
from flask.testing import FlaskClient  # Dùng client Flask để gửi request trong kiểm thử.
from app import app  # Dùng ứng dụng Flask đang được kiểm thử.
from db import cursor  # Mở cursor hoặc connection MySQL.


def pytest_configure(config):
    # Không phụ thuộc thư mục Temp/ACL của máy đã chạy pytest trước đó.
    if config.option.basetemp is None:
        config.option.basetemp = str(Path(__file__).resolve().parents[1] /
                                     'data/exports' / ('pytest-' + uuid4().hex))


@pytest.fixture(autouse=True)
def preserve_workbooks():
    # Mỗi test được bắt đầu từ cùng workbook, không mang theo khách thử của test trước.
    root = Path(__file__).resolve().parents[1]
    paths = (root/'data/source/honda_dataset_khach_hang_san_pham.xlsx',
             root/'data/exports/honda_chatbot_synced.xlsx')
    originals = {path: path.read_bytes() if path.exists() else None for path in paths}
    yield
    for path, content in originals.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(content)


@pytest.fixture
def adv_inventory():
    """ADV là dữ liệu người dùng thêm ở máy cũ; test tự tạo/dọn trên MySQL thật."""
    product_id = variant_id = None
    try:
        with cursor() as cur:
            cur.execute('INSERT INTO products(model_name,segment,engine_cc,description) VALUES(%s,%s,%s,%s)',
                        ('ADV 160', 'tay_ga', 160, 'Dữ liệu mô phỏng cho kiểm thử đồng bộ'))
            product_id = cur.lastrowid
            cur.execute('INSERT INTO product_variants(product_id,variant_name,list_price,cost_price) VALUES(%s,%s,%s,%s)',
                        (product_id, 'ADV 160 - Kiểm thử', 10000000, 9000000))
            variant_id = cur.lastrowid
            cur.execute('INSERT INTO inventory(branch_id,variant_id,quantity) VALUES(%s,%s,%s)',
                        (3, variant_id, 10))
        yield
    finally:
        with cursor() as cur:
            if variant_id is not None:
                cur.execute('DELETE FROM inventory WHERE variant_id=%s', (variant_id,))
                cur.execute('DELETE FROM product_variants WHERE id=%s', (variant_id,))
            if product_id is not None:
                cur.execute('DELETE FROM products WHERE id=%s', (product_id,))


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
