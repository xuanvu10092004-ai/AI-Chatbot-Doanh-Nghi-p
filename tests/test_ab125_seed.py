"""Bổ sung AB 125: kiểm chứng dữ liệu, quyền và chạy lại trên MySQL thật."""
from pathlib import Path  # Tạo và kiểm tra đường dẫn file trong dự án.

import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.

from db import cursor, get_connection  # Mở cursor hoặc connection MySQL.
from init_db import execute_script, verify_counts  # Dùng cấu hình, script SQL và kiểm tra schema khởi tạo.


EXTENSION = Path(__file__).resolve().parents[1] / 'data/schema/extensions/08_air_blade_125_seed.sql'


def test_ab125_model_specs_and_variants_are_complete():
    with cursor() as cur:
        cur.execute('''SELECT p.model_name, p.segment, p.engine_cc, p.description,
                       s.engine_type,s.fuel_tank_l,s.weight_kg,s.brake_type,s.warranty
                       FROM products p JOIN product_specs s ON s.product_id=p.id
                       WHERE p.model_name=%s''', ('Air Blade 125',))
        models = cur.fetchall()
        assert len(models) == 1
        model = models[0]
        assert model['segment'] == 'tay_ga' and model['engine_cc'] == 125
        assert 'mô phỏng' in model['description'] and 'không phải' in model['description']
        assert all(model[key] for key in ('engine_type', 'fuel_tank_l', 'weight_kg', 'brake_type', 'warranty'))
        cur.execute('''SELECT pv.variant_name,pv.list_price,pv.cost_price
                       FROM product_variants pv JOIN products p ON p.id=pv.product_id
                       WHERE p.model_name=%s ORDER BY pv.list_price''', ('Air Blade 125',))
        assert cur.fetchall() == [
            {'variant_name': 'Air Blade 125 - Tiêu chuẩn - Đỏ đen', 'list_price': 42500000, 'cost_price': 38500000},
            {'variant_name': 'Air Blade 125 - Đặc biệt - Đen', 'list_price': 44500000, 'cost_price': 40500000},
            {'variant_name': 'Air Blade 125 - Thể thao - Xám đen', 'list_price': 46500000, 'cost_price': 42500000},
        ]


def test_guest_ab125_prices_match_base_sql_and_hide_cost(auth_client):
    auth_client.login(None)
    response = auth_client.post('/chat', json={'question': 'giá ab 125 bao nhiêu?'})
    assert response.status_code == 200
    data = response.get_json()
    with cursor() as cur:
        cur.execute('''SELECT pv.list_price FROM product_variants pv
                       JOIN products p ON p.id=pv.product_id
                       WHERE p.model_name=%s ORDER BY pv.list_price''', ('Air Blade 125',))
        expected = cur.fetchall()
    assert len(data['rows']) == len(expected) == 3
    assert {row['model_name'] for row in data['rows']} == {'Air Blade 125'}
    assert [row['list_price'] for row in data['rows']] == [row['list_price'] for row in expected]
    assert all('cost_price' not in row for row in data['rows'])
    denied = auth_client.post('/chat', json={'question': 'giá vốn ab 125'}).get_json()
    assert denied['access_denied'] is True and denied['rows'] == []


@pytest.mark.parametrize('user_id,branch_id', [(1, None), (3, 1), (4, 2)])
def test_ab125_available_stock_matches_scoped_base_sql(auth_client, user_id, branch_id):
    auth_client.login(user_id)
    response = auth_client.post('/chat', json={'question': 'ab 125 chi nhánh nào còn?'})
    assert response.status_code == 200
    data = response.get_json()
    with cursor() as cur:
        cur.execute('''SELECT b.code AS branch_code,pv.variant_name,i.quantity
                       FROM inventory i JOIN branches b ON b.id=i.branch_id
                       JOIN product_variants pv ON pv.id=i.variant_id
                       JOIN products p ON p.id=pv.product_id
                       WHERE p.model_name=%s AND i.quantity>0
                       AND (%s IS NULL OR i.branch_id=%s)
                       ORDER BY b.code,pv.variant_name''', ('Air Blade 125', branch_id, branch_id))
        expected = cur.fetchall()
    actual = [{'branch_code': r['branch_code'], 'variant_name': r['variant_name'], 'quantity': r['quantity']} for r in data['rows']]
    assert actual and sorted(actual, key=lambda r: (r['branch_code'], r['variant_name'])) == sorted(expected, key=lambda r: (r['branch_code'], r['variant_name']))
    assert all(r['quantity'] > 0 and r['model_name'] == 'Air Blade 125' for r in data['rows'])


def test_ab125_and_ab160_comparison_is_complete(auth_client):
    auth_client.login(None)
    response = auth_client.post('/chat', json={'question': 'so sánh ab 125 và ab 160'})
    assert response.status_code == 200
    data = response.get_json()
    with cursor() as cur:
        cur.execute('''SELECT p.model_name,pv.variant_name,pv.list_price FROM products p
                       JOIN product_variants pv ON pv.product_id=p.id
                       WHERE p.model_name IN (%s,%s) ORDER BY p.model_name,pv.list_price''', ('Air Blade 125', 'Air Blade 160'))
        expected = cur.fetchall()
    assert len(data['rows']) == len(expected) == 6
    assert {r['model_name'] for r in data['rows']} == {'Air Blade 125', 'Air Blade 160'}
    assert [{'model_name': r['model_name'], 'variant_name': r['variant_name'], 'list_price': r['list_price']} for r in data['rows']] == expected
    assert data['summary'] == 'So sánh thông số và giá niêm yết theo từng phiên bản có dữ liệu.'
    assert 'chưa đủ dữ liệu' not in data['answer']


def test_seed_rerun_does_not_duplicate_or_overwrite_inventory():
    connection = get_connection()
    variant_id = original_quantity = None
    try:
        before = verify_counts(connection)
        with connection.cursor(dictionary=True) as cur:
            cur.execute('''SELECT i.variant_id,i.quantity FROM inventory i
                           JOIN product_variants pv ON pv.id=i.variant_id
                           WHERE i.branch_id=%s AND pv.variant_name=%s''', (1, 'Air Blade 125 - Tiêu chuẩn - Đỏ đen'))
            row = cur.fetchone()
            variant_id, original_quantity = row['variant_id'], row['quantity']
            cur.execute('UPDATE inventory SET quantity=%s WHERE branch_id=%s AND variant_id=%s', (original_quantity + 1, 1, variant_id))
        connection.commit()
        for _ in range(2):
            execute_script(connection, EXTENSION)
        assert verify_counts(connection) == before
        with connection.cursor() as cur:
            cur.execute('SELECT quantity FROM inventory WHERE branch_id=%s AND variant_id=%s', (1, variant_id))
            assert cur.fetchone() == (original_quantity + 1,)
            cur.execute('''SELECT COUNT(*),SUM(i.quantity=0) FROM inventory i
                           JOIN product_variants pv ON pv.id=i.variant_id
                           JOIN products p ON p.id=pv.product_id WHERE p.model_name=%s''', ('Air Blade 125',))
            assert cur.fetchone() == (9, 2)
    finally:
        if variant_id is not None:
            with connection.cursor() as cur:
                cur.execute('UPDATE inventory SET quantity=%s WHERE branch_id=%s AND variant_id=%s', (original_quantity, 1, variant_id))
            connection.commit()
        connection.close()
