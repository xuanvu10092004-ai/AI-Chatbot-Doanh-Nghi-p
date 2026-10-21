import json  # Đọc hoặc ghi dữ liệu JSON trong luồng xử lý của file.
from types import SimpleNamespace  # Tạo response giả cho client model trong test.
import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.
from db import cursor  # Mở cursor hoặc connection MySQL.
from app import app  # Dùng ứng dụng Flask đang được kiểm thử.
from query_plans import plan_query  # Tạo kế hoạch truy vấn tồn kho theo câu hỏi.
from routing import route_question  # Phân loại câu hỏi SQL/RAG và nhãn module.
from access_control import detect_intent, permitted_views  # Dùng session, intent và quyền của chatbot.
from llm_sql import bind_literals, generate_query  # Sinh truy vấn SQL và bind literal thành tham số.
from sql_service import _execute_text_to_sql  # Thực thi câu hỏi SQL hoặc truy vấn đã kiểm tra.


@pytest.mark.parametrize('question,model', [
    ('giá ab 160 bao nhiêu', 'Air Blade 160'),
    ('gia AB160 bao nhieu', 'Air Blade 160'),
    ('thông tin sh mode 125', 'SH Mode 125'),
    ('thong tin shmode125', 'SH Mode 125'),
    ('lead 125 giá bao nhiêu', 'Lead 125'),
    ('giá vario160', 'Vario 160'),
    ('giá future 125', 'Future 125 FI'),
    ('thông số winner x', 'Winner X'),
    ('giá blade 110', 'Blade 110'),
    ('giá wave alpha 110', 'Wave Alpha 110'),
])
def test_aliases_and_information_use_real_catalog(question, model):
    assert route_question(question)['type'] == 'SQL'
    query, params = plan_query(question, detect_intent(question))
    actual = _execute_text_to_sql(query, params, allowed_views=permitted_views(None))
    with cursor() as cur:
        cur.execute('SELECT list_price FROM product_variants pv JOIN products p ON p.id = pv.product_id WHERE p.model_name = %s ORDER BY list_price', (model,))
        expected = [row['list_price'] for row in cur.fetchall()]
    assert actual and {r['model_name'] for r in actual} == {model}
    assert [r['list_price'] for r in actual] == expected
    assert 'variants' not in actual[0]


def test_ab125_is_not_replaced_with_ab160():
    query, params = plan_query('giá ab 125 bao nhiêu', 'ask_price_list')
    rows = _execute_text_to_sql(query, params, allowed_views=permitted_views(None))
    assert len(rows) == 3 and {r['model_name'] for r in rows} == {'Air Blade 125'}
    with cursor() as cur:
        cur.execute('SELECT pv.list_price FROM product_variants pv JOIN products p ON p.id=pv.product_id WHERE p.model_name=%s ORDER BY pv.list_price', ('Air Blade 125',))
        expected = cur.fetchall()
    assert [r['list_price'] for r in rows] == [r['list_price'] for r in expected]


def test_stock_question_counts_motorcycles_not_rows():
    query, params = plan_query('hàng tồn kho còn bao nhiêu', 'ask_stock')
    rows = _execute_text_to_sql(query, params, allowed_views=permitted_views(3), scope_branch_ids=[1])
    with cursor() as cur:
        cur.execute('SELECT SUM(quantity) AS n FROM inventory WHERE branch_id = %s', (1,))
        expected = cur.fetchone()['n']
    assert rows == [{'total_stock': expected}]


def test_public_specs_are_not_internal_procedures():
    assert detect_intent('thông số kỹ thuật SH Mode 125') == 'ask_price_list'
    assert detect_intent('quy trình kỹ thuật SH Mode 125') == 'ask_tech_procedure'
    assert detect_intent('giá nhập AB 160') == 'ask_cost_margin'
    assert route_question('xe ga dưới 50 triệu')['type'] == 'SQL'


def test_rendered_prices_keep_every_digit():
    from answer_renderer import render_rows  # Định dạng kết quả truy vấn thành nội dung hiển thị.
    result = render_rows([{'model_name': 'Air Blade 160', 'list_price': 57500000}, {'list_price': 60500000}])
    assert '57.500.000 VNĐ' in result and '60.500.000 VNĐ' in result
    assert '57.500 VNĐ' not in result


