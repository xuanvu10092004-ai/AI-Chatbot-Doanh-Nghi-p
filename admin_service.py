# Kiểm tra bất biến RBAC rồi lưu thay đổi tài khoản, vai trò và nhật ký audit.
from datetime import datetime, timezone  # Đổi hạn vai trò sang UTC trước khi ghi MySQL.
from flask import g  # Lấy danh tính người đang thực hiện thay đổi trong request.
from werkzeug.security import generate_password_hash  # Lưu mật khẩu dưới dạng hash, không lưu bản rõ.
from db import cursor  # Gom các thao tác ghi RBAC trong transaction của MySQL.
from security import audit, permissions  # Ghi nhật ký và so quyền người thao tác với thay đổi yêu cầu.


# Lỗi nghiệp vụ được route đổi thành phản hồi từ chối mà không lộ chi tiết CSDL.
class AdminRejected(ValueError):pass


def bool_value(value):
    if value not in (True,False,0,1):raise AdminRejected('Giá trị bật/tắt không hợp lệ.')
    return bool(value)


# Chỉ chấp nhận chuỗi mật khẩu từ 10 đến 256 ký tự rồi trả về hash để lưu.
def validate_password(password):
    if not isinstance(password,str) or len(password)<10 or len(password)>256:raise AdminRejected('Mật khẩu cần 10–256 ký tự.')
    return generate_password_hash(password)


# Đảm bảo thao tác không xóa admin cuối, tự khóa user hay tự gỡ quyền RBAC.
def check_invariants(cur,actor,had_manage):
    cur.execute("SELECT COUNT(DISTINCT user_id) AS n FROM v_user_permissions WHERE role_name='super_admin'")
    if cur.fetchone()['n']<1:raise AdminRejected('Không được xóa hoặc hạ quyền quản trị viên cuối cùng.')
    cur.execute('SELECT is_active FROM users WHERE id=%s',(actor,))
    if not cur.fetchone()['is_active']:raise AdminRejected('Không được tự khóa tài khoản.')
    if had_manage:
        cur.execute("SELECT 1 FROM v_user_permissions WHERE user_id=%s AND permission_code='rbac:manage' LIMIT 1",(actor,))
        if not cur.fetchone():raise AdminRejected('Không được tự gỡ quyền quản trị RBAC.')
    cur.execute("""SELECT vp.user_id FROM v_user_permissions vp WHERE vp.data_scope='branch'
      AND NOT EXISTS(SELECT 1 FROM v_user_permissions allp WHERE allp.user_id=vp.user_id AND allp.permission_code=vp.permission_code AND allp.data_scope='all')
      GROUP BY vp.user_id HAVING COUNT(DISTINCT vp.scope_branch_id)>1 LIMIT 1""")
    if cur.fetchone():raise AdminRejected('Chưa hỗ trợ một tài khoản bị giới hạn tại nhiều chi nhánh.')


