import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.
import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.
from db import cursor  # Mở cursor hoặc connection MySQL.
from llm_sql import generate_query  # Sinh truy vấn SQL và bind literal thành tham số.
from sql_service import _execute_text_to_sql  # Thực thi câu hỏi SQL hoặc truy vấn đã kiểm tra.

pytestmark = pytest.mark.skipif(not os.getenv('GROQ_API_KEY'), reason='GROQ_API_KEY is not configured')


@pytest.mark.parametrize('question,views,oracle', [
    ('Liệt kê tên mẫu xe tay ga có phiên bản giá niêm yết dưới 50 triệu VNĐ, mỗi tên xuất hiện một lần, chỉ trả cột model_name.',
     {'v_ai_products'}, "SELECT DISTINCT p.model_name FROM products p JOIN product_variants pv ON pv.product_id = p.id WHERE p.segment = 'tay_ga' AND pv.list_price < 50000000"),
    ('Tổng số xe tồn theo mã chi nhánh, trả cột branch_code và total_stock, sắp xếp theo branch_code.',
     {'v_ai_products', 'v_ai_inventory'}, 'SELECT b.code AS branch_code, SUM(i.quantity) AS total_stock FROM inventory i JOIN branches b ON b.id = i.branch_id GROUP BY b.code ORDER BY b.code'),
    ('So sánh giá niêm yết Vision 110 và Lead 125: mỗi mẫu một dòng với model_name và MIN(list_price) AS min_price.',
     {'v_ai_products'}, "SELECT p.model_name, MIN(pv.list_price) AS min_price FROM products p JOIN product_variants pv ON pv.product_id = p.id WHERE p.model_name IN ('Vision 110', 'Lead 125') GROUP BY p.model_name"),
])
def test_live_generated_query_against_base_sql(question, views, oracle):
    sql, params = generate_query(question, frozenset(views))
    actual = _execute_text_to_sql(sql, params, allowed_views=frozenset(views))
    with cursor() as cur:
        cur.execute(oracle)
        expected = cur.fetchall()
    assert sorted(actual, key=lambda r: str(r)) == sorted(expected, key=lambda r: str(r))