def test_live_mode_sql_does_not_rewrite_numbers(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    def forbidden(*args):
        pytest.fail('The answer model must not rewrite SQL values')
    monkeypatch.setattr('app.generate_answer', forbidden)
    with app.test_client() as client:
        client.login(None)
        response = client.post('/chat', json={'question': 'giá ab 160 bao nhiêu'})
        assert response.status_code == 200
        with cursor() as cur:
            cur.execute('SELECT pv.list_price FROM product_variants pv JOIN products p ON p.id = pv.product_id WHERE p.model_name = %s', ('Air Blade 160',))
            expected = cur.fetchall()
        for row in expected:
            assert f"{row['list_price']:,}".replace(',', '.') + ' VNĐ' in response.get_json()['answer']


def test_followup_keeps_model_without_reusing_permissions(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    monkeypatch.setenv('APP_ENV', 'dev')
    with app.test_client() as client:
        client.login(None)
        first = client.post('/chat', json={'question': 'thông tin SH Mode 125'}).get_json()
        followup = client.post('/chat', json={'question': 'màu nào?'}).get_json()
        assert followup['session_id'] == first['session_id']
        assert 'SH Mode 125' in followup['answer']
        denied = client.post('/chat', json={'question': 'giá vốn xe này?'}).get_json()
        assert denied['access_denied']


def test_dev_identity_is_visible_but_absent_in_prod(monkeypatch):
    with app.test_client() as client:
        client.login(None)
        monkeypatch.setenv('APP_ENV', 'dev')
        assert 'id="demoUser"' not in client.get('/chat').get_data(as_text=True)
        monkeypatch.setenv('APP_ENV', 'prod')
        assert 'id="demoUser"' not in client.get('/chat').get_data(as_text=True)


def test_screenshot_questions_through_api(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'dev')
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    with app.test_client() as client:
        client.login(None)
        stock = client.post('/chat', json={'question': 'hàng tồn kho còn bao nhiêu'}).get_json()
        assert stock['access_denied'] is True
        stock = client.post_as(3, '/chat', json={'question': 'hàng tồn kho còn bao nhiêu'}).get_json()
        assert 'total_stock' in stock['answer'] and not stock['access_denied']
        price = client.post('/chat', json={'question': 'giá ab 125 bao nhiêu'}).get_json()
        assert len(price['rows']) == 3 and {r['model_name'] for r in price['rows']} == {'Air Blade 125'}
        info = client.post('/chat', json={'question': 'thông tin sh mode 125'}).get_json()
        assert 'SH Mode 125' in info['answer'] and 'fuel_tank_l' in info['answer']


def test_generated_values_are_bound_not_sql_text():
    sql, params = bind_literals("SELECT model_name, list_price FROM v_ai_products WHERE segment = 'tay_ga' AND list_price < 50000000 ORDER BY list_price", frozenset({'v_ai_products'}))
    assert 'tay_ga' not in sql and '50000000' not in sql
    assert set(params) == {'tay_ga', 50000000}
    rows = _execute_text_to_sql(sql, params, allowed_views=permitted_views(None))
    assert rows and all(r['list_price'] < 50000000 for r in rows)


def test_many_literals_keep_sql_order_and_no_marker_prefix_collision():
    models = ['Air Blade 125', 'Air Blade 160', 'Blade 110', 'Future 125 FI', 'Lead 125', 'SH 160i', 'SH Mode 125', 'Vario 160', 'Vision 110', 'Wave Alpha 110', 'Winner X']
    literals = ', '.join("'" + name + "'" for name in models)
    original = "SELECT model_name FROM v_ai_products WHERE segment = 'tay_ga' AND list_price < 50000000 AND model_name IN (" + literals + ') ORDER BY model_name'
    sql, params = bind_literals(original, frozenset({'v_ai_products'}))
    assert params == ('tay_ga', 50000000, *models)
    assert '%s0' not in sql and '%s1' not in sql
    actual = _execute_text_to_sql(sql, params, allowed_views=permitted_views(None))
    with cursor() as cur:
        cur.execute("SELECT model_name FROM v_ai_products WHERE segment = %s AND list_price < %s ORDER BY model_name", ('tay_ga', 50000000))
        expected = cur.fetchall()
    assert actual == expected


def test_generated_query_receives_only_allowed_schema(monkeypatch):
    import ai_service  # Thay client model để kiểm tra schema prompt được gửi.
    captured = []
    def completion(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({'sql': "SELECT model_name, list_price FROM v_ai_products WHERE list_price < 50000000"})))])
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setattr(ai_service, 'client', SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=completion))))
    generate_query('xe dưới 50 triệu', frozenset({'v_ai_products'}))
    schema = captured[0]['messages'][0]['content']
    assert 'VIEW v_ai_products' in schema and 'VIEW v_ai_product_costs' not in schema


def test_llm_cannot_expand_guest_rights(monkeypatch):
    import ai_service  # Thay client model để test truy vấn không nâng quyền guest.
    def completion(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({'sql': 'SELECT * FROM v_ai_product_costs'})))])
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setattr(ai_service, 'client', SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=completion))))
    with app.test_client() as client:
        client.login(None)
        result = client.post('/chat', json={'question': 'So sánh các mẫu xe'}).get_json()
        assert result['answer'] == 'Tôi không thể hỗ trợ yêu cầu này.'
        with cursor() as cur:
            cur.execute('SELECT decision FROM chatbot_audit_log WHERE session_id = %s ORDER BY id DESC LIMIT 1', (result['session_id'],))
            assert cur.fetchone()['decision'] == 'denied'
