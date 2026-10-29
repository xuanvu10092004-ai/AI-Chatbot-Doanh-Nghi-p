-- Mở rộng view sản phẩm AI với thông số kỹ thuật và từ điển mô tả cột.
USE honda_chatbot;
-- Bổ sung thông số đã có trong nguồn chuẩn; không thay đổi bảng nghiệp vụ.
CREATE OR REPLACE VIEW v_ai_products AS
SELECT p.id AS product_id, p.model_name, pv.id AS variant_id, pv.variant_name,
       SUBSTRING_INDEX(pv.variant_name, ' - ', -1) AS color,
       p.segment, p.engine_cc, pv.list_price,
       COALESCE((SELECT SUM(i.quantity) FROM inventory i WHERE i.variant_id = pv.id), 0) AS total_stock,
       p.fuel_consumption_l100km, p.description,
       ps.engine_type, ps.fuel_tank_l, ps.weight_kg, ps.brake_type, ps.warranty
FROM products p
JOIN product_variants pv ON pv.product_id = p.id
LEFT JOIN product_specs ps ON ps.product_id = p.id;

INSERT INTO ai_data_dictionary (view_name, column_name, description_vi) VALUES
('v_ai_products', 'description', 'Mô tả mẫu xe từ dữ liệu đã nạp'),
('v_ai_products', 'engine_type', 'Loại động cơ'),
('v_ai_products', 'fuel_consumption_l100km', 'Tiêu hao nhiên liệu (lít/100 km)'),
('v_ai_products', 'fuel_tank_l', 'Dung tích bình nhiên liệu (lít)'),
('v_ai_products', 'weight_kg', 'Khối lượng xe (kg)'),
('v_ai_products', 'brake_type', 'Loại phanh theo dữ liệu đã nạp'),
('v_ai_products', 'warranty', 'Điều kiện bảo hành từ dữ liệu đã nạp')
ON DUPLICATE KEY UPDATE description_vi = VALUES(description_vi);
