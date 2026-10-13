USE honda_chatbot;
CREATE OR REPLACE FUNCTION fn_session_branch() RETURNS INT
NOT DETERMINISTIC NO SQL RETURN @ai_branch;

-- Các view v_ai_* là bề mặt dữ liệu dành cho AI. Không view nào phát lộ cost_price,
-- ngoại trừ v_ai_product_costs, vốn chỉ được cấp quyền riêng.
-- segment nhận một trong các giá trị: xe_so, tay_ga, con_tay.
-- Các cột *_price và *_amount là số nguyên đơn vị VNĐ.

CREATE OR REPLACE VIEW v_ai_products AS
SELECT
    p.id AS product_id,
    p.model_name,
    pv.id AS variant_id,
    pv.variant_name,
    SUBSTRING_INDEX(pv.variant_name, ' - ', -1) AS color,
    p.segment,
    p.engine_cc,
    pv.list_price,
    COALESCE(SUM(i.quantity), 0) AS total_stock
FROM products p
JOIN product_variants pv ON pv.product_id = p.id
LEFT JOIN inventory i ON i.variant_id = pv.id
GROUP BY
    p.id, p.model_name, pv.id, pv.variant_name,
    p.segment, p.engine_cc, pv.list_price;

-- v_ai_products: một dòng cho mỗi phiên bản/màu; total_stock là tổng tồn toàn hệ thống.
-- Không bao gồm product_variants.cost_price.

CREATE OR REPLACE VIEW v_ai_inventory AS
SELECT
    i.branch_id,
    b.code AS branch_code,
    b.name AS branch_name,
    b.city AS branch_city,
    p.id AS product_id,
    p.model_name,
    pv.id AS variant_id,
    pv.variant_name,
    SUBSTRING_INDEX(pv.variant_name, ' - ', -1) AS color,
    p.segment,
    p.engine_cc,
    pv.list_price,
    i.quantity,
    i.updated_at
FROM inventory i
JOIN branches b ON b.id = i.branch_id
JOIN product_variants pv ON pv.id = i.variant_id
JOIN products p ON p.id = pv.product_id
WHERE fn_session_branch() IS NULL OR i.branch_id = fn_session_branch();

-- v_ai_inventory: tồn kho theo chi nhánh; quantity là số xe hiện có.
-- branch_code hiện có: NT01, NT02, CR01.

CREATE OR REPLACE VIEW v_ai_customers AS
SELECT
    u.id AS customer_id,
    u.email,
    u.full_name,
    u.phone,
    u.user_type,
    u.home_branch_id,
    u.home_branch_id AS branch_id,
    b.code AS home_branch_code,
    b.name AS home_branch_name,
    cp.customer_code,
    cp.gender,
    cp.birth_date,
    cp.province,
    cp.district,
    cp.address,
    cp.occupation,
    cp.lead_source,
    cp.interested_product_id,
    cp.payment_preference,
    cp.registered_at,
    cp.status AS customer_status
FROM users u
LEFT JOIN branches b ON b.id = u.home_branch_id
JOIN customer_profiles cp ON cp.user_id = u.id
WHERE u.user_type = 'customer'
  AND (fn_session_branch() IS NULL OR u.home_branch_id = fn_session_branch());

-- v_ai_customers: thông tin khách hàng và hồ sơ; tuyệt đối không có password_hash.
-- customer_status có thể là: Tiềm năng, Đang tư vấn, Đã mua, Ngừng liên hệ.

CREATE OR REPLACE VIEW v_ai_orders AS
SELECT
    o.id AS order_id,
    o.customer_id,
    customer.full_name AS customer_name,
    o.branch_id,
    b.code AS branch_code,
    b.name AS branch_name,
    oi.variant_id,
    p.id AS product_id,
    p.model_name,
    pv.variant_name,
    SUBSTRING_INDEX(pv.variant_name, ' - ', -1) AS color,
    oi.quantity,
    oi.unit_price,
    oi.quantity * oi.unit_price AS line_amount,
    o.discount_amount,
    (oi.quantity * oi.unit_price - o.discount_amount) AS net_amount,
    o.status,
    o.created_at
FROM orders o
JOIN users customer ON customer.id = o.customer_id
JOIN branches b ON b.id = o.branch_id
JOIN order_items oi ON oi.order_id = o.id
JOIN product_variants pv ON pv.id = oi.variant_id
JOIN products p ON p.id = pv.product_id
WHERE fn_session_branch() IS NULL OR o.branch_id = fn_session_branch();

-- v_ai_orders: đơn hàng kèm tên khách, mẫu xe, phiên bản và chi nhánh.
-- line_amount/unit_price/discount_amount là số nguyên đơn vị VNĐ.

CREATE OR REPLACE VIEW v_ai_product_costs AS
SELECT
    p.id AS product_id,
    p.model_name,
    pv.id AS variant_id,
    pv.variant_name,
    SUBSTRING_INDEX(pv.variant_name, ' - ', -1) AS color,
    p.segment,
    p.engine_cc,
    pv.list_price,
    pv.cost_price,
    pv.list_price - pv.cost_price AS gross_margin
FROM products p
JOIN product_variants pv ON pv.product_id = p.id;

-- v_ai_product_costs: dữ liệu nhạy cảm; cost_price/gross_margin là VNĐ.
-- Backend chỉ truy cập view này sau khi kiểm tra permission price:cost:read.

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



INSERT INTO ai_view_registry (view_name, required_permission_id, description_vi)
SELECT v.view_name, p.id, v.descr FROM (
  SELECT 'v_ai_products' AS view_name, 'kb:public:read' AS code, 'Danh mục xe và giá niêm yết, tồn kho toàn hệ thống (công khai)' AS descr
  UNION ALL SELECT 'v_ai_inventory',     'inventory:read',  'Tồn kho theo từng chi nhánh'
  UNION ALL SELECT 'v_ai_customers',     'customer:read',   'Thông tin khách hàng (có dữ liệu cá nhân)'
  UNION ALL SELECT 'v_ai_orders',        'order:read',      'Đơn hàng kèm khách, xe, chi nhánh'
  UNION ALL SELECT 'v_ai_product_costs', 'price:cost:read', 'Giá vốn và lợi nhuận gộp (nhạy cảm)'
) v JOIN permissions p ON p.code = v.code
ON DUPLICATE KEY UPDATE required_permission_id = VALUES(required_permission_id), description_vi = VALUES(description_vi);

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
('v_ai_customers','customer_status','Trạng thái: Tiềm năng, Đang tư vấn, Đã mua, Ngừng liên hệ'),
('v_ai_customers','payment_preference','Hình thức thanh toán dự kiến: Trả thẳng hoặc Trả góp'),
('v_ai_customers','lead_source','Nguồn khách: Website, Zalo, Facebook, Trực tiếp tại cửa hàng, Giới thiệu, Hotline'),
('v_ai_orders','order_id','Mã đơn hàng'),
('v_ai_orders','unit_price','Đơn giá (VNĐ)'),
('v_ai_orders','discount_amount','Số tiền giảm giá của cả đơn (VNĐ)'),
('v_ai_orders','net_amount','Thành tiền sau giảm giá (VNĐ)'),
('v_ai_orders','status','Trạng thái đơn: pending, approved, paid, delivered, cancelled'),
('v_ai_product_costs','cost_price','Giá vốn (VNĐ), NHẠY CẢM'),
('v_ai_product_costs','gross_margin','Lợi nhuận gộp = giá niêm yết - giá vốn (VNĐ)')
ON DUPLICATE KEY UPDATE description_vi = VALUES(description_vi);
