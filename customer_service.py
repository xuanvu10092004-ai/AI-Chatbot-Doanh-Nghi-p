"""One permission boundary and transaction for customer editing and soft deletion."""
from functools import wraps

from flask import g, jsonify
from mysql.connector import IntegrityError

from db import cursor, transaction
from security import get_effective_permissions, audit

ADMIN_PERMISSION = 'customer:admin:manage'


class CustomerError(ValueError):
    def __init__(self,message,status=400):
        super().__init__(message)
        self.status=status


def is_customer_admin():
    if not getattr(g,'user',None) or g.user['user_type']!='staff':return False
    grant=get_effective_permissions(g.user['id']).get(ADMIN_PERMISSION)
    if not grant or grant['scope']!='all':return False
    with cursor() as cur:
        cur.execute("SELECT 1 FROM v_user_permissions WHERE user_id=%s AND role_name='super_admin' AND permission_code=%s AND data_scope='all' LIMIT 1",(g.user['id'],ADMIN_PERMISSION))
        return cur.fetchone() is not None


def require_customer_admin():
    if not is_customer_admin():raise CustomerError('Bạn không có quyền thực hiện yêu cầu này.',403)


def customer_admin_only(fn):
    @wraps(fn)
    def wrapped(*args,**kwargs):
        require_customer_admin()
        return fn(*args,**kwargs)
    return wrapped


def _load(cur,customer_id,lock=False):
    cur.execute('''SELECT u.id,u.email,u.full_name,u.phone,u.home_branch_id,b.code AS branch_code,
        cp.customer_code,cp.gender,cp.birth_date,cp.province,cp.district,cp.address,cp.occupation,
        cp.lead_source,cp.interested_product_id,p.model_name AS interested_model,
        cp.payment_preference,cp.registered_at,cp.status,s.version,s.deleted_at,s.deleted_by,s.restored_at
        FROM users u JOIN customer_profiles cp ON cp.user_id=u.id
        JOIN customer_admin_state s ON s.customer_id=u.id
        LEFT JOIN branches b ON b.id=u.home_branch_id LEFT JOIN products p ON p.id=cp.interested_product_id
        WHERE u.id=%s AND u.user_type='customer' '''+('FOR UPDATE' if lock else ''),(customer_id,))
    row=cur.fetchone()
    if not row:raise CustomerError('Không tìm thấy khách hàng trong phạm vi được cấp.',404)
    return row


def get_customer(customer_id):
    require_customer_admin()
    with cursor() as cur:return _load(cur,customer_id)


def validate_changes(cur,before,changes):
    from customer_input import FIELDS,normalize_row
    writable=set(FIELDS)-{'purchased_sku','purchase_amount'}
    if not isinstance(changes,dict) or set(changes)-writable:
        raise CustomerError('Thông tin sửa khách hàng không hợp lệ; không sửa đơn mua lịch sử qua hồ sơ.')
    merged={key:before.get(key) for key in writable};merged.update(changes)
    row,errors=normalize_row(merged)
    # Profile editing never creates or alters historical purchases.
    errors=[e for e in errors if e!='Khách Đã mua cần mã SP và giá trị mua để ghi nhận đơn hàng.']
    if errors:raise CustomerError(' '.join(errors))
    cur.execute('SELECT id FROM branches WHERE code=%s',(row['branch_code'],));branch=cur.fetchone()
    if not branch:raise CustomerError('Chi nhánh không hợp lệ.')
    product=None
    if row['interested_model']:
        cur.execute('SELECT id FROM products WHERE model_name=%s',(row['interested_model'],));product=cur.fetchone()
        if not product:raise CustomerError('Mẫu xe quan tâm không hợp lệ.')
    cur.execute('SELECT id FROM users WHERE email=%s AND id<>%s',(row['email'],before['id']))
    if cur.fetchone():raise CustomerError('Email đã được sử dụng.',409)
    cur.execute('SELECT user_id FROM customer_profiles WHERE customer_code=%s AND user_id<>%s',(row['customer_code'],before['id']))
    if not row['customer_code'] or cur.fetchone():raise CustomerError('Mã khách hàng không hợp lệ hoặc đã được sử dụng.',409)
    return row,branch['id'],product['id'] if product else None


