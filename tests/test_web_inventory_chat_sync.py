"""Kiểm thử đồng bộ tồn kho hiển thị trên web và trong hội thoại chatbot."""

from db import cursor  # Mở cursor hoặc connection MySQL.
from query_plans import plan_query  # Tạo kế hoạch truy vấn tồn kho theo câu hỏi.
from sql_service import answer_sql_question  # Thực thi câu hỏi SQL hoặc truy vấn đã kiểm tra.


def test_chat_reads_web_inventory_for_adv_at_cr01(adv_inventory):
    question = 'xe ADV 160 ở kho CR01 có mấy chiếc'
    sql, params = plan_query(question, 'ask_stock')
    assert 'SUM(quantity) AS total_stock' in sql
    assert params[0] == 'CR01'
    assert '%ADV%160%' in params

    with cursor() as cur:
        cur.execute(
            'SELECT COALESCE(SUM(quantity), 0) AS total '
            'FROM v_ai_inventory WHERE branch_code=%s AND model_name LIKE %s',
            ('CR01', '%ADV%160%'),
        )
        expected = int(cur.fetchone()['total'])

    result = answer_sql_question(question, 1)
    assert int(result.rows[0]['total_stock']) == expected
