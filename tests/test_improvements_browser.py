"""Kiểm tra giá VNĐ, biểu đồ, menu gọn và công cụ mới ở desktop/mobile."""
import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.
from pathlib import Path  # Tạo và kiểm tra đường dẫn file trong dự án.
import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.

playwright=pytest.importorskip('playwright.sync_api')
from db import cursor  # Mở cursor hoặc connection MySQL.
from test_customer_input_browser import customer_server  # Dùng server fixture và trạng thái batch khách.
from test_customer_input import clean_customer_input,BATCHES  # Dùng fixture và helper tạo/dọn batch nhập khách.
from test_document_uploads import document_storage  # Dùng fixture lưu trữ và helper upload tài liệu.


@pytest.mark.parametrize('width,height',[(1440,1000),(390,844)])
def test_requested_pages_and_money(customer_server,width,height):
    with playwright.sync_playwright() as driver:
        browser=driver.chromium.launch(headless=True,executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        page=browser.new_page(viewport={'width':width,'height':height})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            page.goto(customer_server+'/login')
            with cursor() as cur:cur.execute('SELECT email FROM users WHERE id=1');email=cur.fetchone()['email']
            page.get_by_label('Email',exact=True).fill(email);page.get_by_label('Mật khẩu',exact=True).fill(os.environ['DEMO_ACCOUNT_PASSWORD'])
            page.get_by_role('button',name='Đăng nhập',exact=True).click();page.wait_for_url('**/dashboard')
            page.wait_for_function("() => document.querySelectorAll('.widget canvas').length >= 5")
            page.wait_for_function("() => [...document.querySelectorAll('.widget-content')].every(n=>!n.textContent.includes('Đang tải'))")
            assert 'Không tải được' not in page.locator('.widget-grid').inner_text()
            assert page.locator('.brand-logo').evaluate('n=>n.complete&&n.naturalWidth>0&&n.src.endsWith("/static/images/logo.jpg")')
            assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()")=='#cc0000'
            assert page.locator('.sidebar a',has_text='Quản trị truy cập').count()==1
            for path in ['/dashboard','/customers','/inventory','/bookings','/catalog','/admin/users','/admin/roles']:
                page.goto(customer_server+path)
                if path=='/customers':
                    page.wait_for_function("() => document.querySelector('#recordSummary').textContent.includes('Tổng số khách hàng')")
                    assert page.locator('#recordSummary meter').count()>0
                elif path in ['/bookings','/catalog']:
                    page.wait_for_function("() => !document.querySelector('#operationTable').textContent.includes('Đang tải')")
                    assert 'Không tải được' not in page.locator('#operationTable').inner_text()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),path
            page.goto(customer_server+'/customer-input?quick=1')
            page.locator('#customerField_purchased_sku').wait_for()
            assert page.locator('#customerFields').evaluate("n=>[...n.querySelectorAll('input,select')].findIndex(n=>n.id==='customerField_purchased_sku')<[...n.querySelectorAll('input,select')].findIndex(n=>n.id==='customerField_purchase_amount')")
            page.locator('#customerField_purchased_sku').select_option('SP014')
            with cursor() as cur:cur.execute('SELECT list_price FROM product_variants WHERE id=14');price=cur.fetchone()['list_price']
            assert page.locator('#customerField_purchase_amount').input_value()==f'{price:,}'.replace(',','.')
            assert page.locator('label[for="customerField_purchased_sku"]').inner_text()=='Mã SP'
            page.goto(customer_server+'/chat')
            page.locator('#questionInput').fill('Thêm khách hàng')
            with page.expect_response(lambda r:r.url.endswith('/chat') and r.request.method=='POST') as pending:
                page.get_by_role('button',name='Gửi',exact=True).click()
            BATCHES.add(pending.value.json()['customer_draft']['id'])
            page.wait_for_function("() => !document.querySelector('#sendButton').disabled")
            page.locator('#questionInput').fill('Người Dùng Kiểm Thử, browsercomma@customer-input.test, 0935253359')
            with page.expect_response(lambda r:r.url.endswith('/chat') and r.request.method=='POST') as pending:
                page.get_by_role('button',name='Gửi',exact=True).click()
            draft=pending.value.json()['customer_draft'];row=draft['rows'][0]['data']
            assert row['phone']=='0935253359' and row['email']=='browsercomma@customer-input.test'
            assert not errors,errors
            folder=Path('.pytest_cache/improvements');folder.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(folder/f'chat-{width}.png'),full_page=True)
            page.goto(customer_server+'/dashboard');page.wait_for_timeout(500)
            page.screenshot(path=str(folder/f'dashboard-{width}.png'),full_page=True)
        finally:browser.close()
