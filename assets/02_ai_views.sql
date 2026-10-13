-- =====================================================================
-- 02_ai_views.sql - Lớp view "thân thiện với AI" cho chatbot Honda
-- Chạy lại nhiều lần được (idempotent). Không sửa honda_chatbot_rbac.sql.
-- Lưu ý: MySQL/MariaDB KHÔNG hỗ trợ COMMENT cho VIEW hay cột của view, nên mô tả
-- tiếng Việt được lưu trong bảng ai_data_dictionary (bên dưới).
-- =====================================================================
USE honda_chatbot;

-- Phạm vi chi nhánh theo phiên: backend chạy  SET @ai_branch = <branch_id hoặc NULL>
-- trước MỖI truy vấn (NULL = toàn hệ thống). View không dùng được biến người dùng
-- trực tiếp (lỗi 1351), nên đi qua hàm này.
DROP FUNCTION IF EXISTS fn_session_branch;
CREATE FUNCTION fn_session_branch() RETURNS INT
  NOT DETERMINISTIC NO SQL
  RETURN @ai_branch;

CREATE OR REPLACE VIEW v_ai_products AS
SELECT pv.id AS variant_id,
       CONCAT('SP', LPAD(pv.id, 3, '0')) AS sku,
       p.model_name, pv.variant_name, p.segment, p.engine_cc,
       p.fuel_consumption_l100km, pv.list_price,
       COALESCE((SELECT SUM(i.quantity) FROM inventory i WHERE i.variant_id = pv.id), 0) AS total_stock
FROM product_variants pv
JOIN products p ON p.id = pv.product_id;

CREATE OR REPLACE VIEW v_ai_inventory AS
SELECT b.id AS branch_id, b.code AS branch_code, b.name AS branch_name,
       CONCAT('SP', LPAD(pv.id, 3, '0')) AS sku,
       p.model_name, pv.variant_name, i.quantity
FROM inventory i
JOIN branches b          ON b.id = i.branch_id
JOIN product_variants pv ON pv.id = i.variant_id
JOIN products p          ON p.id = pv.product_id
WHERE fn_session_branch() IS NULL OR i.branch_id = fn_session_branch();

CREATE OR REPLACE VIEW v_ai_customers AS
SELECT cp.customer_code, u.full_name, u.phone, u.email, cp.gender, cp.birth_date,
       cp.province, cp.district, cp.occupation, cp.lead_source,
       p.model_name AS interested_model, cp.payment_preference,
       cp.registered_at, cp.status,
       u.home_branch_id AS branch_id, b.code AS branch_code
FROM users u
JOIN customer_profiles cp ON cp.user_id = u.id
LEFT JOIN products p      ON p.id = cp.interested_product_id
LEFT JOIN branches b      ON b.id = u.home_branch_id
WHERE u.user_type = 'customer'
  AND (fn_session_branch() IS NULL OR u.home_branch_id = fn_session_branch());

CREATE OR REPLACE VIEW v_ai_orders AS
SELECT o.id AS order_id, o.branch_id, b.code AS branch_code,
       cp.customer_code, u.full_name AS customer_name,
       p.model_name, pv.variant_name, oi.quantity, oi.unit_price,
       o.discount_amount, (oi.quantity * oi.unit_price - o.discount_amount) AS net_amount,
       o.status, o.created_at
FROM orders o
JOIN order_items oi       ON oi.order_id = o.id
JOIN product_variants pv  ON pv.id = oi.variant_id
JOIN products p           ON p.id = pv.product_id
JOIN branches b           ON b.id = o.branch_id
JOIN users u              ON u.id = o.customer_id
LEFT JOIN customer_profiles cp ON cp.user_id = u.id
WHERE fn_session_branch() IS NULL OR o.branch_id = fn_session_branch();

-- Giá vốn: chỉ cho role có price:cost:read (kiểm tra ở backend + registry bên dưới)
CREATE OR REPLACE VIEW v_ai_product_costs AS
SELECT CONCAT('SP', LPAD(pv.id, 3, '0')) AS sku, p.model_name, pv.variant_name,
       pv.list_price, pv.cost_price, (pv.list_price - pv.cost_price) AS gross_margin
