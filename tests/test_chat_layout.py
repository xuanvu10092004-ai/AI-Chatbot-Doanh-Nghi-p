"""Kiểm tra khung chat thật bằng Edge/Chromium; cần Playwright (tùy chọn)."""
import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.
from pathlib import Path  # Tạo và kiểm tra đường dẫn file trong dự án.
from threading import Thread  # Tạo hoặc đồng bộ các luồng chạy đồng thời.

import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.
from werkzeug.serving import make_server  # Khởi chạy server Flask để trình duyệt kiểm thử truy cập.

playwright = pytest.importorskip('playwright.sync_api', reason='Cần Playwright để kiểm tra bố cục bằng trình duyệt thật')

from app import app  # Dùng ứng dụng Flask đang được kiểm thử.
from db import cursor  # Mở cursor hoặc connection MySQL.


@pytest.fixture
def chat_server():
    secure = app.config['SESSION_COOKIE_SECURE']
    app.config['SESSION_COOKIE_SECURE'] = False
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        thread.join(timeout=5)
        app.config['SESSION_COOKIE_SECURE'] = secure


@pytest.mark.parametrize('width,height', [(1440, 900), (1280, 600), (390, 844)])
def test_messages_keep_all_text_and_tables_scroll(chat_server, width, height):
    with playwright.sync_playwright() as driver:
        options = {'headless': True}
        edge = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        if edge.exists():
            options['executable_path'] = str(edge)
        browser = driver.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(chat_server + '/login')
            with cursor() as cur:
                cur.execute('SELECT email FROM users WHERE id=%s', (1,))
                email = cur.fetchone()['email']
            page.get_by_label('Email', exact=True).fill(email)
            page.get_by_label('Mật khẩu', exact=True).fill(os.environ['DEMO_ACCOUNT_PASSWORD'])
            page.get_by_role('button', name='Đăng nhập', exact=True).click()
            page.wait_for_url('**/dashboard')
            page.goto(chat_server + '/chat')
            questions = ['ab 150 chi nhánh nào còn?', 'sh 160 chi nhánh nào còn',
                         'so sánh ab 150 và ab 160', 'thông tin SH Mode 125',
                         'thông tin SH 160i', 'so sánh Vision 110 và Lead 125',
                         'ab 125 chi nhánh nào còn?', 'so sánh ab 125 và ab 160']
            for question in questions:
                page.get_by_label('Câu hỏi', exact=True).fill(question)
                with page.expect_response(lambda response: response.url.endswith('/chat') and response.request.method == 'POST') as pending:
                    page.get_by_role('button', name='Gửi', exact=True).click()
                assert pending.value.status == 200
                page.wait_for_function("!document.querySelector('#sendButton').disabled")
            # Nhiều lượt vượt chiều cao khung phải cuộn, không ép thấp từng tin.
            measurements = page.locator('.message').evaluate_all('''nodes => nodes.map(node => ({
                height: node.clientHeight, content: node.scrollHeight,
                shrink: getComputedStyle(node).flexShrink, text: node.textContent
            }))''')
            assert len(measurements) == 1 + 2 * len(questions)
            assert all(row['height'] >= row['content'] - 1 for row in measurements), measurements
            assert all(row['shrink'] == '0' for row in measurements)
            assert any('Air Blade 150' in row['text'] and 'chưa đủ dữ liệu' in row['text'] for row in measurements)
            assert page.locator('#chatMessages').evaluate('(node) => node.scrollHeight > node.clientHeight')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Trang bị tràn ngang'
            assert page.locator('.table-scroll').count() == 7
            assert page.locator('.table-scroll thead tr').last.locator('th').first.inner_text() == 'Mẫu xe'
            assert page.locator('.table-hint').count() == 7
            assert page.locator('.table-scroll').evaluate_all('nodes => nodes.every(n => n.scrollHeight <= n.clientHeight + 1)')
            if width == 390:
                assert page.locator('.table-scroll').evaluate_all('nodes => nodes.every(n => n.scrollWidth > n.clientWidth)')
                last_table = page.locator('.table-scroll').last
                last_table.evaluate('(node) => { node.scrollLeft = node.scrollWidth; }')
                assert last_table.evaluate('(node) => node.scrollLeft > 0')
                last_table.evaluate('(node) => { node.scrollLeft = 0; }')
            assert not errors
            # Chụp đầu câu trả lời mới nhất, kèm ô nhập, để kiểm tra thủ công.
            page.locator('#questionInput').scroll_into_view_if_needed()
            assert page.locator('.topbar').evaluate('node => node.scrollHeight <= node.clientHeight + 1')
            page.evaluate('window.scrollTo(0, 0)')
            artifacts = Path('.pytest_cache/chat-layout')
            artifacts.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(artifacts / f'chat-{width}x{height}.png'), full_page=True)
        finally:
            browser.close()
