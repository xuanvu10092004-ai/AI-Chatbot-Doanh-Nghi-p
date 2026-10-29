-- Thêm dữ liệu mô phỏng cho mẫu xe Air Blade 125 mà không ghi đè dữ liệu hiện có.
USE honda_chatbot;
SET NAMES utf8mb4;

-- Bổ sung dữ liệu mô phỏng, KHÔNG phải bảng giá/thông số/tồn kho thực tế.
-- Mẫu xe: Air Blade 125. Giá niêm yết/giá vốn: VNĐ; nhiên liệu: lít/100 km;
-- bình xăng: lít; khối lượng: kg; tồn kho: số xe.
-- Chỉ thêm bản ghi thiếu; chạy lại không ghi đè dữ liệu người dùng đã cập nhật.
-- Giữ nguyên schema chuẩn và toàn bộ dữ liệu khách hàng/đơn hàng đang có.
START TRANSACTION;

INSERT INTO products (model_name, segment, engine_cc, fuel_consumption_l100km, description)
SELECT 'Air Blade 125', 'tay_ga', 125, 2.1,
       'Dữ liệu mô phỏng bổ sung: xe ga 125cc; giá, thông số và tồn kho dùng cho thử nghiệm, không phải thông tin thương mại thực tế.'
WHERE NOT EXISTS (SELECT 1 FROM products WHERE model_name = 'Air Blade 125');

INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty)
SELECT p.id, '4 thì, 1 xy-lanh, làm mát bằng dung dịch', 4.4, 110,
       'Đĩa trước / Tang trống sau', '3 năm hoặc 30.000 km (mô phỏng)'
FROM products p
WHERE p.model_name = 'Air Blade 125'
  AND NOT EXISTS (SELECT 1 FROM product_specs s WHERE s.product_id = p.id);

INSERT INTO product_variants (product_id, variant_name, list_price, cost_price)
SELECT p.id, seed.variant_name, seed.list_price, seed.cost_price
FROM products p
JOIN (
    SELECT 'Air Blade 125 - Tiêu chuẩn - Đỏ đen' AS variant_name,
           42500000 AS list_price, 38500000 AS cost_price
    UNION ALL SELECT 'Air Blade 125 - Đặc biệt - Đen', 44500000, 40500000
    UNION ALL SELECT 'Air Blade 125 - Thể thao - Xám đen', 46500000, 42500000
) seed ON 1 = 1
WHERE p.model_name = 'Air Blade 125'
  AND NOT EXISTS (
      SELECT 1 FROM product_variants pv
      WHERE pv.product_id = p.id AND pv.variant_name = seed.variant_name
  );

INSERT INTO inventory (branch_id, variant_id, quantity)
SELECT b.id, pv.id, seed.quantity
FROM (
    SELECT 'NT01' AS branch_code, 'Air Blade 125 - Tiêu chuẩn - Đỏ đen' AS variant_name, 8 AS quantity
    UNION ALL SELECT 'NT02', 'Air Blade 125 - Tiêu chuẩn - Đỏ đen', 5
    UNION ALL SELECT 'CR01', 'Air Blade 125 - Tiêu chuẩn - Đỏ đen', 3
    UNION ALL SELECT 'NT01', 'Air Blade 125 - Đặc biệt - Đen', 4
    UNION ALL SELECT 'NT02', 'Air Blade 125 - Đặc biệt - Đen', 2
    UNION ALL SELECT 'CR01', 'Air Blade 125 - Đặc biệt - Đen', 0
    UNION ALL SELECT 'NT01', 'Air Blade 125 - Thể thao - Xám đen', 3
    UNION ALL SELECT 'NT02', 'Air Blade 125 - Thể thao - Xám đen', 0
    UNION ALL SELECT 'CR01', 'Air Blade 125 - Thể thao - Xám đen', 2
) seed
JOIN branches b ON b.code = seed.branch_code
JOIN product_variants pv ON pv.variant_name = seed.variant_name
JOIN products p ON p.id = pv.product_id AND p.model_name = 'Air Blade 125'
WHERE NOT EXISTS (
    SELECT 1 FROM inventory i WHERE i.branch_id = b.id AND i.variant_id = pv.id
);

COMMIT;
