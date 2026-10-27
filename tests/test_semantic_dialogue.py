"""Semantic resolution + persisted state, using the private MySQL test server."""
import json

import pytest

from db import cursor
from intent_resolver import resolve
from chat_tools import TOOLS
from test_chat_tools_imports import chat, confirm, tool_cleanup, no_live_model


@pytest.mark.parametrize('question,tool', [
    ('Bổ sung vào kho 3 chiếc SP014', 'stock_receive'),
    ('Nhận thêm hàng SP014', 'stock_receive'),
    ('Tải chứng từ đơn #1', 'invoice_export'),
    ('Điều chỉnh giá xe SP014: Giá: 57.500.000', 'catalog_save'),
    ('Giúp tôi xem các đơn hàng', 'orders_list'),
    ('Đăng ký tư vấn ngày mai 9h30', 'appointment_create'),
])
def test_paraphrases(question, tool):
    assert resolve(question, {}, TOOLS).tool == tool


def test_literal_model_arguments_and_authorized_catalog(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'fake-test-key')
    catalog = {'invoice_export': TOOLS['invoice_export']}
    def interpret(question, state, supplied):
        assert supplied == catalog
        return {'tool': 'invoice_export', 'arguments': {'id': 99999, 'sql': 'DROP TABLE users'}}
    monkeypatch.setattr('intent_resolver.semantic_interpret', interpret)
    result = resolve('Giúp tôi lấy chứng từ nhé', {}, catalog)
    assert result.arguments == {}
    monkeypatch.setattr('intent_resolver.semantic_interpret', lambda *a: {'tool': 'user_save', 'arguments': {}})
    assert resolve('Giúp tôi làm việc đó', {}, catalog).tool is None


def test_pending_fields_survive_turns_without_writes(auth_client, tool_cleanup):
    auth_client.login(2)
    first = chat(auth_client, 'Nhập hàng: Mã SP: SP014; Số lượng: 3')
    assert first['type'] == 'clarification'
    second = chat(auth_client, 'Nhà cung cấp: Kho mô phỏng')
    draft = second['action_draft']
    assert draft['arguments']['items'] == [{'variant_id': 14, 'quantity': 3}]
    with cursor() as cur:
        cur.execute('SELECT payload FROM chat_dialogue_state WHERE session_id=%s', (first['session_id'],))
        assert json.loads(cur.fetchone()['payload'])['active_tool'] == 'stock_receive'
        cur.execute('SELECT COUNT(*) AS n FROM stock_receipts WHERE reference_code=%s', (draft['arguments']['reference_code'],))
        assert cur.fetchone()['n'] == 0
    out = chat(auth_client, 'Đồng ý')
    assert out['result']['received_quantity'] == 3
    assert confirm(auth_client, second)['result'] == out['result']


def test_new_question_does_not_become_pending_field(auth_client, tool_cleanup):
    auth_client.login(2)
    chat(auth_client, 'Nhập hàng: Mã SP: SP014; Số lượng: 2')
    result = chat(auth_client, 'Giá SH 160i')
    assert result['type'] == 'SQL' and result['rows']
    assert 'action_draft' not in result


def test_missing_update_id_asks_instead_of_claiming_not_found(auth_client, tool_cleanup):
    auth_client.login(2)
    reply = chat(auth_client, 'Hủy lịch sửa xe')
    assert reply['type'] == 'clarification'
    assert not reply.get('access_denied')


def test_resolver_outage_is_explicit_and_never_writes(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'fake-test-key')
    def unavailable(*a):
        raise RuntimeError('secret provider error')
    monkeypatch.setattr('intent_resolver.semantic_interpret', unavailable)
    reply = resolve('Giúp tôi làm việc đó', {}, TOOLS)
    assert reply.unavailable and 'chưa sẵn sàng' in reply.clarification
    assert 'secret' not in reply.clarification


def test_product_name_requires_variant_selection_and_rechecks_scope(auth_client, tool_cleanup):
    auth_client.login(2)
    reply = chat(auth_client, 'Nhập hàng: Nhà cung cấp: Kho mô phỏng; Số lượng: 2; xe SH 160i')
    options = reply['clarification']['options']
    with cursor() as cur:
        cur.execute('SELECT pv.id FROM product_variants pv JOIN products p ON p.id=pv.product_id WHERE p.model_name=%s', ('SH 160i',))
        assert {r['id'] for r in options} == {r['id'] for r in cur.fetchall()}
    assert 'action_draft' not in reply
    rejected = chat(auth_client, 'Chọn 999999')
    assert 'action_draft' not in rejected
    chosen = chat(auth_client, 'Chọn ' + str(options[0]['id']))
    assert chosen['action_draft']['arguments']['items'] == [{'variant_id': options[0]['id'], 'quantity': 2}]


def test_all_dashboard_widget_names_are_resolved():
    from intent_resolver import local_arguments
    from dashboard_service import WIDGETS
    questions = ['đơn hàng', 'tồn kho', 'khách hàng', 'doanh thu theo tháng',
                 'doanh thu theo chi nhánh', 'tồn kho theo chi nhánh',
                 'khách theo trạng thái', 'khách theo nguồn', 'bán chạy', 'lợi nhuận gộp']
    assert {local_arguments('Xem tổng quan ' + q, 'dashboard_read')['widget'] for q in questions} == set(WIDGETS)


def test_customer_name_lookup_cannot_cross_branch(auth_client, tool_cleanup):
    auth_client.login(2)
    with cursor() as cur:
        cur.execute("SELECT full_name FROM users WHERE user_type='customer' AND home_branch_id=2 LIMIT 1")
        name = cur.fetchone()['full_name']
    reply = chat(auth_client, 'Đặt lịch sửa xe: Khách hàng: ' + name)
    assert reply['type'] == 'clarification'
    assert reply['clarification']['options'] == []
    assert 'action_draft' not in reply


@pytest.mark.parametrize('question', ['Lập báo giá cho khách A', 'Tạo cơ hội bán hàng', 'Duyệt đơn hàng #1', 'Thanh toán đơn hàng #1'])
def test_unimplemented_workflows_are_reported(question):
    result = resolve(question, {}, TOOLS)
    assert result.tool is None and 'chưa có backend' in result.clarification