def mutate_customer(customer_id,operation,version,changes=None,confirmed=False):
    require_customer_admin()
    if operation not in {'update','delete','restore'}:raise CustomerError('Thao tác không hợp lệ.')
    if operation!='update' and confirmed is not True:raise CustomerError('Cần xác nhận thao tác với khách hàng.')
    with transaction():
        with cursor() as cur:
            # Share the same lock order as imports/account administration.
            cur.execute('SELECT version FROM rbac_meta WHERE id=1 FOR UPDATE');cur.fetchone()
            before=_load(cur,customer_id,True)
            if operation=='delete' and before['deleted_at']:
                return {'customer':before,'already_deleted':True,'excel_sync':_sync_status()}
            if operation=='restore' and not before['deleted_at']:
                return {'customer':before,'already_restored':True,'excel_sync':_sync_status()}
            if isinstance(version,bool) or not isinstance(version,int) or version!=before['version']:
                raise CustomerError('Hồ sơ đã thay đổi. Hãy tải lại trước khi xác nhận.',409)
            if operation=='update':
                if before['deleted_at']:raise CustomerError('Không sửa khách đã xóa; cần khôi phục trước.',409)
                row,branch,product=validate_changes(cur,before,changes)
                try:
                    cur.execute('UPDATE users SET email=%s,full_name=%s,phone=%s,home_branch_id=%s WHERE id=%s',
                                (row['email'],row['full_name'],row['phone'],branch,customer_id))
                    cur.execute('''UPDATE customer_profiles SET customer_code=%s,gender=%s,birth_date=%s,province=%s,district=%s,
                        address=%s,occupation=%s,lead_source=%s,interested_product_id=%s,payment_preference=%s,registered_at=%s,status=%s WHERE user_id=%s''',
                        (row['customer_code'],row['gender'] or None,row['birth_date'] or None,row['province'] or None,row['district'] or None,
                         row['address'] or None,row['occupation'] or None,row['lead_source'] or None,product,row['payment_preference'] or None,row['registered_at'],row['status'],customer_id))
                except IntegrityError:raise CustomerError('Thông tin khách hàng bị trùng; chưa lưu thay đổi.',409) from None
                cur.execute('UPDATE customer_admin_state SET version=version+1 WHERE customer_id=%s',(customer_id,))
            elif operation=='delete':
                cur.execute('UPDATE customer_admin_state SET deleted_at=NOW(),deleted_by=%s,version=version+1 WHERE customer_id=%s',(g.user['id'],customer_id))
            else:
                cur.execute('UPDATE customer_admin_state SET deleted_at=NULL,deleted_by=NULL,restored_at=NOW(),version=version+1 WHERE customer_id=%s',(customer_id,))
            after=_load(cur,customer_id)
            audit(cur,'customer_'+operation,'customer',customer_id,before,after,actor=g.user['id'])
    return {'customer':after,'excel_sync':_sync_status()}


def _sync_status():
    from excel_sync import sync_after_commit
    return sync_after_commit()


def register_customers(app):
    from flask import request
    @app.errorhandler(CustomerError)
    def rejected(error):return jsonify(error='customer-rejected',message=str(error)),error.status

    @app.get('/api/customers/<int:customer_id>')
    @customer_admin_only
    def customer_detail(customer_id):return jsonify(customer=get_customer(customer_id))

    @app.patch('/api/customers/<int:customer_id>')
    @customer_admin_only
    def customer_update(customer_id):
        data=request.get_json(silent=True)
        if not isinstance(data,dict):raise CustomerError('Dữ liệu không hợp lệ.')
        return jsonify(mutate_customer(customer_id,'update',data.get('version'),{k:v for k,v in data.items() if k!='version'}))

    @app.delete('/api/customers/<int:customer_id>')
    @customer_admin_only
    def customer_delete(customer_id):return _status_change(customer_id,'delete')

    @app.post('/api/customers/<int:customer_id>/restore')
    @customer_admin_only
    def customer_restore(customer_id):return _status_change(customer_id,'restore')

    def _status_change(customer_id,operation):
        data=request.get_json(silent=True)
        if not isinstance(data,dict):raise CustomerError('Dữ liệu không hợp lệ.')
        return jsonify(mutate_customer(customer_id,operation,data.get('version'),confirmed=data.get('confirmed')))