def mutate(kind,target_id,data,operation='save'):
    # Chụp người thao tác và trạng thái quyền trước khi khóa metadata RBAC.
    actor=g.user['id'];had_manage='rbac:manage' in permissions()
    if kind in {'user','assignment'} and target_id:
        with cursor() as cur:
            cur.execute('SELECT user_type,full_name,home_branch_id FROM users WHERE id=%s',(target_id,));person=cur.fetchone()
            if person and person['user_type']=='customer':
                from customer_service import require_customer_admin,CustomerError
                require_customer_admin()
                cur.execute('SELECT deleted_at FROM customer_admin_state WHERE customer_id=%s',(target_id,));state=cur.fetchone()
                if state and state['deleted_at']:raise CustomerError('Khách hàng đã xóa; hãy khôi phục bằng chức năng Khách hàng.',409)
                if any(key in data and data[key]!=person.get(key) for key in ('full_name','home_branch_id','email','phone')):
                    raise CustomerError('Sử dụng chức năng Sửa khách hàng để kiểm tra phiên bản hồ sơ.',409)
    if kind in {'user','assignment'}:
        grant=permissions()['user:manage']
        if grant['scope']!='all':
            with cursor() as check:
                check.execute('SELECT home_branch_id FROM users WHERE id=%s',(target_id or actor,));target=check.fetchone()
            if target_id and (not target or (grant['scope']=='branch' and target['home_branch_id']!=grant['branch']) or (grant['scope']=='own' and target_id!=actor)):
                raise AdminRejected('Tài khoản ngoài phạm vi quản trị của bạn.')
            if 'home_branch_id' in data and grant['scope']=='branch' and data['home_branch_id']!=grant['branch']:raise AdminRejected('Chi nhánh ngoài phạm vi quản trị.')
            if not target_id and grant['scope']=='own':raise AdminRejected('Không có quyền tạo tài khoản mới.')
    with cursor() as cur:
        # Khóa version toàn cục để các thay đổi quyền đồng thời được tuần tự hóa.
        cur.execute('SELECT version FROM rbac_meta WHERE id=1 FOR UPDATE');cur.fetchone()
        before=None;after=None
        if kind=='role':
            if target_id:
                cur.execute('SELECT * FROM roles WHERE id=%s',(target_id,));before=cur.fetchone()
                if not before:raise AdminRejected('Không tìm thấy vai trò.')
                cur.execute('SELECT permission_id,data_scope FROM role_permissions WHERE role_id=%s',(target_id,));before['permissions']=cur.fetchall()
                if before['name']=='super_admin':raise AdminRejected('Vai trò super_admin được bảo vệ và luôn có tất cả quyền.')
                if operation=='delete':
                    cur.execute('SELECT COUNT(*) AS n FROM user_roles WHERE role_id=%s',(target_id,));used=cur.fetchone()['n']
                    if before['is_system'] or used:raise AdminRejected('Vai trò hệ thống hoặc đang được sử dụng không được xóa.')
                    cur.execute('DELETE FROM role_permissions WHERE role_id=%s',(target_id,));cur.execute('DELETE FROM roles WHERE id=%s',(target_id,))
                else:
                    name=data.get('name',before['name'])
                    if before['is_system'] and name!=before['name']:raise AdminRejected('Không được đổi tên vai trò hệ thống.')
                    landing=data.get('landing_path',before['landing_path'])
                    if landing not in {'/dashboard','/chat','/customers','/inventory'}:raise AdminRejected('Trang đích không hợp lệ.')
                    cur.execute('UPDATE roles SET name=%s,description=%s,is_active=%s,landing_path=%s,priority=%s WHERE id=%s',(name,data.get('description',before['description']),bool_value(data.get('is_active',before['is_active'])),landing,int(data.get('priority',before['priority'])),target_id))
            else:
                name=data.get('name','').strip()
                if not name or len(name)>50:raise AdminRejected('Tên vai trò không hợp lệ.')
                landing=data.get('landing_path','/dashboard')
                if landing not in {'/dashboard','/chat','/customers','/inventory'}:raise AdminRejected('Trang đích không hợp lệ.')
                cur.execute('INSERT INTO roles(name,description,landing_path,priority) VALUES(%s,%s,%s,%s)',(name,data.get('description',''),landing,int(data.get('priority',100))));target_id=cur.lastrowid
                if data.get('clone_id'):
                    cur.execute('INSERT INTO role_permissions(role_id,permission_id,data_scope) SELECT %s,permission_id,data_scope FROM role_permissions WHERE role_id=%s',(target_id,int(data['clone_id'])))
            if operation!='delete' and 'permissions' in data:
                if not isinstance(data['permissions'],list):raise AdminRejected('Danh sách quyền không hợp lệ.')
                cur.execute('SELECT permission_id,data_scope FROM role_permissions WHERE role_id=%s',(target_id,));old_permissions=cur.fetchall()
                if before:before['permissions']=old_permissions
                cur.execute('DELETE FROM role_permissions WHERE role_id=%s',(target_id,))
                for grant in data['permissions']:
                    cur.execute('SELECT code FROM permissions WHERE id=%s',(int(grant['permission_id']),));permission=cur.fetchone()
                    if permission and permission['code']=='customer:admin:manage':raise AdminRejected('Quyền sửa khách chỉ dành cho super_admin.')
                    if grant.get('data_scope') not in {'all','branch','own'}:raise AdminRejected('Phạm vi quyền không hợp lệ.')
                    cur.execute('INSERT INTO role_permissions(role_id,permission_id,data_scope) VALUES(%s,%s,%s)',(target_id,int(grant['permission_id']),grant['data_scope']))
            if operation!='delete':
                cur.execute('SELECT * FROM roles WHERE id=%s',(target_id,));after=cur.fetchone()
                cur.execute('SELECT permission_id,data_scope FROM role_permissions WHERE role_id=%s',(target_id,));after['permissions']=cur.fetchall()
        elif kind=='user':
            if target_id:
                cur.execute('SELECT id,email,full_name,home_branch_id,is_active,must_change_password FROM users WHERE id=%s',(target_id,));before=cur.fetchone()
                if not before:raise AdminRejected('Không tìm thấy tài khoản.')
                cur.execute('SELECT role_id,scope_branch_id,expires_at FROM user_roles WHERE user_id=%s',(target_id,));before['roles']=cur.fetchall()
                if 'locked_until' in data and target_id==actor:raise AdminRejected('Không được tự khóa tài khoản.')
                cur.execute('UPDATE users SET full_name=%s,home_branch_id=%s,is_active=%s WHERE id=%s',(data.get('full_name',before['full_name']),data.get('home_branch_id',before['home_branch_id']),bool_value(data.get('is_active',before['is_active'])),target_id))
                if data.get('unlock'):
                    cur.execute('UPDATE users SET failed_login_count=0,locked_until=NULL WHERE id=%s',(target_id,))
                if data.get('lock'):
                    if target_id==actor:raise AdminRejected('Không được tự khóa tài khoản.')
                    cur.execute('UPDATE users SET locked_until=DATE_ADD(NOW(),INTERVAL 15 MINUTE) WHERE id=%s',(target_id,))
                if data.get('password'):
                    cur.execute('UPDATE users SET password_hash=%s,must_change_password=TRUE,password_updated_at=NOW() WHERE id=%s',(validate_password(data['password']),target_id))
            else:
                email=data.get('email','').strip().casefold();name=data.get('full_name','').strip()
                if '@' not in email or len(email)>255 or not name:raise AdminRejected('Email và họ tên không hợp lệ.')
                cur.execute("INSERT INTO users(email,full_name,user_type,home_branch_id,password_hash,must_change_password,password_updated_at) VALUES(%s,%s,'staff',%s,%s,TRUE,NOW())",(email,name,data.get('home_branch_id'),validate_password(data.get('password'))));target_id=cur.lastrowid
            if 'roles' in data:
                set_roles(cur,target_id,data['roles'])
            cur.execute('SELECT id,email,full_name,home_branch_id,is_active,must_change_password,locked_until FROM users WHERE id=%s',(target_id,));after=cur.fetchone()
            cur.execute('SELECT role_id,scope_branch_id,expires_at FROM user_roles WHERE user_id=%s',(target_id,));after['roles']=cur.fetchall()
        elif kind=='assignment':
            cur.execute('SELECT role_id,scope_branch_id,expires_at FROM user_roles WHERE user_id=%s',(target_id,));before=cur.fetchall()
            if operation=='delete':cur.execute('DELETE FROM user_roles WHERE user_id=%s AND role_id=%s',(target_id,int(data['role_id'])))
            else:set_roles(cur,target_id,data.get('roles'),replace=False)
            cur.execute('SELECT role_id,scope_branch_id,expires_at FROM user_roles WHERE user_id=%s',(target_id,));after=cur.fetchall()
        elif kind=='permission':
            cur.execute('SELECT id,code,description FROM permissions WHERE id=%s',(target_id,));before=cur.fetchone()
            if not before:raise AdminRejected('Không tìm thấy quyền.')
            cur.execute('UPDATE permissions SET description=%s WHERE id=%s',(data.get('description',''),target_id));after={**before,'description':data.get('description','')}
        else:raise AdminRejected('Thao tác không hợp lệ.')
        check_invariants(cur,actor,had_manage)
        action=('lock_user' if data.get('lock') else 'unlock_user' if data.get('unlock') else 'password_reset' if data.get('password') and before else operation+'_'+kind)
        audit(cur,action,kind,target_id,before,after,actor=actor)
        cur.execute('UPDATE rbac_meta SET version=version+1 WHERE id=1')
    return target_id


