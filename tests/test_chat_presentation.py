"""Kiểm tra luồng chat thật với MySQL và định dạng DOM không thực thi HTML."""
import shutil  # Tìm tiện ích hoặc sao chép file.
import subprocess  # Chạy parser hoặc tiện ích trong tiến trình riêng.
from pathlib import Path  # Tạo và kiểm tra đường dẫn file trong dự án.

import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.

from db import cursor  # Mở cursor hoặc connection MySQL.
from rag_service import _search_query  # Tạo truy vấn RAG và lọc nguồn theo quyền.
from text_formatting import normalize_dashes  # Kiểm tra quy ước dấu gạch trong câu trả lời.

ROOT = Path(__file__).resolve().parents[1]


def test_safe_dom_formatter():
    """Node chạy parser thật với DOM kiểm soát để bắt lỗi XSS và thẻ định dạng."""
    node = shutil.which('node')
    if not node:
        pytest.skip('Kiểm tra JavaScript cần Node.js')
    result = subprocess.run([node, str(ROOT / 'tests/chat_formatting_check.js')],
                            capture_output=True, encoding='utf-8', timeout=10)
    assert result.returncode == 0, result.stderr


def test_logo_and_formatter_served_locally(auth_client):
    """Logo người dùng cung cấp được phục vụ nguyên bản từ tài nguyên cục bộ."""
    login = auth_client.get('/login').get_data(as_text=True)
    assert 'src="/static/images/logo.jpg"' in login
    response = auth_client.get('/static/images/logo.jpg')
    assert response.status_code == 200
    assert response.data == (ROOT / 'docs/images/logo.jpg').read_bytes()
    assert response.mimetype == 'image/jpeg'
    auth_client.login(1)
    page = auth_client.get('/chat').get_data(as_text=True)
    assert 'src="/static/images/logo.jpg"' in page
    assert page.index('/static/chat-formatting.js') < page.index('/static/chat.js')
    assert 'Dữ liệu mô phỏng' in page
    assert '\u2014' not in page


def test_generated_answer_and_history_normalize_dashes(auth_client, monkeypatch):
    """Mô phỏng riêng LLM, vẫn chạy quyền, RAG và lưu lịch sử bằng MySQL thật."""
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setattr('app.generate_answer', lambda *args: '**Khuyến mãi**\u2014*Dữ liệu mô phỏng*\u2013NT01')
    auth_client.login(1)
    response = auth_client.post('/chat', json={'question': 'Chương trình khuyến mãi'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['answer'] == '**Khuyến mãi**-*Dữ liệu mô phỏng*-NT01'
    assert {source['id'] for source in data['sources']} == {5}
    with cursor() as cur:
        cur.execute("SELECT content FROM chat_messages WHERE session_id=%s AND sender='bot' ORDER BY id DESC LIMIT 1", (data['session_id'],))
        assert cur.fetchone()['content'] == data['answer']


@pytest.mark.parametrize('user_id,expected', [(1, {5}), (3, {5}), (None, set())])
def test_promotions_do_not_match_technical_documents(user_id, expected):
    """Cùng câu trong ảnh: chỉ nguồn khuyến mãi hợp lệ, guest không thấy sales."""
    query, params = _search_query('Chương trình khuyến mãi', user_id, use_like=True)
    with cursor() as cur:
        cur.execute(query, params)
        assert {row['id'] for row in cur.fetchall()} == expected


def test_dash_normalization():
    assert normalize_dashes('A\u2014B\u2013C-D') == 'A-B-C-D'
