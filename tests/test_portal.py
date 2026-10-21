import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.
from db import cursor  # Mở cursor hoặc connection MySQL.


@pytest.mark.parametrize('user_id,path',[(1,'/dashboard'),(3,'/customers'),(3,'/inventory'),(5,'/inventory'),(8,'/chat')])
def test_permitted_pages(auth_client,user_id,path):
    auth_client.login(user_id);assert auth_client.get(path).status_code==200


def test_menu_role_visibility(auth_client):
    auth_client.login(5)
    text=auth_client.get('/dashboard').get_data(as_text=True)
    assert '/admin/' not in text and 'href="/dashboard#revenue"' not in text
    assert 'href="/inventory"' in text
    assert auth_client.get('/customers').status_code==403
    auth_client.login(None)
    text=auth_client.get('/chat').get_data(as_text=True)
    assert 'href="/chat"' in text and 'href="/inventory"' not in text
    assert 'demoUser' not in text


def test_business_api_scope_pagination_and_sort(auth_client):
    auth_client.login(3)
    data=auth_client.get('/api/inventory?size=5').get_json()
    assert len(data['rows'])==5 and data['total']==31
    assert {row['branch_code'] for row in data['rows']}=={'NT01'}
    assert auth_client.get('/api/inventory?branch=NT02').get_json()['total']==0
    assert auth_client.get('/api/inventory?sort=quantity;DROP').status_code==400
    with cursor() as c:c.execute('SELECT COUNT(*) AS n FROM customer_profiles cp JOIN users u ON u.id=cp.user_id WHERE u.home_branch_id=1');expected=c.fetchone()['n']
    assert auth_client.get('/api/customers').get_json()['total']==expected


def test_legacy_endpoints_and_soon(auth_client):
    auth_client.login(1)
    for path in ('/quotes','/opportunities','/api/quotes','/api/opportunities'):assert auth_client.get(path).status_code==501
    assert auth_client.get('/bookings').status_code==200
    assert isinstance(auth_client.get('/api/bookings').get_json()['rows'],list)
    auth_client.login(5)
    assert auth_client.get('/api/quotes').status_code==403
