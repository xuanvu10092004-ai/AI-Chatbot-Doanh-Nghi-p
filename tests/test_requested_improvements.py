"""Hồi quy cho các tình huống trong ảnh và công cụ nghiệp vụ mới (MySQL thật)."""
from datetime import datetime,timedelta  # Tạo, so sánh hoặc định dạng ngày giờ.
from zoneinfo import ZoneInfo  # Tính thời gian theo múi giờ Việt Nam.
import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.
from db import cursor  # Mở cursor hoặc connection MySQL.
from customer_chat import parse_customer_values  # Phân tích thông tin khách gửi qua chat.
from sql_service import answer_sql_question  # Thực thi câu hỏi SQL hoặc truy vấn đã kiểm tra.
from test_customer_input import clean_customer_input,BATCHES  # Dùng fixture và helper tạo/dọn batch nhập khách.
from test_document_uploads import document_storage  # Dùng fixture lưu trữ và helper upload tài liệu.


def test_comma_customer_values_in_any_contact_order():
    a=parse_customer_values('Nguyễn Trí Thường, 0935253359, example@customer-input.test, 123 Đoàn Kết, Nha Trang, Khánh Hòa')
    b=parse_customer_values('Nguyễn Trí Thường, example@customer-input.test, 0935253359')
    assert a['full_name']==b['full_name']=='Nguyễn Trí Thường'
    assert a['email']==b['email']=='example@customer-input.test'
    assert a['phone']==b['phone']=='0935253359'
    assert a['address']=='123 Đoàn Kết, Nha Trang, Khánh Hòa'


def test_screenshot_customer_and_unrelated_stock_question(auth_client,clean_customer_input,monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    monkeypatch.setenv('APP_ENV','dev')
    auth_client.login(3)
    first=auth_client.post('/chat',json={'question':'thêm nhanh khách hàng với thông tin như sau: Nguyễn Trí Thường, 0935253359, screenshot@customer-input.test, 123 Đoàn Kết, Nha Trang, Khánh Hòa'}).get_json()
    draft=first['customer_draft'];BATCHES.add(draft['id'])
    assert draft['valid'],draft
    row=draft['rows'][0]['data']
    assert row['full_name']=='Nguyễn Trí Thường' and row['phone']=='0935253359'
    answer=auth_client.post('/chat',json={'question':'hiện tại chi nhánh nha trang sản phẩm nào gần hết hàng'}).get_json()
    assert answer['type']=='SQL' and not answer['access_denied']
    with cursor() as cur:
        cur.execute('SELECT branch_code,branch_name,model_name,variant_name,quantity FROM v_ai_inventory WHERE branch_code=%s AND quantity>0 AND quantity<5',('NT01',));expected=cur.fetchall()
    assert sorted(answer['rows'],key=str)==sorted(expected,key=str)
    after=auth_client.get('/api/customer-input/'+str(draft['id'])).get_json()
    assert after['version']==draft['version'] and after['rows'][0]['data']==row


def test_comma_followup_captures_all_contacts(auth_client,clean_customer_input):
    auth_client.login(3)
    draft=auth_client.post('/chat',json={'question':'Thêm khách mua xe'}).get_json()['customer_draft'];BATCHES.add(draft['id'])
    reply=auth_client.post('/chat',json={'question':'Tên Người Mua, followup@customer-input.test, 0901234567'}).get_json()['customer_draft']
    row=reply['rows'][0]['data']
    assert row['full_name']=='Tên Người Mua' and row['phone']=='0901234567' and row['email']=='followup@customer-input.test'


@pytest.mark.parametrize('location,codes',[('Nha Trang',{'NT01','NT02'}),('Cam Ranh',{'CR01'})])
def test_low_stock_city_matches_independent_sql(location,codes):
    result=answer_sql_question('Hiện tại chi nhánh '+location+' sản phẩm nào gần hết hàng',1)
    with cursor() as cur:
        cur.execute('SELECT branch_code,branch_name,model_name,variant_name,quantity FROM v_ai_inventory WHERE quantity>0 AND quantity<5')
        expected=[r for r in cur.fetchall() if r['branch_code'] in codes]
    assert sorted(result.rows,key=str)==sorted(expected,key=str)


def test_total_inventory_has_every_variant_and_branch(auth_client,monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY',raising=False);monkeypatch.setenv('APP_ENV','dev')
    auth_client.login(1)
    data=auth_client.post('/chat',json={'question':'Tổng tồn kho'}).get_json()
    with cursor() as cur:
        cur.execute('SELECT branch_code,branch_name,model_name,variant_name,quantity FROM v_ai_inventory');expected=cur.fetchall()
    assert sorted(data['rows'],key=str)==sorted(expected,key=str)
    assert str(sum(r['quantity'] for r in expected)) in data['summary']


def test_customer_summary_uses_filters_not_current_page(auth_client):
    auth_client.login(3)
    data=auth_client.get('/api/customers?size=1&status=Đã mua').get_json()
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM users u JOIN customer_profiles cp ON cp.user_id=u.id WHERE u.home_branch_id=1 AND cp.status='Đã mua'");expected=cur.fetchone()['n']
    assert len(data['rows'])<=1 and data['summary']['total']==expected
    assert sum(r['value'] for r in data['summary']['distribution'])==expected
    assert auth_client.get('/api/customers?branch=NT02').get_json()['summary']['total']==0


@pytest.fixture
def booking_cleanup():
    ids=[]
    yield ids
    with cursor() as cur:
        for target in ids:
            cur.execute("DELETE FROM rbac_audit_log WHERE target_type='booking' AND target_id=%s",(target,))
            cur.execute('DELETE FROM service_bookings WHERE id=%s',(target,))


def booking_data(branch=1):
    with cursor() as cur:
        cur.execute("SELECT id FROM users WHERE user_type='customer' AND home_branch_id=%s ORDER BY id LIMIT 1",(branch,));customer=cur.fetchone()['id']
    day=(datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))+timedelta(days=7)).replace(hour=9,minute=0,second=0,microsecond=0,tzinfo=None)
    return dict(branch_id=branch,customer_id=customer,scheduled_at=day.isoformat(),service_type='repair',vehicle_description='Xe kiểm thử',license_plate='79-TEST',notes='Kiểm thử tự động')


