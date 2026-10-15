"""Nhập hàng có chứng từ, không ghi đè số lượng tồn kho."""
from uuid import uuid4
from flask import g
from mysql.connector import IntegrityError
from db import cursor
from security import permissions,audit
from dashboard_service import scope_filter
from operations_routes import OperationRejected,number,text


def receive_stock(data):
    grant=permissions().get('inventory:receive')
    if not g.user or g.user['user_type']!='staff' or not grant:
        raise OperationRejected('Bạn không có quyền thực hiện yêu cầu này.',403)
    branch=number(data,'branch_id',1,2**31-1)
    if grant['scope']!='all' and (grant['scope']!='branch' or branch!=grant['branch']):
        raise OperationRejected('Chi nhánh ngoài phạm vi được cấp.',403)
    supplier=text(data,'supplier',200)
    reference=text(data,'reference_code',100)
    notes=text(data,'notes',1000,False)
    items=data.get('items')
    if not isinstance(items,list) or not 1<=len(items)<=100:
        raise OperationRejected('Phiếu nhập cần từ 1 đến 100 dòng hàng.')
    canonical={}
    for item in items:
        if not isinstance(item,dict):raise OperationRejected('Dòng hàng không hợp lệ.')
        variant=number(item,'variant_id',1,2**31-1);quantity=number(item,'quantity',1,100000)
        if variant in canonical:raise OperationRejected('Mỗi mã SP chỉ được xuất hiện một lần trong phiếu.')
        canonical[variant]=quantity
    try:
        with cursor() as cur:
            cur.execute('SELECT id FROM branches WHERE id=%s FOR UPDATE',(branch,))
            if not cur.fetchone():raise OperationRejected('Chi nhánh không hợp lệ.')
            for variant in sorted(canonical):
                cur.execute('SELECT id FROM product_variants WHERE id=%s',(variant,))
                if not cur.fetchone():raise OperationRejected('Mã SP không hợp lệ.')
                cur.execute('SELECT quantity FROM inventory WHERE branch_id=%s AND variant_id=%s FOR UPDATE',(branch,variant))
                row=cur.fetchone()
                if (row['quantity'] if row else 0)+canonical[variant]>2**31-1:
                    raise OperationRejected('Số lượng tồn vượt giới hạn.')
            cur.execute('INSERT INTO stock_receipts(branch_id,created_by,supplier,reference_code,notes) VALUES(%s,%s,%s,%s,%s)',(branch,g.user['id'],supplier,reference,notes))
            receipt=cur.lastrowid
            for variant,quantity in sorted(canonical.items()):
                cur.execute('INSERT INTO stock_receipt_items(receipt_id,variant_id,quantity) VALUES(%s,%s,%s)',(receipt,variant,quantity))
                cur.execute('''INSERT INTO inventory(branch_id,variant_id,quantity) VALUES(%s,%s,%s)
                            ON DUPLICATE KEY UPDATE quantity=quantity+VALUES(quantity)''',(branch,variant,quantity))
            audit(cur,'stock_receive','stock_receipt',receipt,after={'branch_id':branch,'reference_code':reference,'items':canonical},actor=g.user['id'])
        return {'id':receipt,'reference_code':reference,'received_quantity':sum(canonical.values())}
    except IntegrityError as error:
        if error.errno==1062:raise OperationRejected('Mã chứng từ đã được ghi nhận; không cộng tồn kho lần nữa.',409) from None
        raise


def list_receipts():
    where,params=scope_filter('inventory:receive','r.branch_id')
    with cursor() as cur:
        cur.execute('''SELECT r.id,r.reference_code,r.supplier,b.code AS branch_code,r.created_at,
                    SUM(ri.quantity) AS received_quantity FROM stock_receipts r
                    JOIN branches b ON b.id=r.branch_id JOIN stock_receipt_items ri ON ri.receipt_id=r.id
                    WHERE '''+where+' GROUP BY r.id,r.reference_code,r.supplier,b.code,r.created_at ORDER BY r.id DESC LIMIT 100',params)
        return cur.fetchall()
