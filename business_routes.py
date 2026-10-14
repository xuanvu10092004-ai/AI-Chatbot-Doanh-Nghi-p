from flask import request,render_template,jsonify
from db import cursor
from security import require_permission
from dashboard_service import scope_filter
from inventory_policy import LOW_STOCK_THRESHOLD


def records(kind,low_stock=False):
    page=max(1,int(request.args.get('page',1)));size=max(1,min(100,int(request.args.get('size',20))))
    if kind=='customers':
        where,params=scope_filter('customer:read','u.home_branch_id','u.id')
        source='users u JOIN customer_profiles cp ON cp.user_id=u.id LEFT JOIN branches b ON b.id=u.home_branch_id'
        columns='u.id AS customer_id,cp.customer_code,u.full_name,u.email,u.phone,b.code AS branch_code,cp.status AS customer_status,cp.province,cp.lead_source,cp.registered_at'
        searchable=['u.full_name','u.email','u.phone','cp.customer_code']
        sort_map={'name':'u.full_name','date':'cp.registered_at','status':'cp.status'}
        if request.args.get('status'):where+=' AND cp.status=%s';params+=(request.args['status'],)
    else:
        where,params=scope_filter('inventory:read','i.branch_id')
        source='inventory i JOIN branches b ON b.id=i.branch_id JOIN product_variants pv ON pv.id=i.variant_id JOIN products p ON p.id=pv.product_id'
        columns='b.code AS branch_code,p.model_name,pv.variant_name,i.quantity,pv.list_price,i.updated_at'
        searchable=['p.model_name','pv.variant_name','b.code']
        sort_map={'name':'p.model_name','quantity':'i.quantity','price':'pv.list_price'}
        if low_stock:where+=' AND i.quantity>0 AND i.quantity<%s';params+=(LOW_STOCK_THRESHOLD,)
    if request.args.get('branch'):
        where+=' AND b.code=%s';params+=(request.args['branch'],)
    if request.args.get('q'):
        where+=' AND ('+' OR '.join(column+' LIKE %s' for column in searchable)+')';params+=tuple('%'+request.args['q']+'%' for _ in searchable)
    sort=request.args.get('sort','name');direction=request.args.get('direction','asc')
    if sort not in sort_map or direction not in {'asc','desc'}:raise ValueError('Invalid sort')
    with cursor() as cur:
        cur.execute('SELECT COUNT(*) AS total FROM '+source+' WHERE '+where,params);total=cur.fetchone()['total']
        cur.execute('SELECT '+columns+' FROM '+source+' WHERE '+where+' ORDER BY '+sort_map[sort]+' '+direction.upper()+' LIMIT %s OFFSET %s',(*params,size,(page-1)*size));rows=cur.fetchall()
    return dict(rows=rows,total=total,page=page,size=size)


def register_business(app):
    for kind,permission in [('customers','customer:read'),('inventory','inventory:read')]:
        def page(dataset=kind):return render_template('records.html',dataset=dataset)
        def api(dataset=kind):
            try:return jsonify(records(dataset))
            except ValueError:return jsonify(error='invalid-filter'),400
        app.add_url_rule('/'+kind,endpoint='page_'+kind,view_func=require_permission(permission)(page))
        app.add_url_rule('/api/'+kind,endpoint='api_'+kind,view_func=require_permission(permission)(api))
    for kind,permission in [('quotes','order:read'),('opportunities','order:read'),('bookings','kb:public:read')]:
        def soon(module=kind):return render_template('soon.html',module=module),501
        app.add_url_rule('/'+kind,endpoint='soon_'+kind,view_func=require_permission(permission)(soon))
