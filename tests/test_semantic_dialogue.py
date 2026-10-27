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
