import os
import pytest
from mysql.connector import Error

from app import app
from db import cursor, get_connection
from access_control import detect_intent, permitted_views
from query_plans import plan_query
from sql_service import _execute_text_to_sql
from rag_service import _search_query
from schema_context import build_schema_context


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'dev')
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    app.config.update(TESTING=True)
    return app.test_client().login(None)


@pytest.mark.parametrize('body', [None, [], {'question': None}, {'question': 3}, {}, {'question': '  '}])
def test_invalid_request(client, body):
    assert client.post('/chat', json=body).status_code == 400


def test_session_history_and_audit(client):
    first = client.post('/chat', json={'question': 'SH 160i giá bao nhiêu?'}).get_json()
    second = client.post('/chat', json={'question': 'Vision 110 có mấy phiên bản?'}).get_json()
    assert first['session_id'] == second['session_id']
    assert first['engine'] == 'database'
    assert '92500000' in first['answer']
    with cursor() as cur:
        cur.execute('SELECT sender FROM chat_messages WHERE session_id = %s ORDER BY id', (first['session_id'],))
        assert [r['sender'] for r in cur.fetchall()] == ['user', 'bot', 'user', 'bot']
        cur.execute('SELECT COUNT(*) AS n FROM chatbot_audit_log WHERE session_id = %s', (first['session_id'],))
        assert cur.fetchone()['n'] == 2


@pytest.mark.parametrize('user', [None, '3', '5'])
def test_cost_denied_before_retrieval(client, monkeypatch, user):
    def forbidden(*args, **kwargs):
        pytest.fail('SQL retrieval must not run for a denied question')
    monkeypatch.setattr('sql_service._execute_text_to_sql', forbidden)
    response = client.post_as(int(user) if user else None, '/chat', json={'question': 'Giá vốn SH 160i?'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['answer'] == 'Tôi không thể hỗ trợ yêu cầu này.'
    with cursor() as cur:
        cur.execute('SELECT decision FROM chatbot_audit_log WHERE session_id = %s', (data['session_id'],))
        assert [r['decision'] for r in cur.fetchall()] == ['denied']


def test_sales_scope_and_pool_reset(client):
    data = client.post_as(3, '/chat', json={'question': 'Tồn kho tại NT02'}).get_json()
    assert data['answer'] == 'Không tìm thấy dữ liệu phù hợp.'
    rows = _execute_text_to_sql('SELECT branch_code FROM v_ai_inventory', allowed_views=permitted_views(3), scope_branch_ids=[1])
    assert len(rows) == 31 and {r['branch_code'] for r in rows} == {'NT01'}
    rows = _execute_text_to_sql('SELECT branch_code FROM v_ai_inventory', allowed_views=permitted_views(1))
    assert len(rows) == 93 and {r['branch_code'] for r in rows} == {'NT01', 'NT02', 'CR01'}
    with cursor('text_to_sql') as cur:
        cur.execute('SELECT @ai_branch AS scope, @@max_statement_time AS timeout')
        row = cur.fetchone()
        assert row['scope'] is None and float(row['timeout']) == 5


@pytest.mark.parametrize('sql', ['SELECT * FROM users', 'SELECT * FROM product_variants', 'DELETE FROM v_ai_orders'])
def test_readonly_database_privileges(sql):
    with cursor('text_to_sql') as cur:
        with pytest.raises(Error) as exc:
            cur.execute(sql)
        assert exc.value.errno == 1142


@pytest.mark.parametrize('user,expected', [
    (None, {'v_ai_products'}),
    (5, {'v_ai_products', 'v_ai_inventory'}),
    (3, {'v_ai_products', 'v_ai_inventory', 'v_ai_orders', 'v_ai_customers'}),
    (6, {'v_ai_products', 'v_ai_orders', 'v_ai_product_costs'}),
])
def test_permission_whitelist(user, expected):
    assert permitted_views(user) == expected


def test_guest_schema_does_not_expose_costs():
    conn = get_connection()
    try:
        prompt = build_schema_context(conn, os.environ['DB_NAME'], permitted_views(None))
        assert 'VIEW v_ai_products' in prompt
        assert 'VIEW v_ai_product_costs' not in prompt
        assert 'Giá niêm yết (VNĐ)' in prompt
        assert 'password_hash' not in prompt
    finally:
        conn.close()


def test_guest_documents_never_include_sales_or_branch():
    query, params = _search_query('Honda', None, use_like=True)
    with cursor() as cur:
        cur.execute(query, params)
        ids = {r['id'] for r in cur.fetchall()}
    assert ids and ids <= {1, 2, 3, 4}


def test_rag_sources_and_no_evidence(client):
    data = client.post('/chat', json={'question': 'Thủ tục trả góp?'}).get_json()
    assert '[Nguồn id=' in data['answer'] and 'tiêu đề=' in data['answer']
    data = client.post('/chat', json={'question': 'Tài liệu zzznonexistent12345?'}).get_json()
    assert data['answer'] == 'Không tìm thấy bằng chứng trong tài liệu được phép truy cập.'


def test_prod_ignores_demo_header(client, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'prod')
    data = client.post('/chat', json={'question': 'Tồn kho?'}, headers={'X-Demo-User-Id': '1'}).get_json()
    assert data['answer'] == 'Tôi không thể hỗ trợ yêu cầu này.'


def test_database_failure_is_controlled(client, monkeypatch):
    def unavailable(*args):
        raise Error('private_database_details')
    monkeypatch.setattr('app.create_session', unavailable)
    response = client.post('/chat', json={'question': 'Giá xe?'})
    assert response.status_code == 503
    assert 'private_database_details' not in response.get_data(as_text=True)


def test_prompt_is_sent_to_model(monkeypatch):
    import ai_service
    from types import SimpleNamespace
    calls = []
    def completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='answer'))])
    monkeypatch.setattr(ai_service, 'API_KEY', 'test-key')
    monkeypatch.setattr(ai_service, 'client', SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=completion))))
    assert ai_service.generate_answer('Giá?', 'evidence', [{'sender': 'user', 'content': 'previous'}]) == 'answer'
    assert calls[0]['messages'][0] == {'role': 'system', 'content': ai_service.SYSTEM_PROMPT}
    assert 'evidence' in calls[0]['messages'][1]['content']


