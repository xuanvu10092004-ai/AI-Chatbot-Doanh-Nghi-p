"""Kiểm thử giao diện quản trị khách hàng trên trình duyệt."""

import os
from threading import Thread,Event
import time

from openpyxl import load_workbook
import pytest

playwright=pytest.importorskip('playwright.sync_api')
from db import cursor
from excel_sync import SOURCE_WORKBOOK
from excel_sync_worker import process_sync
from test_customer_input_browser import customer_server
from test_customer_input import clean_customer_input
from test_customer_admin import target
from test_document_uploads import document_storage
from test_chat_tools_imports import no_live_model


@pytest.fixture
def running_worker(tmp_path,monkeypatch):
    output=tmp_path/'official.xlsx';monkeypatch.setattr('excel_sync.SYNCED_WORKBOOK',output)
    stop=Event();errors=[]
    def run():
        while not stop.is_set():
            try:
                result=process_sync()
                if result['status']=='failed':errors.append(result)
            except Exception as error:errors.append(str(error))
            stop.wait(.1)
    thread=Thread(target=run);thread.start()
    yield output
    stop.set();thread.join(timeout=10)
    assert not thread.is_alive() and not errors,errors


def wait_export(output,expected):
    for _ in range(100):
        if output.exists():
            book=load_workbook(output,read_only=True,data_only=True)
            try:
                names={row[1] for row in book['Khach_hang'].iter_rows(min_row=2,values_only=True) if row[6]=='new@customer-input.test'}
                if names==expected:return
            finally:book.close()
        time.sleep(.05)
    pytest.fail('Worker không tự cập nhật workbook sau thay đổi website.')


@pytest.mark.parametrize('width,height',[(1440,1000),(390,844)])
def test_admin_edit_delete_restore_buttons_and_automatic_excel(customer_server,target,running_worker,width,height):
    before=SOURCE_WORKBOOK.read_bytes()
    with playwright.sync_playwright() as driver:
        browser=driver.chromium.launch(headless=True,executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        try:
            page=browser.new_page(viewport={'width':width,'height':height});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(customer_server+'/login?next=/customers')
            with cursor() as cur:cur.execute('SELECT email FROM users WHERE id=1');email=cur.fetchone()['email']
            page.get_by_label('Email',exact=True).fill(email);page.get_by_label('Mật khẩu',exact=True).fill(os.environ['DEMO_ACCOUNT_PASSWORD'])
            page.get_by_role('button',name='Đăng nhập',exact=True).click();page.wait_for_url('**/customers')
            assert page.get_by_role('link',name='+ Thêm khách mua xe',exact=True).count()==1
            page.locator('#q').fill('new@customer-input.test');page.get_by_role('button',name='Lọc',exact=True).click()
            page.locator('#recordTable').get_by_role('button',name='Sửa',exact=True).click()
            page.locator('#editCustomer_full_name').fill('Khách được admin sửa')
            page.get_by_role('button',name='Lưu thay đổi',exact=True).click()
            page.locator('#customerEditor').wait_for(state='hidden')
            page.locator('#recordTable').get_by_text('Khách được admin sửa',exact=True).wait_for()
            wait_export(running_worker,{'Khách được admin sửa'})
            page.on('dialog',lambda d:d.accept())
            page.locator('#recordTable').get_by_role('button',name='Xóa',exact=True).click()
            page.locator('#recordTable').get_by_text('Chưa có kết quả trong phạm vi của bạn.',exact=True).wait_for()
            wait_export(running_worker,set())
            page.locator('#deletedCustomers').check()
            page.locator('#recordTable').get_by_role('button',name='Khôi phục',exact=True).click()
            page.locator('#recordTable').get_by_text('Chưa có kết quả trong phạm vi của bạn.',exact=True).wait_for()
            wait_export(running_worker,{'Khách được admin sửa'})
            assert page.get_by_role('button',name='Trang trước',exact=True).count()==1
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert SOURCE_WORKBOOK.read_bytes()==before and not errors,errors
        finally:browser.close()
