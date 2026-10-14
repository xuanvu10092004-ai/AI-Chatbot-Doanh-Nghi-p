import os
from pathlib import Path
from threading import Thread

import pytest
from werkzeug.serving import make_server

playwright=pytest.importorskip('playwright.sync_api',reason='Cần Playwright để kiểm tra giao diện tải tài liệu')
from app import app
from db import cursor
from test_document_uploads import document_storage

SAMPLES=Path(__file__).resolve().parents[1]/'data/samples/documents'


@pytest.fixture
def document_server(document_storage):
    secure=app.config['SESSION_COOKIE_SECURE'];app.config['SESSION_COOKIE_SECURE']=False
    server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown();thread.join(timeout=5);app.config['SESSION_COOKIE_SECURE']=secure


@pytest.mark.parametrize('width,height',[(1440,900),(390,844)])
def test_upload_review_publish_and_scan_warning(document_server,width,height):
    with playwright.sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        try:
            page=browser.new_page(viewport={'width':width,'height':height})
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(document_server+'/login?next=/documents')
            with cursor() as cur:cur.execute('SELECT email FROM users WHERE id=%s',(1,));email=cur.fetchone()['email']
            page.get_by_label('Email',exact=True).fill(email);page.get_by_label('Mật khẩu',exact=True).fill(os.environ['DEMO_ACCOUNT_PASSWORD'])
            page.get_by_role('button',name='Đăng nhập',exact=True).click();page.wait_for_url('**/documents')
            page.locator('#documentCategory option[value="1"]').wait_for(state='attached')
            page.locator('#documentTitle').fill('Kiểm thử parser giao diện '+str(width));page.locator('#documentCategory').select_option('1')
            page.locator('#documentFile').set_input_files(SAMPLES/'table.docx')
            with page.expect_response(lambda r:r.url.endswith('/api/documents') and r.request.method=='POST') as response:
                page.get_by_role('button',name='Tải lên và trích xuất').click()
            assert response.value.status==201
            page.locator('#extractionBlocks table').wait_for()
            assert page.locator('#extractionBlocks').inner_text().find('Phụ kiện')>=0
            assert page.locator('#publishDocument').is_disabled()
            page.locator('#reviewContent').fill('Nội dung mô phỏng đã kiểm tra.\nMã\tSố lượng\nSP01\t3')
            page.locator('#reviewConfirmed').check()
            with page.expect_response(lambda r:r.url.endswith('/review')) as review:
                page.get_by_role('button',name='Lưu bản đã kiểm tra').click()
            assert review.value.status==200
            page.wait_for_function("!document.querySelector('#publishDocument').disabled")
            with page.expect_response(lambda r:r.url.endswith('/publish')) as publication:
                page.get_by_role('button',name='Đưa vào kho tri thức').click()
            assert publication.value.status==200
            page.get_by_text('Đã vào kho tri thức',exact=True).wait_for()
            page.locator('#documentTitle').fill('Kiểm thử parser scan giao diện '+str(width));page.locator('#documentFile').set_input_files(SAMPLES/'scan.pdf')
            with page.expect_response(lambda r:r.url.endswith('/api/documents') and r.request.method=='POST') as response:
                page.get_by_role('button',name='Tải lên và trích xuất').click()
            assert response.value.status==201
            page.wait_for_function("document.querySelector('#extractionWarnings').textContent.includes('0%')")
            assert 'Cần OCR' in page.locator('#extractionWarnings').inner_text()
            assert page.locator('#publishDocument').is_disabled()
            assert page.locator('#reviewContent').input_value()==''
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors
            artifacts=Path('.pytest_cache/document-ui');artifacts.mkdir(parents=True,exist_ok=True)
            page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(artifacts/f'documents-{width}.png'),full_page=True)
        finally:browser.close()
