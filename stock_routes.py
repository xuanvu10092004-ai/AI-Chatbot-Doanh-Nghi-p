from flask import jsonify,render_template,request,g
from db import cursor
from security import require_permission,permissions
from stock_service import receive_stock,list_receipts
from operations_routes import OperationRejected


def register_stock(app):
    @app.get('/stock-receipts')
    @require_permission('inventory:receive')
    def stock_page():return render_template('stock_receipts.html')

    @app.get('/api/stock-receipts/lookups')
    @require_permission('inventory:receive')
    def stock_lookups():
        grant=permissions()['inventory:receive']
        with cursor() as cur:
            cur.execute('SELECT id,code FROM branches ORDER BY id');branches=[r for r in cur.fetchall() if grant['scope']=='all' or grant['scope']=='branch' and grant['branch']==r['id']]
            cur.execute('SELECT pv.id,p.model_name,pv.variant_name FROM product_variants pv JOIN products p ON p.id=pv.product_id ORDER BY p.model_name,pv.id');variants=cur.fetchall()
        return jsonify(branches=branches,variants=variants)

    @app.get('/api/stock-receipts')
    @require_permission('inventory:receive')
    def stock_list():return jsonify(rows=list_receipts())

    @app.post('/api/stock-receipts')
    @require_permission('inventory:receive')
    def stock_receive():
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or data.get('confirmed') is not True:
            raise OperationRejected('Cần kiểm tra và xác nhận phiếu nhập trước khi ghi sổ.')
        return jsonify(receive_stock(data)),201
