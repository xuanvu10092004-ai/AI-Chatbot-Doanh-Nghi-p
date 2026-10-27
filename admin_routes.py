# Đăng ký trang và API quản lý user, role, permission cùng audit log.
from flask import request, render_template, jsonify  # Đọc bộ lọc request và tạo phản hồi HTML/JSON.
from mysql.connector import IntegrityError  # Nhận lỗi ràng buộc khi dữ liệu admin bị trùng.
from db import cursor  # Chạy các truy vấn MySQL trong phạm vi từng request.
from security import require_permission  # Bảo vệ mỗi route bằng permission ở backend.
from admin_service import mutate, AdminRejected  # Giao cập nhật RBAC cho service và ánh xạ lỗi nghiệp vụ.
from dashboard_service import scope_filter  # Áp dụng giới hạn chi nhánh hoặc user cho danh sách.


# Đăng ký các endpoint của nhóm admin để Flask chuyển request vào đúng hàm.
def register_admin(app):
    @app.errorhandler(AdminRejected)
    def admin_error(error):return jsonify(error='rejected',message=str(error)),400

    for kind,permission in [('users','user:manage'),('roles','rbac:manage'),('permissions','rbac:manage'),('audit','audit:read')]:
        def page(section=kind):return render_template('admin.html',section=section)
        app.add_url_rule('/admin/'+kind,endpoint='admin_page_'+kind,view_func=require_permission(permission)(page))

    @app.get('/api/admin/users')
    @require_permission('user:manage')
    def users_list():
        # Lọc user theo quyền quản trị, giới hạn kết quả để bảng không tải quá nhiều dòng.
        search='%'+request.args.get('q','')+'%'
        where,params=scope_filter('user:manage','home_branch_id','id')
        with cursor() as cur:
            cur.execute('SELECT id,email,full_name,home_branch_id,is_active,must_change_password,locked_until FROM users WHERE '+where+' AND (email LIKE %s OR full_name LIKE %s) ORDER BY id LIMIT 100',(*params,search,search));rows=cur.fetchall()
            cur.execute('SELECT user_id,role_id,scope_branch_id,expires_at FROM user_roles ORDER BY user_id,role_id');grants=cur.fetchall()
            for row in rows:row['roles']=[r for r in grants if r['user_id']==row['id']]
        return jsonify(rows=rows)

    @app.get('/api/admin/roles')
    @require_permission('rbac:manage')
    def roles_list():
        with cursor() as cur:
            cur.execute('SELECT * FROM roles ORDER BY priority,id');rows=cur.fetchall()
            cur.execute('SELECT role_id,permission_id,data_scope FROM role_permissions');grants=cur.fetchall()
            cur.execute('SELECT id FROM permissions');all_permissions=cur.fetchall()
            for row in rows:row['permissions']=[{'permission_id':p['id'],'data_scope':'all'} for p in all_permissions] if row['name']=='super_admin' else [r for r in grants if r['role_id']==row['id']]
        return jsonify(rows=rows)

    @app.get('/api/admin/permissions')
    @require_permission('rbac:manage')
    def permission_list():
        with cursor() as cur:cur.execute('SELECT id,code,description,SUBSTRING_INDEX(code,":",1) AS permission_group FROM permissions ORDER BY code');rows=cur.fetchall()
        return jsonify(rows=rows)

    @app.get('/api/admin/lookups')
    @require_permission('user:manage')
    def lookups():
        with cursor() as cur:
            cur.execute('SELECT id,name FROM roles WHERE is_active=TRUE ORDER BY priority,id');roles=cur.fetchall()
            cur.execute('SELECT id,code FROM branches ORDER BY id');branches=cur.fetchall()
        return jsonify(roles=roles,branches=branches)

    @app.get('/api/admin/audit')
    @require_permission('audit:read')
    def audit_list():
        scope,values=scope_filter('audit:read','au.home_branch_id','l.actor_user_id')
        filters=[scope];params=list(values)
        # Ghép điều kiện audit theo tên cột cố định; giá trị lọc luôn bind qua parameters.
        for key,column in [('actor','l.actor_user_id'),('action','l.action')]:
            if request.args.get(key):filters.append(column+'=%s');params.append(request.args[key])
        for key,operator in [('from','>='),('to','<=')]:
            if request.args.get(key):filters.append('l.created_at'+operator+'%s');params.append(request.args[key])
        with cursor() as cur:
            cur.execute('SELECT l.* FROM rbac_audit_log l LEFT JOIN users au ON au.id=l.actor_user_id WHERE '+' AND '.join(filters)+' ORDER BY l.id DESC LIMIT 100',tuple(params));rbac=cur.fetchall()
            scope,values=scope_filter('audit:read','cu.home_branch_id','cl.user_id')
            parts=[scope];bind=list(values)
            for key,col in [('decision','cl.decision'),('actor','cl.user_id')]:
                if request.args.get(key):parts.append(col+'=%s');bind.append(request.args[key])
            for key,op in [('from','>='),('to','<=')]:
                if request.args.get(key):parts.append('cl.created_at'+op+'%s');bind.append(request.args[key])
            cur.execute('SELECT cl.* FROM chatbot_audit_log cl LEFT JOIN users cu ON cu.id=cl.user_id WHERE '+' AND '.join(parts)+' ORDER BY cl.id DESC LIMIT 100',tuple(bind));chat=cur.fetchall()
        return jsonify(rows=rbac,chatbot=chat)

    for plural,kind,permission in [('users','user','user:manage'),('roles','role','rbac:manage'),('permissions','permission','rbac:manage')]:
        def save(target_id=None,entity=kind):
            payload=request.get_json(silent=True)
            if not isinstance(payload,dict):return jsonify(error='invalid-body'),400
            try:target=mutate(entity,target_id,payload,'delete' if request.method=='DELETE' else 'save')
            except (IntegrityError,TypeError,KeyError,ValueError) as error:
                from customer_service import CustomerError
                if isinstance(error,(AdminRejected,CustomerError)):raise
                return jsonify(error='invalid-change',message='Dữ liệu trùng hoặc không hợp lệ.'),400
            return jsonify(id=target)
        if kind!='permission':app.add_url_rule('/api/admin/'+plural,endpoint='create_'+plural,view_func=require_permission(permission)(save),methods=['POST'])
        app.add_url_rule('/api/admin/'+plural+'/<int:target_id>',endpoint='update_'+plural,view_func=require_permission(permission)(save),methods=['PUT']+(['DELETE'] if kind=='role' else []))

    @app.route('/api/admin/users/<int:target_id>/roles',methods=['POST','DELETE'])
    @require_permission('user:manage')
    def assign_roles(target_id):
        payload=request.get_json(silent=True)
        if not isinstance(payload,dict):return jsonify(error='invalid-body'),400
        try:mutate('assignment',target_id,payload,'delete' if request.method=='DELETE' else 'save')
        except (IntegrityError,TypeError,KeyError) :return jsonify(error='invalid-change'),400
        return jsonify(id=target_id)