def set_roles(cur,user_id,roles,replace=True):
    # Kiểm tra từng role và chặn gán quyền rộng hơn phạm vi của người quản trị.
    if not isinstance(roles,list):raise AdminRejected('Danh sách vai trò không hợp lệ.')
    for assignment in roles:
        cur.execute('SELECT name FROM roles WHERE id=%s',(int(assignment['role_id']),));role=cur.fetchone()
        if not role:raise AdminRejected('Vai trò không tồn tại.')
        if role['name']=='super_admin':
            cur.execute("SELECT 1 FROM v_user_permissions WHERE user_id=%s AND role_name='super_admin' LIMIT 1",(g.user['id'],))
            if not cur.fetchone():raise AdminRejected('Chỉ super_admin có thể gán super_admin.')
        if permissions().get('rbac:manage',{}).get('scope')!='all':
            cur.execute('SELECT p.code,rp.data_scope FROM role_permissions rp JOIN permissions p ON p.id=rp.permission_id WHERE rp.role_id=%s',(int(assignment['role_id']),))
            for row in cur.fetchall():
                owned=permissions().get(row['code'])
                if not owned or (owned['scope']!='all' and row['data_scope']=='all') or (owned['scope']=='own' and row['data_scope']=='branch'):
                    raise AdminRejected('Không được gán quyền rộng hơn quyền của người quản trị.')
                if owned['scope']=='branch' and row['data_scope']=='branch' and assignment.get('scope_branch_id')!=owned['branch']:
                    raise AdminRejected('Không được gán quyền ngoài chi nhánh được quản trị.')
    if replace:cur.execute('DELETE FROM user_roles WHERE user_id=%s',(user_id,))
    for assignment in roles:
        expiry=assignment.get('expires_at') or None
        if expiry:
            try:
                expiry=datetime.fromisoformat(expiry)
                if expiry.tzinfo:expiry=expiry.astimezone(timezone.utc).replace(tzinfo=None)
            except (ValueError,TypeError):raise AdminRejected('Ngày hết hạn không hợp lệ.')
        cur.execute('INSERT INTO user_roles(user_id,role_id,scope_branch_id,expires_at,granted_by) VALUES(%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE scope_branch_id=VALUES(scope_branch_id),expires_at=VALUES(expires_at),granted_by=VALUES(granted_by)',(user_id,int(assignment['role_id']),assignment.get('scope_branch_id'),expiry,g.user['id']))