STANDARD_CASES = [
    ('SH 160i giá bao nhiêu?', 'SELECT pv.list_price FROM product_variants pv JOIN products p ON p.id = pv.product_id WHERE p.model_name = %s ORDER BY pv.list_price', ('SH 160i',), 'list_price'),
    ('Có bao nhiêu khách hàng đã mua xe?', 'SELECT COUNT(*) AS n FROM customer_profiles WHERE status = %s', ('Đã mua',), 'purchased_customers'),
    ('Tổng số đơn hàng?', 'SELECT COUNT(*) AS n FROM orders', (), 'orders'),
    ('Tổng tồn kho toàn hệ thống?', 'SELECT SUM(quantity) AS n FROM inventory', (), 'total_stock'),
    ('Mỗi phân khúc có bao nhiêu phiên bản?', 'SELECT p.segment, COUNT(*) AS variants FROM products p JOIN product_variants pv ON pv.product_id = p.id GROUP BY p.segment ORDER BY p.segment', (), None),
    ('Mẫu xe nào có giá niêm yết cao nhất?', 'SELECT p.model_name, pv.variant_name, pv.list_price FROM products p JOIN product_variants pv ON pv.product_id = p.id ORDER BY pv.list_price DESC LIMIT 1', (), None),
    ('Tổng doanh thu thuần của các đơn?', 'SELECT SUM(oi.quantity * oi.unit_price - o.discount_amount) AS n FROM orders o JOIN order_items oi ON oi.order_id = o.id', (), 'net_revenue'),
    ('Bao nhiêu khách hàng chọn trả góp?', 'SELECT COUNT(*) AS n FROM customer_profiles WHERE payment_preference = %s', ('Trả góp',), 'installment_customers'),
    ('Có bao nhiêu dòng tồn kho đang hết hàng?', 'SELECT COUNT(*) AS n FROM inventory WHERE quantity = 0', (), 'empty_inventory_rows'),
    ('Vision 110 có bao nhiêu phiên bản?', 'SELECT COUNT(*) AS n FROM products p JOIN product_variants pv ON pv.product_id = p.id WHERE p.model_name = %s', ('Vision 110',), 'variants'),
]


@pytest.mark.parametrize('question,oracle,params,key', STANDARD_CASES)
def test_standard_answers_against_base_sql(question, oracle, params, key, client):
    sql, bind = plan_query(question, detect_intent(question))
    actual = _execute_text_to_sql(sql, bind, allowed_views=permitted_views(1))
    with cursor() as cur:
        cur.execute(oracle, params)
        expected = cur.fetchall()
    if key:
        assert [r[key] for r in actual] == [next(iter(r.values())) for r in expected]
    else:
        assert actual == expected
    response = client.post_as(1, '/chat', json={'question': question})
    assert response.status_code == 200
    answer = response.get_json()['answer']
    for row in expected:
        for value in row.values():
            assert str(value) in answer


def test_unknown_model_does_not_invent_price(client):
    response = client.post('/chat', json={'question': 'Honda Rebel 500 giá bao nhiêu?'})
    assert response.get_json()['answer'] == 'Không tìm thấy dữ liệu phù hợp.'
