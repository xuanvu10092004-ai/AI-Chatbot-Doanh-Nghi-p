USE honda_chatbot;
CREATE TABLE IF NOT EXISTS customer_input_batches (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, created_by INT NOT NULL,
 document_id BIGINT NULL, chat_session_id INT NULL,
 status ENUM('draft','committed','cancelled') NOT NULL DEFAULT 'draft',
 rows_json JSON NOT NULL, preview_json JSON NULL, result_json JSON NULL,
 version INT NOT NULL DEFAULT 1, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY(created_by) REFERENCES users(id), FOREIGN KEY(document_id) REFERENCES document_uploads(id),
 FOREIGN KEY(chat_session_id) REFERENCES chat_sessions(id), INDEX ix_customer_batch_owner(created_by,status)
);
INSERT INTO permissions(code,description)
SELECT s.code,s.description FROM (
 SELECT 'customer:write' code,'Thêm/cập nhật hồ sơ khách hàng qua bản nháp được xác nhận' description
 UNION ALL SELECT 'order:write','Tạo đơn chờ duyệt từ thông tin mua của khách hàng'
) s WHERE NOT EXISTS (SELECT 1 FROM permissions p WHERE p.code=s.code);
INSERT INTO role_permissions(role_id,permission_id,data_scope)
SELECT r.id,p.id,CASE WHEN r.name='super_admin' THEN 'all' ELSE 'branch' END
FROM roles r JOIN permissions p ON p.code IN ('customer:write','order:write','document:manage')
WHERE r.name IN ('super_admin','branch_manager','sales_staff')
 AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.role_id=r.id AND rp.permission_id=p.id);
INSERT INTO kb_categories(code,name,required_permission_id)
SELECT 'customers','Thông tin / Danh sách khách hàng',p.id FROM permissions p
WHERE p.code='customer:read' AND NOT EXISTS (SELECT 1 FROM kb_categories WHERE code='customers');
INSERT INTO chatbot_intents(code,description,required_permission_id,data_source)
SELECT 'add_customer','Thêm/cập nhật khách hàng qua công cụ được xác nhận',p.id,'customer_input'
FROM permissions p WHERE p.code='customer:write'
 AND NOT EXISTS (SELECT 1 FROM chatbot_intents WHERE code='add_customer');
