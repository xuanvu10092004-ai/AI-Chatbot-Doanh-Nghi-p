import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.
from db import cursor  # Mở cursor hoặc connection MySQL.


@pytest.mark.parametrize('user_id,branch',[(3,1),(4,2),(6,None)])
def test_kpis_match_independent_sql(auth_client,user_id,branch):
    auth_client.login(user_id)
    response=auth_client.get('/api/dashboard/orders');assert response.status_code==200
    where=' WHERE o.branch_id=%s' if branch else ''
    with cursor() as c:
        c.execute('SELECT COUNT(*) AS orders,SUM((SELECT SUM(oi.quantity*oi.unit_price) FROM order_items oi WHERE oi.order_id=o.id)-o.discount_amount) AS net_revenue FROM orders o'+where,(branch,) if branch else ())
        expected=c.fetchone()
    actual=response.get_json()['rows'][0]
    assert actual['orders']==expected['orders'] and int(actual['net_revenue'])==expected['net_revenue']


def test_technician_widgets_and_api_denial(auth_client):
    auth_client.login(5)
    response=auth_client.get('/dashboard');assert response.status_code==200
    assert 'data-widget="orders"' not in response.get_data(as_text=True)
    assert 'data-widget="inventory"' in response.get_data(as_text=True)
    assert auth_client.get('/api/dashboard/orders').status_code==403
    assert auth_client.get('/api/dashboard/profit').status_code==403
    with cursor() as c:
        c.execute('SELECT SUM(quantity) AS total_stock,SUM(quantity=0) AS empty_rows FROM inventory WHERE branch_id=1');expected=c.fetchone()
    actual=auth_client.get('/api/dashboard/inventory').get_json()['rows'][0]
    assert int(actual['total_stock'])==expected['total_stock'] and int(actual['empty_rows'])==expected['empty_rows']


def test_all_widget_routes_and_customer_status(auth_client):
    auth_client.login(1)
    from dashboard_service import WIDGETS  # Dùng truy vấn widget và scope quyền.
    for name in WIDGETS:assert auth_client.get('/api/dashboard/'+name).status_code==200
    with cursor() as c:
        c.execute('SELECT status AS label,COUNT(*) AS value FROM customer_profiles GROUP BY status ORDER BY value DESC,label');expected=c.fetchall()
    assert auth_client.get('/api/dashboard/customer-status').get_json()['rows']==expected
