"""Kiểm thử độ tin cậy của truy xuất tài liệu và căn cứ cho câu trả lời RAG."""

import pytest

from rag_service import rank_documents, search_documents
from db import cursor
from access_control import create_session
from test_chat_tools_imports import no_live_model


def test_rank_prefers_relevant_title_over_document_id():
    unrelated = {'id': 1, 'title': 'Giới thiệu', 'content': 'Một ghi chú có từ bảo hành.'}
    relevant = {'id': 99, 'title': 'Chính sách bảo hành', 'content': 'Điều kiện bảo hành.'}
    assert rank_documents('Chính sách bảo hành', [[unrelated, relevant], [relevant]])[0]['id'] == 99


def test_guest_hybrid_search_cannot_see_unpublished_or_sales(auth_client):
    auth_client.login(None)
    evidence = search_documents('hướng dẫn bảo hành', None, create_session(None))
    with cursor() as cur:
        cur.execute("SELECT d.id FROM kb_documents d JOIN kb_categories c ON c.id=d.category_id WHERE c.code='public' AND d.branch_id IS NULL")
        allowed = {r['id'] for r in cur.fetchall()}
    import re
    assert {int(i) for i in re.findall(r'Nguồn id=(\d+)', evidence)} <= allowed


def test_production_sql_answer_never_goes_to_language_model(auth_client, monkeypatch):
    auth_client.login(1)
    monkeypatch.setenv('APP_ENV', 'prod')
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    def forbidden(*a, **kw):
        pytest.fail('Số liệu SQL không gửi cho model diễn đạt lại')
    monkeypatch.setattr('app.generate_answer', forbidden)
    reply = auth_client.post('/chat', json={'question': 'Giá SH 160i'})
    assert reply.status_code == 200
    with cursor() as cur:
        cur.execute('SELECT list_price FROM product_variants pv JOIN products p ON p.id=pv.product_id WHERE p.model_name=%s ORDER BY list_price', ('SH 160i',))
        assert [r['list_price'] for r in reply.json['rows']] == [int(r['list_price']) for r in cur.fetchall()]
