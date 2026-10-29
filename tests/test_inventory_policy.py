"""Kiểm thử quy tắc tồn kho, khả năng bán và phạm vi chi nhánh."""

import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.
from db import cursor  # Mở cursor hoặc connection MySQL.
from query_planner import plan_query  # Tạo SQL template cho intent được nhận diện.
from sql_service import answer_sql_question  # Thực thi câu hỏi SQL hoặc truy vấn đã kiểm tra.


@pytest.mark.parametrize('question,condition',[
    ('Kho nào sắp hết hàng','quantity > 0 AND quantity < 5'),
    ('Tồn kho sắp hết hàng NT01','quantity > 0 AND quantity < 5 AND branch_code=\'NT01\''),
    ('Xe nào hết hàng','quantity=0'),
])
def test_stock_matches_database_and_scope(question,condition):
    actual=answer_sql_question(question,1)
    with cursor() as cur:
        cur.execute('SELECT branch_code,branch_name,model_name,variant_name,quantity FROM v_ai_inventory WHERE '+condition)
        expected=cur.fetchall()
    assert sorted(actual.rows,key=str)==sorted(expected,key=str)
    if 'sắp' in question:
        assert all(1<=r['quantity']<=4 for r in actual.rows)
        assert '1–4' in actual.summary


@pytest.mark.parametrize('quantity,low',[(0,False),(1,True),(4,True),(5,False)])
def test_stock_boundaries(quantity,low):
    sql,params=plan_query('Kho nào sắp hết hàng','ask_stock')
    with cursor() as cur:
        cur.execute('SELECT i.branch_id,i.variant_id,i.quantity,b.code AS branch_code,pv.variant_name FROM inventory i JOIN branches b ON b.id=i.branch_id JOIN product_variants pv ON pv.id=i.variant_id LIMIT 1');row=cur.fetchone()
        try:
            cur.execute('UPDATE inventory SET quantity=%s WHERE branch_id=%s AND variant_id=%s',(quantity,row['branch_id'],row['variant_id']))
            # Truy vấn trong cùng transaction để kiểm tra điều kiện planner vừa tạo.
            cur.execute(sql,params)
            found=any(r['branch_code']==row['branch_code'] and r['variant_name']==row['variant_name'] for r in cur.fetchall())
            assert found==low
        finally:cur.execute('UPDATE inventory SET quantity=%s WHERE branch_id=%s AND variant_id=%s',(row['quantity'],row['branch_id'],row['variant_id']))


def test_low_stock_api_uses_sales_scope(auth_client):
    auth_client.login(3)
    data=auth_client.get('/api/low-stock?size=100').get_json()
    with cursor() as cur:
        cur.execute('SELECT COUNT(*) AS n FROM inventory WHERE branch_id=1 AND quantity>0 AND quantity<5');expected=cur.fetchone()['n']
    assert data['total']==expected
    assert all(r['branch_code']=='NT01' and 1<=r['quantity']<=4 for r in data['rows'])