FROM product_variants pv
JOIN products p ON p.id = pv.product_id;

-- ---------------------------------------------------------------------
-- Registry: view nào cần permission nào. Whitelist của validator được TÍNH ĐỘNG
-- từ bảng này + v_user_permissions của từng user (đây là phần "RBAC động").
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_view_registry (
  view_name VARCHAR(64) PRIMARY KEY,
  required_permission_id INT NOT NULL,
  description_vi VARCHAR(255) NOT NULL,
  FOREIGN KEY (required_permission_id) REFERENCES permissions(id)
);

CREATE TABLE IF NOT EXISTS ai_data_dictionary (
  view_name VARCHAR(64) NOT NULL,
  column_name VARCHAR(64) NOT NULL,
  description_vi VARCHAR(255) NOT NULL,
  PRIMARY KEY (view_name, column_name)
);

DELETE FROM ai_data_dictionary;
DELETE FROM ai_view_registry;

INSERT INTO ai_view_registry (view_name, required_permission_id, description_vi)
SELECT v.view_name, p.id, v.descr FROM (
  SELECT 'v_ai_products' AS view_name, 'kb:public:read' AS code, 'Danh mục xe và giá niêm yết, tồn kho toàn hệ thống (công khai)' AS descr
  UNION ALL SELECT 'v_ai_inventory',     'inventory:read',  'Tồn kho theo từng chi nhánh'
  UNION ALL SELECT 'v_ai_customers',     'customer:read',   'Thông tin khách hàng (có dữ liệu cá nhân)'
  UNION ALL SELECT 'v_ai_orders',        'order:read',      'Đơn hàng kèm khách, xe, chi nhánh'
  UNION ALL SELECT 'v_ai_product_costs', 'price:cost:read', 'Giá vốn và lợi nhuận gộp (nhạy cảm)'
) v JOIN permissions p ON p.code = v.code;

INSERT INTO ai_data_dictionary (view_name, column_name, description_vi) VALUES
('v_ai_products','sku','Mã phiên bản xe, dạng SP001 đến SP028'),
('v_ai_products','model_name','Tên mẫu xe, ví dụ SH 160i, Vision 110'),
('v_ai_products','variant_name','Tên đầy đủ: mẫu - phiên bản - màu'),
('v_ai_products','segment','Phân khúc: xe_so (xe số), tay_ga (xe ga), con_tay (xe côn tay)'),
('v_ai_products','engine_cc','Dung tích xi-lanh (cc)'),
('v_ai_products','fuel_consumption_l100km','Mức tiêu hao nhiên liệu (lít/100km)'),
('v_ai_products','list_price','Giá niêm yết (VNĐ)'),
('v_ai_products','total_stock','Tổng tồn kho toàn hệ thống (chiếc)'),
('v_ai_inventory','branch_code','Mã chi nhánh: NT01, NT02 (Nha Trang), CR01 (Cam Ranh)'),
('v_ai_inventory','quantity','Số xe còn trong kho của chi nhánh'),
('v_ai_customers','customer_code','Mã khách hàng, dạng KH0001'),
('v_ai_customers','status','Trạng thái: Tiềm năng, Đang tư vấn, Đã mua, Ngừng liên hệ'),
('v_ai_customers','payment_preference','Hình thức thanh toán dự kiến: Trả thẳng hoặc Trả góp'),
('v_ai_customers','lead_source','Nguồn khách: Website, Zalo, Facebook, Trực tiếp tại cửa hàng, Giới thiệu, Hotline'),
('v_ai_orders','order_id','Mã đơn hàng'),
('v_ai_orders','unit_price','Đơn giá (VNĐ)'),
('v_ai_orders','discount_amount','Số tiền giảm giá của cả đơn (VNĐ)'),
('v_ai_orders','net_amount','Thành tiền sau giảm giá (VNĐ)'),
('v_ai_orders','status','Trạng thái đơn: pending, approved, paid, delivered, cancelled'),
('v_ai_product_costs','cost_price','Giá vốn (VNĐ), NHẠY CẢM'),
('v_ai_product_costs','gross_margin','Lợi nhuận gộp = giá niêm yết - giá vốn (VNĐ)');
