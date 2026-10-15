"""Luồng thật desktop/mobile: nhập kho và đính kèm khách ngay trong chat."""
import os
import re
from pathlib import Path
import pytest
playwright=pytest.importorskip('playwright.sync_api')
from db import cursor
from test_customer_input_browser import customer_server
from test_customer_input import clean_customer_input,BATCHES
from test_document_uploads import document_storage
from test_chat_tools_imports import tool_cleanup,make_customer_file,no_live_model


@pytest.mark.parametrize('width,height',[(1440,1000),(390,844)])
def test_chat_receive_and_file_without_toolbar(customer_server,tool_cleanup,width,height,tmp_path):
    document_id=None;batch_id=None
    with playwright.sync_playwright() as driver:
        browser=driver.chromium.launch(headless=True,executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        page=browser.new_page(viewport={'width':width,'height':height});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(customer_server+'/login?next=/chat')
            with cursor() as cur:cur.execute('SELECT email FROM users WHERE id=1');email=cur.fetchone()['email']
            page.get_by_label('Email',exact=True).fill(email);page.get_by_label('Mật khẩu',exact=True).fill(os.environ['DEMO_ACCOUNT_PASSWORD']);page.get_by_role('button',name='Đăng nhập',exact=True).click();page.wait_for_url('**/chat')
            with cursor() as cur:cur.execute('SELECT quantity FROM inventory WHERE branch_id=1 AND variant_id=14');before=cur.fetchone()['quantity']
            page.get_by_label('Câu hỏi',exact=True).fill('Nhập hàng: Chi nhánh: NT01; Nhà cung cấp: Kho giao diện; Mã SP: SP014; Số lượng: 2')
            page.get_by_role('button',name='Gửi',exact=True).click()
            page.get_by_role('button',name=re.compile('^Xác nhận lệnh #')).wait_for()
            with cursor() as cur:cur.execute('SELECT quantity FROM inventory WHERE branch_id=1 AND variant_id=14');assert cur.fetchone()['quantity']==before
            with page.expect_response(lambda r:r.url.endswith('/chat') and r.request.method=='POST') as confirmed:
                page.get_by_role('button',name=re.compile('^Xác nhận lệnh #')).click()
            assert confirmed.value.json()['result']['received_quantity']==2
            page.wait_for_function('()=>!document.querySelector("#sendButton").disabled')
            file=tmp_path/'customers.docx';file.write_bytes(make_customer_file('docx',f'toolbrowser{width}@customer-input.test').read())
            page.locator('#chatCustomerFile').set_input_files(file)
            with page.expect_response(lambda r:r.url.endswith('/api/chat/customer-file')) as uploaded:
                page.get_by_role('button',name='Gửi',exact=True).click()
            result=uploaded.value.json();assert uploaded.value.status==201,result
            document_id=result['document_id'];batch_id=result['customer_draft']['id'];BATCHES.add(batch_id)
            with page.expect_response(lambda r:r.url.endswith('/chat') and r.request.method=='POST') as committed:
                page.get_by_role('button',name='Xác nhận lưu khách hàng',exact=True).click()
            assert committed.value.json()['result']['created']==1
            page.get_by_role('link',name='Xem danh sách khách hàng vừa đồng bộ').click()
            page.wait_for_function('()=>document.querySelector("#recordTable").textContent.includes("@customer-input.test")')
            assert f'toolbrowser{width}@customer-input.test' in page.locator('#recordTable').inner_text()
            page.wait_for_function('()=>document.querySelector("#customerImportHistory").textContent.includes("DOCX")')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors,errors
            folder=Path('.pytest_cache/chat-tools');folder.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(folder/f'imported-customers-{width}.png'),full_page=True)
        finally:
            browser.close()
            if document_id:
                with cursor() as cur:
                    if batch_id:cur.execute('DELETE FROM customer_input_batches WHERE id=%s',(batch_id,));BATCHES.discard(batch_id)
                    cur.execute("DELETE FROM rbac_audit_log WHERE target_type='document' AND target_id=%s",(document_id,));cur.execute('DELETE FROM document_uploads WHERE id=%s',(document_id,))
