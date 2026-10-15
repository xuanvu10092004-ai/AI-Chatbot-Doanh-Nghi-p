"""Công cụ danh mục xe và lịch sửa chữa: SQL cố định, CSRF, scope và audit."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation

from flask import g, jsonify, render_template, request
from mysql.connector import IntegrityError
from db import cursor
from security import require_permission, permissions, audit
from dashboard_service import scope_filter


class OperationRejected(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def payload():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise OperationRejected('Dữ liệu yêu cầu không hợp lệ.')
    return value


def text(data, key, maximum, required=True):
    value = data.get(key, '')
    if not isinstance(value, str):
        raise OperationRejected('Thông tin văn bản không hợp lệ.')
    value = value.strip()
    if len(value) > maximum or required and not value:
        raise OperationRejected('Vui lòng nhập đầy đủ thông tin, đúng độ dài cho phép.')
    return value


def number(data, key, minimum, maximum):
    try:
        raw = data[key]
        if isinstance(raw, bool):raise ValueError()
        value = Decimal(str(raw))
        if not value.is_finite() or value != value.to_integral_value() or not minimum <= value <= maximum:
            raise ValueError()
        return int(value)
    except (KeyError, InvalidOperation, ValueError, TypeError):
        raise OperationRejected('Giá trị số không hợp lệ: ' + key) from None


def register_operations(app):
    @app.errorhandler(OperationRejected)
    def rejected(error):
        return jsonify(error='operation-rejected', message=str(error)), error.status

    @app.get('/catalog')
    @require_permission('product:manage')
    def catalog_page():
        return render_template('operations.html', section='catalog')

    @app.get('/api/catalog')
    @require_permission('product:manage')
    def catalog_list():
        if permissions()['product:manage']['scope'] != 'all':
            raise OperationRejected('Danh mục dùng chung cần quyền toàn hệ thống.',403)
        with cursor() as cur:
            cur.execute('''SELECT pv.id,p.id AS product_id,p.model_name,p.segment,p.engine_cc,
                           pv.variant_name,pv.list_price,r.model_year,COALESCE(r.lifecycle,'current') AS lifecycle,
                           COALESCE(r.version,0) AS version
                           FROM product_variants pv JOIN products p ON p.id=pv.product_id
                           LEFT JOIN vehicle_releases r ON r.variant_id=pv.id
                           ORDER BY p.model_name,r.model_year DESC,pv.id''')
            rows=cur.fetchall()
        return jsonify(rows=rows)

    @app.route('/api/catalog',methods=['POST'])
    @app.route('/api/catalog/<int:variant_id>',methods=['PUT'])
    @require_permission('product:manage')
    def save_vehicle(variant_id=None,tool_data=None):
        if permissions()['product:manage']['scope'] != 'all':
            raise OperationRejected('Danh mục dùng chung cần quyền toàn hệ thống.',403)
        data=payload() if tool_data is None else tool_data
        model=text(data,'model_name',100)
        variant=text(data,'variant_name',100)
        segment=data.get('segment')
        lifecycle=data.get('lifecycle','current')
        if segment not in {'xe_so','tay_ga','con_tay'} or lifecycle not in {'current','previous','discontinued'}:
            raise OperationRejected('Phân khúc hoặc trạng thái kinh doanh không hợp lệ.')
        price=number(data,'list_price',1,10_000_000_000)
        engine=number(data,'engine_cc',1,3000)
        year=number(data,'model_year',1950,datetime.now().year+2) if data.get('model_year') not in (None,'') else None
        with cursor() as cur:
            # Cùng khóa với luồng ghi nghiệp vụ, tránh hai lần sửa ghi đè nhau.
            cur.execute('SELECT version FROM rbac_meta WHERE id=1 FOR UPDATE');cur.fetchone()
            before=None
            if variant_id:
                cur.execute('''SELECT pv.*,p.model_name,p.segment,p.engine_cc,COALESCE(r.version,0) AS version,
                            r.model_year,r.lifecycle FROM product_variants pv JOIN products p ON p.id=pv.product_id
                            LEFT JOIN vehicle_releases r ON r.variant_id=pv.id WHERE pv.id=%s FOR UPDATE''',(variant_id,))
                before=cur.fetchone()
                if not before:raise OperationRejected('Không tìm thấy phiên bản xe.',404)
                if number(data,'version',0,2**31-1)!=before['version']:
                    raise OperationRejected('Dữ liệu đã thay đổi. Hãy tải lại trước khi lưu.',409)
                product_id=before['product_id']
                cur.execute('UPDATE products SET model_name=%s,segment=%s,engine_cc=%s WHERE id=%s',(model,segment,engine,product_id))
                if (model,segment,engine)!=(before['model_name'],before['segment'],before['engine_cc']):
                    cur.execute('''INSERT INTO vehicle_releases(variant_id,updated_by)
                                SELECT id,%s FROM product_variants WHERE product_id=%s AND id<>%s
                                ON DUPLICATE KEY UPDATE version=version+1,updated_by=VALUES(updated_by)''',(g.user['id'],product_id,variant_id))
                cur.execute('UPDATE product_variants SET variant_name=%s,list_price=%s WHERE id=%s',(variant,price,variant_id))
            else:
                product_id=data.get('product_id')
                if product_id:
                    cur.execute('SELECT id FROM products WHERE id=%s',(number(data,'product_id',1,2**31-1),))
                    if not cur.fetchone():raise OperationRejected('Mẫu xe không hợp lệ.')
                else:
                    cur.execute('INSERT INTO products(model_name,segment,engine_cc) VALUES(%s,%s,%s)',(model,segment,engine))
                    product_id=cur.lastrowid
                cur.execute('INSERT INTO product_variants(product_id,variant_name,list_price,cost_price) VALUES(%s,%s,%s,0)',(product_id,variant,price))
                variant_id=cur.lastrowid
                cur.execute('INSERT INTO inventory(branch_id,variant_id,quantity) SELECT id,%s,0 FROM branches',(variant_id,))
            cur.execute('''INSERT INTO vehicle_releases(variant_id,model_year,lifecycle,updated_by) VALUES(%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE model_year=VALUES(model_year),lifecycle=VALUES(lifecycle),
                        version=version+1,updated_by=VALUES(updated_by)''',(variant_id,year,lifecycle,g.user['id']))
            # Không đưa giá vốn vào audit trả về giao diện danh mục.
            if before:before.pop('cost_price',None)
            audit(cur,'catalog_update' if before else 'catalog_create','variant',variant_id,before=before,
                  after={k:data.get(k) for k in ('model_name','variant_name','list_price','model_year','lifecycle')},actor=g.user['id'])
        return jsonify(id=variant_id),200 if before else 201

    @app.get('/bookings')
    @require_permission('booking:read')
    def bookings_page():
        return render_template('operations.html', section='bookings')

    @app.get('/api/bookings/lookups')
    @require_permission('booking:create')
    def booking_lookups():
        grant=permissions()['booking:create']
        with cursor() as cur:
            cur.execute('SELECT id,code FROM branches ORDER BY id')
            branches=[r for r in cur.fetchall() if grant['scope']!='branch' or r['id']==grant['branch']]
            where,params=scope_filter('booking:create','u.home_branch_id','u.id')
            cur.execute("SELECT u.id,u.full_name,u.phone FROM users u WHERE u.user_type='customer' AND "+where+' ORDER BY u.full_name',params)
            customers=cur.fetchall()
        return jsonify(branches=branches,customers=customers)

    @app.get('/api/bookings')
    @require_permission('booking:read')
    def booking_list():
        where,params=scope_filter('booking:read','s.branch_id','s.customer_id')
        status=request.args.get('status')
        if status:
            if status not in {'scheduled','confirmed','completed','cancelled'}:raise OperationRejected('Trạng thái không hợp lệ.')
            where+=' AND s.status=%s';params+=(status,)
        with cursor() as cur:
            cur.execute('''SELECT s.*,b.code AS branch_code,u.full_name AS customer_name FROM service_bookings s
                        JOIN branches b ON b.id=s.branch_id JOIN users u ON u.id=s.customer_id WHERE '''+where+' ORDER BY s.scheduled_at DESC,s.id DESC',params)
            rows=cur.fetchall()
        return jsonify(rows=rows)

    @app.post('/api/bookings')
    @require_permission('booking:create')
    def create_booking(tool_data=None):
        data=payload() if tool_data is None else tool_data
        branch=number(data,'branch_id',1,2**31-1)
        customer=number(data,'customer_id',1,2**31-1)
        grant=permissions()['booking:create']
        if grant['scope']=='branch' and branch!=grant['branch'] or grant['scope']=='own' and customer!=g.user['id']:
            raise OperationRejected('Thông tin đặt lịch ngoài phạm vi được cấp.',403)
        try:scheduled=datetime.fromisoformat(str(data.get('scheduled_at','')))
        except ValueError:raise OperationRejected('Ngày giờ hẹn không hợp lệ.') from None
        now=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).replace(tzinfo=None)
        if scheduled.tzinfo or not now+timedelta(minutes=10)<=scheduled<=now+timedelta(days=180) or not 7<=scheduled.hour<18:
            raise OperationRejected('Chọn lịch trước ít nhất 10 phút, trong 180 ngày và từ 07:00 đến trước 18:00.')
        service=data.get('service_type')
        if service not in {'maintenance','repair','inspection'}:raise OperationRejected('Loại dịch vụ không hợp lệ.')
        if g.user['user_type']!='staff' and service!='maintenance':raise OperationRejected('Khách chỉ có thể đặt lịch bảo dưỡng hoặc tư vấn.',403)
        vehicle=text(data,'vehicle_description',200)
        plate=text(data,'license_plate',20,False)
        notes=text(data,'notes',1000,False)
        with cursor() as cur:
            cur.execute('SELECT id FROM branches WHERE id=%s FOR UPDATE',(branch,))
            if not cur.fetchone():raise OperationRejected('Chi nhánh không hợp lệ.')
            cur.execute("SELECT id,home_branch_id FROM users WHERE id=%s AND user_type='customer' FOR UPDATE",(customer,));owner=cur.fetchone()
            if not owner or grant['scope']=='branch' and owner['home_branch_id']!=grant['branch']:
                raise OperationRejected('Khách hàng không hợp lệ trong phạm vi được cấp.',403)
            cur.execute("SELECT id FROM service_bookings WHERE customer_id=%s AND scheduled_at=%s AND status IN ('scheduled','confirmed')",(customer,scheduled))
            if cur.fetchone():raise OperationRejected('Khách hàng đã có lịch tại thời điểm này.',409)
            cur.execute('''INSERT INTO service_bookings(branch_id,customer_id,created_by,scheduled_at,service_type,vehicle_description,license_plate,notes)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)''',(branch,customer,g.user['id'],scheduled,service,vehicle,plate,notes))
            booking_id=cur.lastrowid
            audit(cur,'booking_create','booking',booking_id,after={'branch_id':branch,'scheduled_at':scheduled},actor=g.user['id'])
        return jsonify(id=booking_id),201

    @app.patch('/api/bookings/<int:booking_id>')
    @require_permission('booking:read')
    def update_booking(booking_id,tool_data=None):
        data=payload() if tool_data is None else tool_data
        status=data.get('status')
        if status not in {'confirmed','completed','cancelled'}:raise OperationRejected('Trạng thái không hợp lệ.')
        code='booking:manage' if status!='cancelled' or 'booking:manage' in permissions() else 'booking:create'
        if code not in permissions():raise OperationRejected('Bạn chưa có quyền cập nhật lịch.',403)
        where,params=scope_filter(code,'s.branch_id','s.customer_id')
        with cursor() as cur:
            cur.execute('SELECT s.* FROM service_bookings s WHERE s.id=%s AND '+where+' FOR UPDATE',(booking_id,*params));before=cur.fetchone()
            if not before:raise OperationRejected('Không tìm thấy lịch trong phạm vi được cấp.',404)
            if number(data,'version',1,2**31-1)!=before['version']:raise OperationRejected('Lịch đã thay đổi. Hãy tải lại.',409)
            transitions={'scheduled':{'confirmed','cancelled'},'confirmed':{'completed','cancelled'}}
            if status not in transitions.get(before['status'],set()):raise OperationRejected('Không thể chuyển trạng thái lịch này.',409)
            cur.execute('UPDATE service_bookings SET status=%s,version=version+1 WHERE id=%s',(status,booking_id))
            audit(cur,'booking_status','booking',booking_id,before={'status':before['status']},after={'status':status},actor=g.user['id'])
        return jsonify(id=booking_id)
