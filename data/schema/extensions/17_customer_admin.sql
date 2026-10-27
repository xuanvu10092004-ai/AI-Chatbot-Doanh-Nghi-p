USE honda_chatbot;
CREATE TABLE IF NOT EXISTS customer_admin_state (
 customer_id INT PRIMARY KEY,
 version BIGINT NOT NULL DEFAULT 1,
 deleted_at DATETIME NULL,
 deleted_by INT NULL,
 restored_at DATETIME NULL,
 updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Version và xóa mềm khách hàng; giữ nguyên đơn hàng và lịch sử';
INSERT IGNORE INTO customer_admin_state(customer_id) SELECT user_id FROM customer_profiles;
INSERT IGNORE INTO permissions(code,description) VALUES('customer:admin:manage','Chỉ super_admin toàn hệ thống được sửa, xóa mềm và khôi phục khách');
DELETE rp FROM role_permissions rp JOIN permissions p ON p.id=rp.permission_id JOIN roles r ON r.id=rp.role_id
 WHERE p.code='customer:admin:manage' AND r.name<>'super_admin';
INSERT INTO role_permissions(role_id,permission_id,data_scope)
 SELECT r.id,p.id,'all' FROM roles r JOIN permissions p ON p.code='customer:admin:manage' WHERE r.name='super_admin'
 ON DUPLICATE KEY UPDATE data_scope='all';
CREATE OR REPLACE VIEW v_active_customer_profiles AS
 SELECT cp.* FROM customer_profiles cp JOIN users u ON u.id=cp.user_id
 LEFT JOIN customer_admin_state s ON s.customer_id=cp.user_id
 WHERE u.user_type='customer' AND s.deleted_at IS NULL;
CREATE OR REPLACE VIEW v_ai_customers AS
 SELECT u.id AS customer_id,u.email,u.full_name,u.phone,u.user_type,u.home_branch_id,u.home_branch_id AS branch_id,
 b.code AS home_branch_code,b.name AS home_branch_name,cp.customer_code,cp.gender,cp.birth_date,cp.province,cp.district,cp.address,cp.occupation,cp.lead_source,cp.interested_product_id,cp.payment_preference,cp.registered_at,cp.status AS customer_status
 FROM users u JOIN v_active_customer_profiles cp ON cp.user_id=u.id LEFT JOIN branches b ON b.id=u.home_branch_id
 WHERE (fn_session_branch() IS NULL OR u.home_branch_id=fn_session_branch())
 AND (fn_session_user() IS NULL OR u.id=fn_session_user());
INSERT IGNORE INTO chatbot_intents(code,description,required_permission_id,data_source)
 SELECT CONCAT('tool_',v.code),v.description,p.id,'controlled_tool' FROM (
 SELECT 'customer_update' code,'Sửa khách hàng' description UNION ALL SELECT 'customer_delete','Xóa mềm khách hàng'
 UNION ALL SELECT 'customer_restore','Khôi phục khách hàng') v JOIN permissions p ON p.code='customer:admin:manage';
