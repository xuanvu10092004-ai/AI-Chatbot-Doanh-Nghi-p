"""Kiểm thử luồng nhập dữ liệu khách hàng trên giao diện trình duyệt."""

import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.
from threading import Thread  # Tạo hoặc đồng bộ các luồng chạy đồng thời.
from pathlib import Path  # Tạo và kiểm tra đường dẫn file trong dự án.

import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.
from werkzeug.serving import make_server  # Khởi chạy server Flask để trình duyệt kiểm thử truy cập.

playwright=pytest.importorskip('playwright.sync_api',reason='Cần Playwright kiểm thử nhập khách hàng')
from app import app  # Dùng ứng dụng Flask đang được kiểm thử.
from db import cursor  # Mở cursor hoặc connection MySQL.
from test_customer_input import clean_customer_input,BATCHES  # Dùng fixture và helper tạo/dọn batch nhập khách.
from customer_input import WORKBOOK_HEADERS,FIELDS  # Dùng quy tắc kiểm tra và lưu batch nhập khách.
from test_document_uploads import document_storage  # Dùng fixture lưu trữ và helper upload tài liệu.


@pytest.fixture
def customer_server(clean_customer_input):
    secure=app.config['SESSION_COOKIE_SECURE'];app.config['SESSION_COOKIE_SECURE']=False
    server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown();thread.join(timeout=5);app.config['SESSION_COOKIE_SECURE']=secure


