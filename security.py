# File này xử lý session, CSRF, xác thực, phân quyền và audit cho request Flask.
import json  # Tuần tự hóa trạng thái trước/sau trong nhật ký audit.
import os  # Đọc cấu hình cho guest và chế độ session bảo vệ.
import secrets  # Tạo token CSRF, hash giả và so sánh token an toàn.
from functools import wraps  # Giữ metadata route khi bọc decorator quyền.
from urllib.parse import urlsplit, unquote  # Kiểm tra URL chuyển hướng nội bộ sau đăng nhập.
from flask import g, session, request, redirect, url_for, jsonify, render_template  # Truy cập danh tính/session và dựng phản hồi.
from werkzeug.security import check_password_hash, generate_password_hash  # So mật khẩu với hash và tạo hash giả chống dò user.
from db import cursor  # Đọc quyền và user, ghi audit trong MySQL.

DUMMY_HASH=generate_password_hash(secrets.token_urlsafe(32))


def csrf_token():
    if 'csrf_token' not in session:session['csrf_token']=secrets.token_urlsafe(32)
    return session['csrf_token']


def safe_next(value):
    if value: value=unquote(value)
    if not value or not value.startswith('/') or value.startswith('//') or '\\' in value or any(ord(c)<32 for c in value):return None
    parsed=urlsplit(value)
    return value if not parsed.scheme and not parsed.netloc else None


def audit(cur,action,target_type,target_id=None,before=None,after=None,actor=None):
    cur.execute('INSERT INTO rbac_audit_log(actor_user_id,action,target_type,target_id,before_json,after_json,ip_address) VALUES(%s,%s,%s,%s,%s,%s,%s)',
                (actor,action,target_type,target_id,json.dumps(before,default=str,ensure_ascii=False) if before is not None else None,json.dumps(after,default=str,ensure_ascii=False) if after is not None else None,request.remote_addr))


# Gộp quyền từ role và lọc quyền của user thường; guest chỉ nhận các quyền công khai.
def get_effective_permissions(user_id):
    with cursor() as cur:
        if user_id is None:
            cur.execute("SELECT p.code AS permission_code,'all' AS data_scope,NULL AS scope_branch_id FROM permissions p JOIN role_permissions rp ON rp.permission_id=p.id JOIN roles r ON r.id=rp.role_id WHERE r.name='guest' AND r.is_active=TRUE")
        else:
            cur.execute('SELECT permission_code,data_scope,scope_branch_id FROM v_user_permissions WHERE user_id=%s',(user_id,))
        groups={}
        for row in cur.fetchall():groups.setdefault(row['permission_code'],[]).append(row)
    result={}
    for code,rows in groups.items():
        if any(r['data_scope']=='all' for r in rows):result[code]={'scope':'all','branch':None}
        elif any(r['data_scope']=='branch' for r in rows):
            branches={r['scope_branch_id'] for r in rows if r['data_scope']=='branch'}
            if len(branches)==1 and None not in branches:result[code]={'scope':'branch','branch':next(iter(branches))}
        else:result[code]={'scope':'own','branch':None}
    if user_id is not None:
        with cursor() as cur:
            cur.execute('SELECT user_type FROM users WHERE id=%s',(user_id,));person=cur.fetchone()
        if not person or person['user_type']!='staff':
            result={code:({'scope':'own','branch':None} if code.startswith('booking:') else grant)
                    for code,grant in result.items() if code in {'chatbot:use','kb:public:read','booking:read','booking:create'}}
    return result


def permissions():
    if not hasattr(g,'permissions'):g.permissions=get_effective_permissions(g.user['id'] if g.user else None)
    return g.permissions


# Chặn route ngay ở backend nếu user thiếu permission, không dựa vào việc ẩn nút trên giao diện.
def require_permission(*codes):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            if any(code not in permissions() or (code=='rbac:manage' and permissions()[code]['scope']!='all') for code in codes):
                if request.path.startswith('/api/') or request.is_json:return jsonify(error='forbidden',message='Bạn không có quyền thực hiện yêu cầu này.'),403
                return render_template('error.html',message='Bạn không có quyền vào trang này.'),403
            return fn(*args,**kwargs)
        wrapped.required_permissions=codes
        return wrapped
    return decorator