def test_booking_lifecycle_scope_duplicates_and_stale_updates(auth_client,booking_cleanup):
    auth_client.login(3);data=booking_data()
    response=auth_client.post('/api/bookings',json=data);assert response.status_code==201,response.json
    target=response.json['id'];booking_cleanup.append(target)
    assert auth_client.post('/api/bookings',json=data).status_code==409
    assert auth_client.post('/api/bookings',json=booking_data(2)).status_code==403
    assert auth_client.patch('/api/bookings/'+str(target),json={'status':'confirmed','version':1}).status_code==403
    auth_client.login(4)
    assert target not in {r['id'] for r in auth_client.get('/api/bookings').json['rows']}
    assert auth_client.patch('/api/bookings/'+str(target),json={'status':'cancelled','version':1}).status_code==404
    auth_client.login(5)
    assert auth_client.patch('/api/bookings/'+str(target),json={'status':'confirmed','version':1}).status_code==200
    assert auth_client.patch('/api/bookings/'+str(target),json={'status':'completed','version':1}).status_code==409
    assert auth_client.patch('/api/bookings/'+str(target),json={'status':'completed','version':2}).status_code==200
    assert auth_client.patch('/api/bookings/'+str(target),json={'status':'cancelled','version':3}).status_code==409


@pytest.mark.parametrize('changes',[{'service_type':'invalid'},{'scheduled_at':'2020-01-01T09:00'},{'scheduled_at':'invalid'},{'vehicle_description':''}])
def test_invalid_bookings_rejected(auth_client,changes):
    auth_client.login(3)
    assert auth_client.post('/api/bookings',json={**booking_data(),**changes}).status_code==400


def test_booking_guest_and_customer_ownership(auth_client,booking_cleanup):
    auth_client.login(None)
    assert auth_client.get('/api/bookings').status_code==403
    auth_client.login(8)
    data=booking_data()
    assert data['customer_id']!=8
    assert auth_client.post('/api/bookings',json=data).status_code==403
    data['customer_id']=8
    assert auth_client.post('/api/bookings',json=data).status_code==403
    data['service_type']='maintenance'
    response=auth_client.post('/api/bookings',json=data);assert response.status_code==201
    target=response.json['id'];booking_cleanup.append(target)
    assert all(r['customer_id']==8 for r in auth_client.get('/api/bookings').json['rows'])
    assert auth_client.patch('/api/bookings/'+str(target),json={'status':'cancelled','version':1}).status_code==200


