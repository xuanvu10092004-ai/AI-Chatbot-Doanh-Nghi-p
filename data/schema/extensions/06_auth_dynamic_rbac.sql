USE honda_chatbot;
ALTER TABLE users ADD last_login_at DATETIME NULL,
 ADD failed_login_count INT NOT NULL DEFAULT 0, ADD locked_until DATETIME NULL,
 ADD must_change_password BOOLEAN NOT NULL DEFAULT FALSE, ADD password_updated_at DATETIME NULL;
ALTER TABLE roles ADD is_system BOOLEAN NOT NULL DEFAULT FALSE,
 ADD is_active BOOLEAN NOT NULL DEFAULT TRUE,
 ADD landing_path VARCHAR(100) NOT NULL DEFAULT '/dashboard', ADD priority INT NOT NULL DEFAULT 100;
ALTER TABLE role_permissions ADD data_scope ENUM('all','branch','own') NOT NULL DEFAULT 'all';
ALTER TABLE user_roles ADD expires_at DATETIME NULL;
UPDATE roles SET is_system=TRUE WHERE name IN ('super_admin','branch_manager','sales_staff','technician','accountant','marketing','customer','guest');
UPDATE roles SET landing_path='/chat' WHERE name IN ('customer','guest');
UPDATE roles SET priority=id*10;
UPDATE role_permissions rp JOIN roles r ON r.id=rp.role_id
SET rp.data_scope=CASE WHEN r.name IN ('sales_staff','technician','branch_manager') THEN 'branch' WHEN r.name='customer' THEN 'own' ELSE 'all' END;
CREATE TABLE rbac_audit_log (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, actor_user_id INT NULL, action VARCHAR(80) NOT NULL,
 target_type VARCHAR(40) NOT NULL, target_id INT NULL, before_json JSON NULL, after_json JSON NULL,
 ip_address VARCHAR(45) NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX ix_rbac_audit_created(created_at), FOREIGN KEY(actor_user_id) REFERENCES users(id)
);
CREATE TABLE rbac_meta(id TINYINT PRIMARY KEY, version INT NOT NULL);
INSERT INTO rbac_meta VALUES(1,1);
INSERT INTO permissions(code,description) VALUES
 ('dashboard:view','Voir dashboard / Xem tổng quan'),('dashboard:finance','Xem tài chính trên dashboard'),('rbac:manage','Quản trị vai trò và quyền');
INSERT INTO role_permissions(role_id,permission_id,data_scope)
SELECT r.id,p.id,CASE WHEN r.name IN ('branch_manager','sales_staff','technician') THEN 'branch' ELSE 'all' END
FROM roles r JOIN permissions p ON p.code='dashboard:view'
WHERE r.name IN ('super_admin','branch_manager','sales_staff','technician','accountant','marketing');
INSERT INTO role_permissions(role_id,permission_id,data_scope)
SELECT r.id,p.id,'all' FROM roles r JOIN permissions p ON p.code='dashboard:finance' WHERE r.name IN ('super_admin','accountant');
INSERT INTO role_permissions(role_id,permission_id,data_scope)
SELECT r.id,p.id,'all' FROM roles r JOIN permissions p ON p.code='rbac:manage' WHERE r.name='super_admin';
CREATE OR REPLACE VIEW v_user_permissions AS
SELECT u.id AS user_id,r.name AS role_name,p.code AS permission_code,
 CASE WHEN r.name='super_admin' OR rp.data_scope='all' THEN NULL
      WHEN rp.data_scope='branch' THEN COALESCE(ur.scope_branch_id,u.home_branch_id) ELSE NULL END AS scope_branch_id,
 CASE WHEN r.name='super_admin' THEN 'all' ELSE rp.data_scope END AS data_scope
FROM users u JOIN user_roles ur ON ur.user_id=u.id JOIN roles r ON r.id=ur.role_id
JOIN permissions p ON r.name='super_admin' OR EXISTS (SELECT 1 FROM role_permissions rp2 WHERE rp2.role_id=r.id AND rp2.permission_id=p.id)
LEFT JOIN role_permissions rp ON rp.role_id=r.id AND rp.permission_id=p.id
WHERE u.is_active=TRUE AND r.is_active=TRUE AND (ur.expires_at IS NULL OR ur.expires_at>NOW());
CREATE OR REPLACE VIEW v_user_kb_access AS
SELECT DISTINCT vp.user_id,d.id AS doc_id,d.title,c.code AS category
FROM v_user_permissions vp JOIN permissions p ON p.code=vp.permission_code
JOIN kb_categories c ON c.required_permission_id=p.id JOIN kb_documents d ON d.category_id=c.id
WHERE d.branch_id IS NULL OR vp.data_scope='all' OR (vp.data_scope='branch' AND d.branch_id=vp.scope_branch_id);
CREATE TABLE nav_items (
 code VARCHAR(50) PRIMARY KEY,label VARCHAR(100) NOT NULL,path VARCHAR(100) NOT NULL,
 required_permission_id INT NULL,sort_order INT NOT NULL DEFAULT 100,is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
 FOREIGN KEY(required_permission_id) REFERENCES permissions(id)
);
INSERT INTO nav_items(code,label,path,required_permission_id,sort_order,is_enabled)
SELECT v.code,v.label,v.path,p.id,v.ord,v.enabled FROM (
 SELECT 'dashboard' code,'Tổng quan' label,'/dashboard' path,'dashboard:view' perm,10 ord,1 enabled
 UNION ALL SELECT 'chat','Trợ lý AI','/chat','kb:public:read',20,1
 UNION ALL SELECT 'customers','Khách hàng','/customers','customer:read',30,1
 UNION ALL SELECT 'inventory','Tồn kho','/inventory','inventory:read',40,1
 UNION ALL SELECT 'revenue','Doanh thu','/dashboard#revenue','order:read',50,1
 UNION ALL SELECT 'quotes','Báo giá','/quotes','order:read',60,0
 UNION ALL SELECT 'opportunities','Cơ hội','/opportunities','order:read',70,0
 UNION ALL SELECT 'bookings','Đặt lịch','/bookings','kb:public:read',80,0
 UNION ALL SELECT 'users','Tài khoản','/admin/users','user:manage',100,1
 UNION ALL SELECT 'roles','Vai trò','/admin/roles','rbac:manage',110,1
 UNION ALL SELECT 'permissions','Quyền','/admin/permissions','rbac:manage',120,1
 UNION ALL SELECT 'audit','Nhật ký','/admin/audit','audit:read',130,1
) v JOIN permissions p ON p.code=v.perm;
