USE honda_chatbot;
CREATE TABLE IF NOT EXISTS stock_receipts (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,branch_id INT NOT NULL,created_by INT NOT NULL,
 supplier VARCHAR(200) NOT NULL,reference_code VARCHAR(100) NOT NULL,notes VARCHAR(1000) NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY uq_stock_reference(branch_id,reference_code),
 FOREIGN KEY(branch_id) REFERENCES branches(id),FOREIGN KEY(created_by) REFERENCES users(id)
) COMMENT='Phiếu nhập hàng đã ghi sổ; mã chứng từ duy nhất trong chi nhánh';
CREATE TABLE IF NOT EXISTS stock_receipt_items (
 receipt_id BIGINT NOT NULL,variant_id INT NOT NULL,quantity INT NOT NULL,
 PRIMARY KEY(receipt_id,variant_id),CHECK(quantity>0),
 FOREIGN KEY(receipt_id) REFERENCES stock_receipts(id),FOREIGN KEY(variant_id) REFERENCES product_variants(id)
);
CREATE TABLE IF NOT EXISTS appointment_requests (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,session_id INT NOT NULL,customer_id INT NULL,branch_id INT NOT NULL,
 kind ENUM('maintenance','consultation') NOT NULL,full_name VARCHAR(150) NOT NULL,
 phone VARCHAR(20) NOT NULL,email VARCHAR(255) NULL,scheduled_at DATETIME NOT NULL,
 notes VARCHAR(1000) NULL,status ENUM('scheduled','confirmed','completed','cancelled') NOT NULL DEFAULT 'scheduled',
 version INT NOT NULL DEFAULT 1,created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX ix_appointment_branch_date(branch_id,scheduled_at),
 FOREIGN KEY(session_id) REFERENCES chat_sessions(id),FOREIGN KEY(customer_id) REFERENCES users(id),
 FOREIGN KEY(branch_id) REFERENCES branches(id)
) COMMENT='Lịch bảo dưỡng và tư vấn từ chat; khách vãng lai gắn với phiên chat';
CREATE TABLE IF NOT EXISTS chat_action_drafts (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,session_id INT NOT NULL,user_id INT NULL,
 tool_name VARCHAR(60) NOT NULL,arguments_json JSON NOT NULL,
 status ENUM('draft','committed','cancelled') NOT NULL DEFAULT 'draft',result_json JSON NULL,
 version INT NOT NULL DEFAULT 1,created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(session_id) REFERENCES chat_sessions(id),FOREIGN KEY(user_id) REFERENCES users(id),
 INDEX ix_action_session(session_id,status)
) COMMENT='Lệnh công cụ đã xem trước; xác nhận có khóa, quyền được đọc lại khi thực thi';
CREATE TABLE IF NOT EXISTS customer_import_sources (
 batch_id BIGINT PRIMARY KEY,document_version INT NOT NULL,warnings_json JSON NOT NULL,
 FOREIGN KEY(batch_id) REFERENCES customer_input_batches(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS customer_import_rows (
 batch_id BIGINT NOT NULL,customer_id INT NOT NULL,row_number INT NOT NULL,action VARCHAR(20) NOT NULL,
 PRIMARY KEY(batch_id,row_number),INDEX ix_import_customer(customer_id),
 FOREIGN KEY(batch_id) REFERENCES customer_input_batches(id) ON DELETE CASCADE,
 FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE
);
INSERT IGNORE INTO permissions(code,description) VALUES
 ('inventory:receive','Nhập hàng và ghi tăng tồn kho trong phạm vi được cấp');
INSERT IGNORE INTO role_permissions(role_id,permission_id,data_scope)
 SELECT r.id,p.id,CASE WHEN r.name='super_admin' THEN 'all' ELSE 'branch' END
 FROM roles r JOIN permissions p ON p.code='inventory:receive' WHERE r.name IN ('super_admin','branch_manager');
INSERT INTO nav_items(code,label,path,required_permission_id,sort_order,is_enabled)
 SELECT 'stock-receipts','Nhập hàng','/stock-receipts',id,42,TRUE FROM permissions WHERE code='inventory:receive'
 ON DUPLICATE KEY UPDATE required_permission_id=VALUES(required_permission_id),is_enabled=TRUE;
INSERT IGNORE INTO chatbot_intents(code,description,required_permission_id,data_source)
 SELECT CONCAT('tool_',v.name),v.description,p.id,'controlled_tool' FROM (
 SELECT 'stock_receive' name,'Nhập hàng' description,'inventory:receive' perm
 UNION ALL SELECT 'stock_list','Lịch sử nhập hàng','inventory:receive'
 UNION ALL SELECT 'catalog_save','Thêm/sửa xe và giá','product:manage'
 UNION ALL SELECT 'catalog_list','Danh mục xe','product:manage'
 UNION ALL SELECT 'booking_create','Đặt lịch sửa xe','booking:create'
 UNION ALL SELECT 'booking_update','Cập nhật lịch sửa xe','booking:read'
 UNION ALL SELECT 'booking_list','Xem lịch sửa xe','booking:read'
 UNION ALL SELECT 'appointment_create','Đặt lịch bảo dưỡng/tư vấn','kb:public:read'
 UNION ALL SELECT 'appointment_list','Xem lịch tư vấn/bảo dưỡng','booking:read'
 UNION ALL SELECT 'appointment_update','Cập nhật lịch tư vấn/bảo dưỡng','booking:read'
 UNION ALL SELECT 'dashboard_read','Số liệu tổng quan','dashboard:view'
 UNION ALL SELECT 'users_list','Danh sách tài khoản','user:manage'
 UNION ALL SELECT 'user_save','Thêm/sửa tài khoản','user:manage'
 UNION ALL SELECT 'user_password','Đặt lại mật khẩu qua ô bảo mật','user:manage'
 UNION ALL SELECT 'role_save','Thêm/sửa vai trò','rbac:manage'
 UNION ALL SELECT 'role_delete','Xóa vai trò','rbac:manage'
 UNION ALL SELECT 'roles_list','Danh sách vai trò','rbac:manage'
 UNION ALL SELECT 'permissions_list','Danh mục quyền','rbac:manage'
 UNION ALL SELECT 'permission_save','Sửa mô tả quyền','rbac:manage'
 UNION ALL SELECT 'assignment_save','Gán vai trò','user:manage'
 UNION ALL SELECT 'assignment_delete','Gỡ vai trò','user:manage'
 UNION ALL SELECT 'audit_list','Nhật ký','audit:read'
 UNION ALL SELECT 'documents_list','Danh sách tài liệu','document:manage'
 UNION ALL SELECT 'document_review','Hiệu đính tài liệu','document:manage'
 UNION ALL SELECT 'document_publish','Xuất bản tài liệu','document:manage'
 UNION ALL SELECT 'orders_list','Danh sách đơn','order:read'
 UNION ALL SELECT 'invoice_export','Xuất chứng từ','invoice:export'
 ) v JOIN permissions p ON p.code=v.perm;