def test_catalog_create_edit_preserves_order_prices_and_readonly_bot(auth_client):
    auth_client.login(3)
    assert auth_client.get('/api/catalog').status_code==403
    assert auth_client.post('/api/catalog',json={}).status_code==403
    auth_client.login(1)
    data=dict(model_name='Mẫu thử đời xe',variant_name='Mẫu thử - Đỏ',segment='tay_ga',engine_cc=125,list_price=96500000,model_year=2026,lifecycle='current')
    response=auth_client.post('/api/catalog',json=data);assert response.status_code==201,response.json
    target=response.json['id'];product_id=None
    try:
        row=next(r for r in auth_client.get('/api/catalog').json['rows'] if r['id']==target);product_id=row['product_id']
        with cursor() as cur:
            cur.execute('SELECT COUNT(*) AS n,SUM(quantity) AS q FROM inventory WHERE variant_id=%s',(target,));stock=cur.fetchone()
            cur.execute('SELECT COUNT(*) AS n FROM branches');branches=cur.fetchone()['n']
            cur.execute('SELECT order_id,variant_id,unit_price FROM order_items ORDER BY order_id,variant_id');prices=cur.fetchall()
        assert stock['n']==branches and stock['q']==0
        changed={**data,'list_price':100500000,'lifecycle':'previous','model_year':2024,'version':row['version']}
        assert auth_client.put('/api/catalog/'+str(target),json=changed).status_code==200
        assert auth_client.put('/api/catalog/'+str(target),json=changed).status_code==409
        result=answer_sql_question('Giá các mẫu xe đời 2024',1)
        assert any(r['variant_name']==data['variant_name'] and r['list_price']==100500000 and r['model_year']==2024 and r['lifecycle']=='previous' for r in result.rows)
        with cursor() as cur:
            cur.execute('SELECT list_price FROM product_variants WHERE id=%s',(target,));assert cur.fetchone()['list_price']==100500000
            cur.execute('SELECT order_id,variant_id,unit_price FROM order_items ORDER BY order_id,variant_id');assert cur.fetchall()==prices
            cur.execute('SELECT action FROM rbac_audit_log WHERE target_type=%s AND target_id=%s',('variant',target));assert {r['action'] for r in cur.fetchall()}=={'catalog_create','catalog_update'}
    finally:
        with cursor() as cur:
            cur.execute("DELETE FROM rbac_audit_log WHERE target_type='variant' AND target_id=%s",(target,))
            cur.execute('DELETE FROM inventory WHERE variant_id=%s',(target,));cur.execute('DELETE FROM vehicle_releases WHERE variant_id=%s',(target,));cur.execute('DELETE FROM product_variants WHERE id=%s',(target,))
            if product_id:cur.execute('DELETE FROM products WHERE id=%s',(product_id,))


def test_access_management_is_single_navigation_tool(auth_client):
    auth_client.login(1)
    text=auth_client.get('/admin/users').get_data(as_text=True)
    sidebar=text.split('<aside',1)[1].split('</aside>',1)[0]
    assert sidebar.count('Quản trị truy cập')==1
    assert '/admin/roles' not in sidebar and '/admin/permissions' not in sidebar
    assert 'Vai trò & ma trận quyền' in text and 'Danh mục quyền' in text
    assert 'src="/static/images/logo.jpg"' in text and 'Dữ liệu mô phỏng' in text


@pytest.mark.parametrize('changes',[{'list_price':-1},{'list_price':True},{'engine_cc':'abc'},{'model_year':1800},{'lifecycle':'invalid'},{'variant_name':'x'*101}])
def test_catalog_invalid_changes_have_no_writes(auth_client,changes):
    auth_client.login(1)
    data=dict(model_name='Không được tạo',variant_name='Phiên bản thử',segment='tay_ga',engine_cc=125,list_price=96500000,model_year=2026,lifecycle='current')
    with cursor() as cur:cur.execute('SELECT COUNT(*) AS n FROM product_variants');before=cur.fetchone()['n']
    assert auth_client.post('/api/catalog',json={**data,**changes}).status_code==400
    with cursor() as cur:cur.execute('SELECT COUNT(*) AS n FROM product_variants');assert cur.fetchone()['n']==before
