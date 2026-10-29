"""Kiểm thử chức năng bán hàng, đơn hàng và tạo chứng từ mô phỏng."""

from io import BytesIO  # Tạo stream trong bộ nhớ cho upload hoặc PDF.
import pdfplumber  # Đọc nội dung PDF để xác nhận chứng từ.
import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.

from db import cursor  # Mở cursor hoặc connection MySQL.
from test_customer_input import clean_customer_input,customer,stage_client,commit_client,BATCHES  # Dùng fixture và helper tạo/dọn batch nhập khách.
from test_document_uploads import document_storage  # Dùng fixture lưu trữ và helper upload tài liệu.


def test_quick_chat_creates_order_only_after_confirmation(auth_client,clean_customer_input):
    auth_client.login(3)
    response=auth_client.post('/chat',json={'question':'Thêm khách mua xe: Họ và tên: Nguyễn Thị Ánh; Email: quick@customer-input.test; Số điện thoại: 0901234567; Mã SP đã mua: SP014; Giá trị mua: 56.500.000'}).get_json()
    draft=response['customer_draft'];BATCHES.add(draft['id'])
    assert draft['valid'] and draft['rows'][0]['data']['status']=='Đã mua', draft['rows']
    with cursor() as cur:
        cur.execute('SELECT COUNT(*) AS n FROM users WHERE email=%s',('quick@customer-input.test',));assert cur.fetchone()['n']==0
    saved=auth_client.post('/chat',json={'question':'Xác nhận lưu khách hàng','customer_batch_id':draft['id'],'customer_batch_version':draft['version']}).get_json()['result']
    assert saved['created']==1 and saved['orders_created']==1
    pdf=auth_client.get(f"/api/orders/{saved['order_ids'][0]}/invoice.pdf")
    assert pdf.status_code==200 and pdf.mimetype=='application/pdf'
    with pdfplumber.open(BytesIO(pdf.data)) as doc:text='\n'.join(p.extract_text() for p in doc.pages)
    assert 'Nguyễn Thị Ánh' in text and '56.500.000 ₫' in text and 'Chờ duyệt' in text
    assert 'Phiếu xác nhận đơn hàng (mô phỏng)' in text
    assert 'Đơn chưa xác nhận thanh toán' in text


def test_quick_chat_collects_purchase_fields_sequentially(auth_client,clean_customer_input):
    auth_client.login(3)
    result=auth_client.post('/chat',json={'question':'Thêm khách mua xe: Họ và tên: Khách tuần tự; Email: sequence@customer-input.test; Số điện thoại: 0901234567'}).get_json()
    BATCHES.add(result['customer_draft']['id'])
    assert 'Mã SP' in result['answer']
    result=auth_client.post('/chat',json={'question':'SP014'}).get_json()
    assert 'Giá trị mua' in result['answer']
    result=auth_client.post('/chat',json={'question':'Giá trị mua: 56.500.000'}).get_json()
    assert result['customer_draft']['valid']


def test_malformed_customer_row_reports_validation_error(auth_client,clean_customer_input):
    auth_client.login(3)
    assert auth_client.post('/api/customer-input',json={'rows':['invalid']}).status_code==400


@pytest.mark.parametrize('user',[None,5,8])
def test_invoice_denies_without_permission(auth_client,user):
    auth_client.login(user)
    assert auth_client.get('/api/orders/1/invoice.pdf').status_code==403


def test_invoice_and_list_scope_checked_on_server(auth_client):
    auth_client.login(3)
    data=auth_client.get('/api/orders').get_json()
    assert data['rows'] and all(r['branch_code']=='NT01' for r in data['rows'])
    with cursor() as cur:
        cur.execute('SELECT id FROM orders WHERE branch_id<>1 LIMIT 1');order_id=cur.fetchone()['id']
    assert auth_client.get(f'/api/orders/{order_id}/invoice.pdf').status_code==404
    assert auth_client.get('/api/orders/999999/invoice.pdf').status_code==404
    assert auth_client.get('/api/orders?status=bad').status_code==400


def test_paid_invoice_totals_use_stored_items_and_discount(auth_client):
    auth_client.login(1)
    with cursor() as cur:
        cur.execute("SELECT id FROM orders WHERE status IN ('paid','delivered') LIMIT 1");order_id=cur.fetchone()['id']
        cur.execute('SELECT SUM(oi.quantity*oi.unit_price)-o.discount_amount AS net FROM orders o JOIN order_items oi ON oi.order_id=o.id WHERE o.id=%s GROUP BY o.id',(order_id,));net=cur.fetchone()['net']
        cur.execute("SELECT COUNT(*) AS n FROM rbac_audit_log WHERE action='invoice_export' AND target_id=%s",(order_id,));before=cur.fetchone()['n']
    response=auth_client.get(f'/api/orders/{order_id}/invoice.pdf');assert response.status_code==200
    with pdfplumber.open(BytesIO(response.data)) as doc:text='\n'.join(p.extract_text() for p in doc.pages)
    assert 'Hóa đơn bán hàng (mô phỏng)' in text
    assert f'{int(net):,}'.replace(',','.')+' ₫' in text
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM rbac_audit_log WHERE action='invoice_export' AND target_id=%s",(order_id,));assert cur.fetchone()['n']==before+1


@pytest.mark.parametrize('change',[{'status':'cancelled'},{'discount_amount':10**12}])
def test_invoice_rejects_cancelled_or_invalid_amount(auth_client,clean_customer_input,change):
    auth_client.login(3)
    draft=stage_client(auth_client,[customer(status='Đã mua',purchased_sku='SP014',purchase_amount=56500000)]).get_json()
    order_id=commit_client(auth_client,draft).get_json()['order_ids'][0]
    with cursor() as cur:
        if 'status' in change:cur.execute('UPDATE orders SET status=%s WHERE id=%s',(change['status'],order_id))
        else:cur.execute('UPDATE orders SET discount_amount=%s WHERE id=%s',(change['discount_amount'],order_id))
    response=auth_client.get(f'/api/orders/{order_id}/invoice.pdf')
    assert response.status_code==409 and response.mimetype=='application/json'