# Nạp user từ session vào request context để các route dùng cùng một danh tính đã xác thực.
def initialize_request():
    # Khôi phục user/role từ session; guest chỉ được vào các endpoint chat cho phép.
    g.user=None;g.roles=[]
    user_id=session.get('user_id')
    if user_id:
        with cursor() as cur:
            cur.execute('SELECT id,email,full_name,user_type,phone,home_branch_id,is_active,must_change_password FROM users WHERE id=%s',(user_id,))
            g.user=cur.fetchone()
            if not g.user or not g.user['is_active']:
                session.clear();g.user=None
            else:
                cur.execute('SELECT r.name,r.landing_path,r.priority,b.code AS branch_code FROM user_roles ur JOIN roles r ON r.id=ur.role_id LEFT JOIN branches b ON b.id=COALESCE(ur.scope_branch_id,%s) WHERE ur.user_id=%s AND r.is_active=TRUE AND (ur.expires_at IS NULL OR ur.expires_at>NOW()) ORDER BY r.priority,r.id',(g.user['home_branch_id'],user_id))
                g.roles=cur.fetchall()
    public=request.endpoint in {'login','static','guest_login'}
    guest=bool(session.get('guest')) and os.getenv('ALLOW_GUEST_CHAT','false').lower()=='true'
    if not public and not g.user and not guest:
        if request.path.startswith('/api/') or request.endpoint=='chat_api':return jsonify(error='authentication-required',message='Vui lòng đăng nhập.'),401
        return redirect(url_for('login',next=request.full_path.rstrip('?')))
    if guest and not public and request.endpoint not in {'home','chat_page','chat_api','chat_tools_list','logout'}:
        if request.path.startswith('/api/'):return jsonify(error='forbidden'),403
        return render_template('error.html',message='Khách chỉ sử dụng Trợ lý AI.'),403
    if request.method in {'POST','PUT','PATCH','DELETE'}:
        supplied=request.headers.get('X-CSRF-Token') or request.form.get('csrf_token','')
        if not supplied or not secrets.compare_digest(str(supplied),str(session.get('csrf_token',''))):return jsonify(error='csrf-failed',message='Phiên yêu cầu không hợp lệ. Hãy tải lại trang.'),403
    if g.user and g.user['must_change_password'] and request.endpoint not in {'change_password','logout','static'}:
        if request.path.startswith('/api/') or request.endpoint=='chat_api':return jsonify(error='password-change-required'),403
        return redirect(url_for('change_password'))


# So khớp thông tin đăng nhập với password hash rồi tạo session server-side cho user hợp lệ.
def authenticate(email,password):
    # Khóa bản ghi đăng nhập, kiểm tra hash và tăng bộ đếm sai để áp dụng khóa tạm.
    with cursor() as cur:
        cur.execute('SELECT *, locked_until IS NOT NULL AND locked_until>NOW() AS locked FROM users WHERE email=%s FOR UPDATE',(email.casefold().strip(),))
        user=cur.fetchone()
        candidate=user['password_hash'] if user else DUMMY_HASH
        try:valid=check_password_hash(candidate,password)
        except (ValueError,TypeError):valid=False
        if not user or not user['is_active'] or user['locked'] or not valid:
            if user and user['is_active'] and not user['locked']:
                cur.execute('UPDATE users SET failed_login_count=failed_login_count+1,locked_until=CASE WHEN failed_login_count>=5 THEN DATE_ADD(NOW(),INTERVAL 15 MINUTE) ELSE locked_until END WHERE id=%s',(user['id'],))
                cur.execute('SELECT locked_until IS NOT NULL AND locked_until>NOW() AS locked FROM users WHERE id=%s',(user['id'],));user['locked']=bool(cur.fetchone()['locked'])
            audit(cur,'login_locked' if user and user['locked'] else 'login_failed','user',user['id'] if user else None,actor=user['id'] if user else None)
            return None
        cur.execute('UPDATE users SET failed_login_count=0,locked_until=NULL,last_login_at=NOW() WHERE id=%s',(user['id'],))
        audit(cur,'login_success','user',user['id'],actor=user['id'])
        return {key:user[key] for key in ('id','must_change_password')}


def navigation():
    with cursor() as cur:
        cur.execute('SELECT n.*,p.code AS permission FROM nav_items n LEFT JOIN permissions p ON p.id=n.required_permission_id ORDER BY sort_order,code')
        rows=[r for r in cur.fetchall() if r['is_enabled'] and r['permission'] in permissions() and (r['permission']!='rbac:manage' or permissions()[r['permission']]['scope']=='all') and (g.user or r['code']=='chat')]
    result=[];admin_added=False
    for row in rows:
        if row['code']=='revenue':continue
        if row['code'] in {'users','roles','permissions'}:
            if admin_added:continue
            row['label']='Quản trị truy cập';admin_added=True
        result.append(row)
    return result
