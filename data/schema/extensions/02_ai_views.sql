USE honda_chatbot;

-- Các view v_ai_* là bề mặt dữ liệu dành cho AI. Không view nào phát lộ cost_price,
-- ngoại trừ v_ai_product_costs, vốn chỉ được cấp quyền riêng.
-- segment nhận một trong các giá trị: xe_so, tay_ga, con_tay.
-- Các cột *_price và *_amount là số nguyên đơn vị VNĐ.

DROP VIEW IF EXISTS v_ai_products;
CREATE VIEW v_ai_products AS
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

DROP VIEW IF EXISTS v_ai_inventory;
CREATE VIEW v_ai_inventory AS
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
JOIN products p ON p.id = pv.product_id;

-- v_ai_inventory: tồn kho theo chi nhánh; quantity là số xe hiện có.
-- branch_code hiện có: NT01, NT02, CR01.

DROP VIEW IF EXISTS v_ai_customers;
CREATE VIEW v_ai_customers AS
SELECT
    u.id AS customer_id,
    u.email,
    u.full_name,
    u.phone,
    u.user_type,
    u.home_branch_id,
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
LEFT JOIN customer_profiles cp ON cp.user_id = u.id
WHERE u.user_type = 'customer';

-- v_ai_customers: thông tin khách hàng và hồ sơ; tuyệt đối không có password_hash.
-- customer_status có thể là: Tiềm năng, Đang tư vấn, Đã mua, Ngừng liên hệ.

DROP VIEW IF EXISTS v_ai_orders;
CREATE VIEW v_ai_orders AS
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
    o.status,
    o.created_at
FROM orders o
JOIN users customer ON customer.id = o.customer_id
JOIN branches b ON b.id = o.branch_id
JOIN order_items oi ON oi.order_id = o.id
JOIN product_variants pv ON pv.id = oi.variant_id
JOIN products p ON p.id = pv.product_id;

-- v_ai_orders: đơn hàng kèm tên khách, mẫu xe, phiên bản và chi nhánh.
-- line_amount/unit_price/discount_amount là số nguyên đơn vị VNĐ.

DROP VIEW IF EXISTS v_ai_product_costs;
CREATE VIEW v_ai_product_costs AS
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
