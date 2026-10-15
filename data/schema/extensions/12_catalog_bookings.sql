USE honda_chatbot;
CREATE TABLE IF NOT EXISTS vehicle_releases (
 variant_id INT PRIMARY KEY,
 model_year SMALLINT NULL COMMENT 'Năm đời xe; NULL khi chưa xác định',
 lifecycle ENUM('current','previous','discontinued') NOT NULL DEFAULT 'current',
 version INT NOT NULL DEFAULT 1,
 updated_by INT NULL,
 updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY(variant_id) REFERENCES product_variants(id),
 FOREIGN KEY(updated_by) REFERENCES users(id)
) COMMENT='Thông tin bổ sung về đời xe; không thay đổi schema sản phẩm chuẩn';
CREATE TABLE IF NOT EXISTS service_bookings (
 id INT AUTO_INCREMENT PRIMARY KEY,
 branch_id INT NOT NULL, customer_id INT NOT NULL, created_by INT NOT NULL,
 scheduled_at DATETIME NOT NULL COMMENT 'Giờ hẹn địa phương Việt Nam',
 service_type ENUM('maintenance','repair','inspection') NOT NULL,
 vehicle_description VARCHAR(200) NOT NULL, license_plate VARCHAR(20) NULL,
 notes VARCHAR(1000) NULL,
 status ENUM('scheduled','confirmed','completed','cancelled') NOT NULL DEFAULT 'scheduled',
 version INT NOT NULL DEFAULT 1,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 INDEX ix_service_branch_date(branch_id,scheduled_at,status),
 INDEX ix_service_customer(customer_id),
 FOREIGN KEY(branch_id) REFERENCES branches(id), FOREIGN KEY(customer_id) REFERENCES users(id),
 FOREIGN KEY(created_by) REFERENCES users(id)
) COMMENT='Lịch sửa chữa và bảo dưỡng; giờ Asia/Ho_Chi_Minh';
INSERT IGNORE INTO permissions(code,description) VALUES
 ('product:manage','Quản lý mẫu xe, phiên bản, năm đời và giá niêm yết'),
 ('booking:read','Xem lịch sửa chữa trong phạm vi được cấp'),
 ('booking:create','Đặt lịch sửa chữa trong phạm vi được cấp'),
 ('booking:manage','Xác nhận và hoàn tất lịch sửa chữa');
INSERT IGNORE INTO role_permissions(role_id,permission_id,data_scope)
 SELECT r.id,p.id,CASE WHEN r.name='customer' THEN 'own' WHEN r.name IN ('branch_manager','sales_staff','technician') THEN 'branch' ELSE 'all' END
 FROM roles r JOIN permissions p ON
 (p.code IN ('booking:read','booking:create') AND r.name IN ('super_admin','branch_manager','sales_staff','technician','customer')) OR
 (p.code='booking:manage' AND r.name IN ('super_admin','branch_manager','technician')) OR
 (p.code='product:manage' AND r.name='super_admin');
INSERT INTO nav_items(code,label,path,required_permission_id,sort_order,is_enabled)
 SELECT 'bookings','Lịch sửa chữa','/bookings',id,70,TRUE FROM permissions WHERE code='booking:read'
 ON DUPLICATE KEY UPDATE label=VALUES(label),path=VALUES(path),required_permission_id=VALUES(required_permission_id),is_enabled=TRUE;
INSERT INTO nav_items(code,label,path,required_permission_id,sort_order,is_enabled)
 SELECT 'catalog','Danh mục xe','/catalog',id,45,TRUE FROM permissions WHERE code='product:manage'
 ON DUPLICATE KEY UPDATE label=VALUES(label),path=VALUES(path),required_permission_id=VALUES(required_permission_id),is_enabled=TRUE;