@pytest.mark.parametrize('width,height',[(1440,900),(390,844)])
def test_customer_form_and_chat_creation(customer_server,width,height,tmp_path):
    with playwright.sync_playwright() as driver:
        browser=driver.chromium.launch(headless=True,executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        try:
            page=browser.new_page(viewport={'width':width,'height':height});errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(customer_server+'/login?next=/customer-input')
            with cursor() as cur:cur.execute('SELECT email FROM users WHERE id=%s',(3,));email=cur.fetchone()['email']
            page.get_by_label('Email',exact=True).fill(email);page.get_by_label('Mật khẩu',exact=True).fill(os.environ['DEMO_ACCOUNT_PASSWORD']);page.get_by_role('button',name='Đăng nhập',exact=True).click();page.wait_for_url('**/customer-input')
            page.locator('#customerField_full_name').fill('Khách giao diện');page.locator('#customerField_email').fill(f'browser{width}@customer-input.test');page.locator('#customerField_phone').fill('0901234567')
            with page.expect_response(lambda r:r.url.endswith('/api/customer-input') and r.request.method=='POST') as preview:
                page.get_by_role('button',name='Kiểm tra và xem trước thay đổi').click()
            assert preview.value.status==201;batch=preview.value.json();BATCHES.add(batch['id']);assert batch['valid']
            page.locator('#confirmCustomerBatch').check()
            with page.expect_response(lambda r:r.url.endswith('/commit')) as committed:page.get_by_role('button',name='Xác nhận đồng bộ vào CSDL').click()
            assert committed.value.status==200 and committed.value.json()['created']==1
            page.goto(customer_server+'/chat')
            question=f'Thêm khách hàng: Họ và tên: Khách qua chat; Email: chatbrowser{width}@customer-input.test; Số điện thoại: 0909876543; Mẫu xe quan tâm: AB125'
            page.locator('#questionInput').fill(question)
            with page.expect_response(lambda r:r.url.endswith('/chat') and r.request.method=='POST') as reply:page.get_by_role('button',name='Gửi',exact=True).click()
            result=reply.value.json();BATCHES.add(result['customer_draft']['id']);assert result['customer_draft']['valid']
            page.get_by_role('button',name='Xác nhận lưu khách hàng',exact=True).wait_for()
            assert 'Họ và tên:' in page.locator('.bot-message').last.inner_text()
            with page.expect_response(lambda r:r.url.endswith('/chat') and r.request.method=='POST') as saved:page.get_by_role('button',name='Xác nhận lưu khách hàng',exact=True).click()
            assert saved.value.json()['result']['created']==1
            page.goto(customer_server+'/documents');page.locator('#documentCategory option').filter(has_text='Thông tin / Danh sách khách hàng').wait_for(state='attached')
            page.locator('#documentCategory').select_option(label='Thông tin / Danh sách khách hàng')
            assert page.locator('#customerTemplateLink').is_visible()
            from openpyxl import Workbook  # Đọc hoặc tạo workbook Excel.
            book=Workbook();sheet=book.active;sheet.title='Khach_hang';sheet.append(WORKBOOK_HEADERS)
            values={'full_name':'Khách từ file','phone':'0907654321','email':f'filebrowser{width}@customer-input.test','branch_code':'NT01','registered_at':'2026-10-10','status':'Đã mua','purchased_sku':'SP014','purchase_amount':56500000}
            reverse={label:key for key,label in FIELDS.items()};reverse['Mã SP đã mua']='purchased_sku';sheet.append([values.get(reverse.get(label)) for label in WORKBOOK_HEADERS])
            file=tmp_path/'customers.xlsx';book.save(file)
            page.locator('#documentTitle').fill('Kiểm thử parser đồng bộ khách giao diện');page.locator('#documentFile').set_input_files(file)
            with page.expect_response(lambda r:r.url.endswith('/api/customer-input') and r.request.method=='POST') as imported:
                with page.expect_response(lambda r:r.url.endswith('/api/documents') and r.request.method=='POST') as uploaded:page.get_by_role('button',name='Tải lên và trích xuất').click()
            assert uploaded.value.status==201
            staged=imported.value.json();BATCHES.add(staged['id']);assert staged['valid']
            page.locator('#confirmCustomerImport').check()
            with page.expect_response(lambda r:r.url.endswith('/commit')) as synced:page.get_by_role('button',name='Xác nhận cập nhật danh sách khách hàng',exact=True).click()
            assert synced.value.json()['created']==1 and synced.value.json()['orders_created']==1
            page.goto(customer_server+'/customer-input?quick=1')
            page.locator('#customerField_full_name').fill('Khách mua nhanh')
            page.locator('#customerField_email').fill(f'quickbrowser{width}@customer-input.test')
            page.locator('#customerField_phone').fill('0901234567')
            assert page.locator('#customerField_status').input_value()=='Đã mua'
            assert not page.locator('#customerField_occupation').is_visible()
            page.locator('#customerField_purchased_sku').select_option('SP014')
            assert page.locator('#customerField_purchase_amount').input_value()=='56.500.000'
            with page.expect_response(lambda r:r.url.endswith('/api/customer-input') and r.request.method=='POST') as fast:
                page.get_by_role('button',name='Kiểm tra và xem trước thay đổi').click()
            quick=fast.value.json();BATCHES.add(quick['id']);assert quick['valid']
            page.locator('#confirmCustomerBatch').check()
            with page.expect_response(lambda r:r.url.endswith('/commit')) as ordered:
                page.get_by_role('button',name='Xác nhận đồng bộ vào CSDL').click()
            order_id=ordered.value.json()['order_ids'][0]
            link=page.locator('#customerOrderLinks a');link.wait_for()
            assert link.get_attribute('href')==f'/api/orders/{order_id}/invoice.pdf'
            pdf=page.request.get(customer_server+link.get_attribute('href'))
            assert pdf.status==200 and pdf.body().startswith(b'%PDF-')
            page.goto(customer_server+'/orders')
            page.locator('#orderSearch').fill(f'quickbrowser{width}@customer-input.test')
            with page.expect_response(lambda r:'/api/orders?' in r.url):
                page.get_by_role('button',name='Lọc đơn hàng').click()
            page.get_by_role('link',name='Xuất phiếu đơn PDF').wait_for()
            assert 'Khách mua nhanh' in page.locator('#orderList').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors
            artifact=Path('.pytest_cache/customer-input-ui');artifact.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(artifact/f'category-{width}.png'),full_page=True)
        finally:browser.close()
