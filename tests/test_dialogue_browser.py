"""Kiểm thử giao diện hội thoại chatbot trong trình duyệt."""

import os
import re

import pytest

playwright = pytest.importorskip('playwright.sync_api')
from db import cursor
from test_customer_input_browser import customer_server
from test_customer_input import clean_customer_input
from test_document_uploads import document_storage
from test_chat_tools_imports import tool_cleanup, no_live_model


@pytest.mark.parametrize('width,height', [(1440,900),(390,844)])
def test_entity_choice_preview_cancel_and_safe_dom(customer_server,tool_cleanup,width,height,tmp_path):
    with playwright.sync_playwright() as driver:
        browser=driver.chromium.launch(headless=True,executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        try:
            page=browser.new_page(viewport={'width':width,'height':height})
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(customer_server+'/login?next=/chat')
            with cursor() as cur:
                cur.execute('SELECT email FROM users WHERE id=2');email=cur.fetchone()['email']
                cur.execute('SELECT SUM(quantity) AS n FROM inventory WHERE branch_id=1');before=cur.fetchone()['n']
            page.get_by_label('Email',exact=True).fill(email)
            page.get_by_label('Mật khẩu',exact=True).fill(os.environ['DEMO_ACCOUNT_PASSWORD'])
            page.get_by_role('button',name='Đăng nhập',exact=True).click();page.wait_for_url('**/chat')
            page.get_by_label('Câu hỏi',exact=True).fill('Nhập hàng: Nhà cung cấp: Kho trình duyệt; Số lượng: 2; xe SH 160i')
            page.get_by_role('button',name='Gửi',exact=True).click()
            choices=page.get_by_role('group',name='Chọn đối tượng cần thao tác')
            choices.wait_for();assert choices.get_by_role('button').count()==3
            page.wait_for_function('()=>!document.querySelector("#sendButton").disabled')
            choices.get_by_role('button').first.click()
            page.get_by_role('button',name=re.compile('^Xác nhận lệnh #')).wait_for()
            page.wait_for_function('()=>!document.querySelector("#sendButton").disabled')
            page.get_by_role('button',name='Hủy lệnh',exact=True).click()
            page.get_by_text('Đã xử lý hủy lệnh trong phiên hiện tại.',exact=True).wait_for()
            with cursor() as cur:
                cur.execute('SELECT SUM(quantity) AS n FROM inventory WHERE branch_id=1')
                assert cur.fetchone()['n']==before
            page.evaluate('''() => {const target=document.createElement('div');target.id='unsafe-result';document.body.append(target);
                renderConversationDetails(target,{clarification:{options:[{id:1,label:'<img src=x onerror=alert(1)>'}]},links:[{url:'javascript:alert(1)',label:'x'}]},document.querySelector('#questionInput'),document.querySelector('#chatForm'));}''')
            assert page.locator('#unsafe-result img').count()==0
            assert page.locator('#unsafe-result a').count()==0
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors
            page.screenshot(path=str(tmp_path/f'dialogue-{width}.png'),full_page=True)
        finally:
            browser.close()
