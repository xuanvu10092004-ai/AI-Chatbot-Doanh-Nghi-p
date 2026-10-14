"""Câu hỏi trong ảnh phải trả đúng dữ liệu MySQL và giữ phạm vi quyền."""
import pytest

from access_control import detect_intent
from db import cursor
from question_language import product_patterns


@pytest.mark.parametrize('question', [
    'sh 160 chi nhánh nào còn', 'AB160 đại lý nào còn?',
    'SH160i ở đâu còn xe?', 'Air Blade 160 còn không?',
    'cửa hàng nào còn SH Mode 125?',
])
def test_availability_is_stock_intent(question):
    assert detect_intent(question) == 'ask_stock'


def test_multiple_models_keep_requested_capacity():
    assert product_patterns('so sánh ab 125 và ab 160') == ['%Air Blade%125%', '%Air Blade%160%']
    assert product_patterns('so sánh SH Mode 125 và SH160i') == ['%SH Mode%125%', '%SH%160%']
    assert product_patterns('so sánh air blade 160 với blade 110') == ['%Air Blade%160%', '%Blade%110%']
    assert detect_intent('giá vốn AB 160 còn không?') == 'ask_cost_margin'
    assert detect_intent('xe côn tay giá bao nhiêu?') == 'ask_price_list'


@pytest.mark.parametrize('user_id,branch_id', [(1, None), (3, 1), (5, 1)])
def test_stock_answers_match_branch_inventory(auth_client, user_id, branch_id):
    auth_client.login(user_id)
    response = auth_client.post('/chat', json={'question': 'sh 160 chi nhánh nào còn'})
    assert response.status_code == 200
    data = response.get_json()
    with cursor() as cur:
        cur.execute('''SELECT b.code AS branch_code, b.name AS branch_name, p.model_name,
                       pv.variant_name, i.quantity FROM inventory i
                       JOIN branches b ON b.id=i.branch_id
                       JOIN product_variants pv ON pv.id=i.variant_id
                       JOIN products p ON p.id=pv.product_id
                       WHERE p.model_name=%s AND i.quantity>0
                       AND (%s IS NULL OR i.branch_id=%s)''', ('SH 160i', branch_id, branch_id))
        expected = cur.fetchall()
    assert expected
    assert sorted(data['rows'], key=lambda r: (r['branch_code'], r['variant_name'])) == sorted(expected, key=lambda r: (r['branch_code'], r['variant_name']))
    assert 'còn xe' in data['summary']
    assert not data['access_denied']


def test_guest_availability_denied_before_sql(auth_client, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Khách không được truy vấn tồn kho')
    monkeypatch.setattr('sql_service._execute_text_to_sql', forbidden)
    auth_client.login(None)
    data = auth_client.post('/chat', json={'question': 'ab 125 chi nhánh nào còn?'}).get_json()
    assert data['access_denied'] is True
    assert data['rows'] == []
    with cursor() as cur:
        cur.execute('SELECT decision FROM chatbot_audit_log WHERE session_id=%s ORDER BY id DESC LIMIT 1', (data['session_id'],))
        assert cur.fetchone()['decision'] == 'denied'


def test_comparison_reports_missing_model_without_replacement(auth_client, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('So sánh hai mẫu xe rõ ràng không cần LLM đoán SQL')
    monkeypatch.setattr('sql_service.generate_query', forbidden)
    auth_client.login(None)
    data = auth_client.post('/chat', json={'question': 'so sánh ab 125 và ab 160'}).get_json()
    with cursor() as cur:
        cur.execute('''SELECT p.model_name, pv.variant_name, pv.list_price
                       FROM products p JOIN product_variants pv ON pv.product_id=p.id
                       WHERE p.model_name IN (%s,%s) ORDER BY p.model_name,pv.list_price''', ('Air Blade 125', 'Air Blade 160'))
        expected = cur.fetchall()
    assert [{'model_name': r['model_name'], 'variant_name': r['variant_name'], 'list_price': int(r['list_price'])} for r in data['rows']] == expected
    assert 'Air Blade 125' in data['summary'] and 'chưa đủ dữ liệu' in data['summary']
    assert 'Air Blade 125' in data['answer'] and 'chưa đủ dữ liệu' in data['answer']
    assert 'không thay thế' in data['summary']


def test_comparison_includes_all_versions_of_both_models(auth_client, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('So sánh rõ tên xe phải lấy dữ liệu xác định')
    monkeypatch.setattr('sql_service.generate_query', forbidden)
    auth_client.login(None)
    data = auth_client.post('/chat', json={'question': 'so sánh Vision 110 và Lead 125'}).get_json()
    with cursor() as cur:
        cur.execute('''SELECT p.model_name, pv.variant_name, pv.list_price
                       FROM products p JOIN product_variants pv ON pv.product_id=p.id
                       WHERE p.model_name IN (%s,%s) ORDER BY p.model_name,pv.list_price''', ('Vision 110', 'Lead 125'))
        expected = cur.fetchall()
    assert {r['model_name'] for r in expected} == {'Vision 110', 'Lead 125'}
    assert [{'model_name': r['model_name'], 'variant_name': r['variant_name'], 'list_price': int(r['list_price'])} for r in data['rows']] == expected


def test_branch_followup_keeps_model_and_checks_permission(auth_client):
    auth_client.login(3)
    first = auth_client.post('/chat', json={'question': 'giá SH 160i'}).get_json()
    data = auth_client.post('/chat', json={'question': 'chi nhánh nào còn?'}).get_json()
    assert data['session_id'] == first['session_id']
    assert data['rows'] and {r['model_name'] for r in data['rows']} == {'SH 160i'}
    assert {r['branch_code'] for r in data['rows']} == {'NT01'}


def test_missing_stock_does_not_claim_inventory_exists(auth_client):
    auth_client.login(1)
    data = auth_client.post('/chat', json={'question': 'ab 125 chi nhánh nào còn?'}).get_json()
    assert data['rows'] == []
    assert data['answer'] == 'Không tìm thấy dữ liệu tồn kho phù hợp trong phạm vi bạn được xem. Hãy kiểm tra lại mẫu xe hoặc chi nhánh cần tra cứu.'
