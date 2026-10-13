-- Sinh tự động bởi import_excel_to_sql.py - dữ liệu giả lập
USE honda_chatbot;
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS product_specs (
  product_id INT PRIMARY KEY,
  engine_type VARCHAR(100),
  fuel_tank_l DECIMAL(3,1),
  weight_kg SMALLINT,
  brake_type VARCHAR(100),
  warranty VARCHAR(60),
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customer_profiles (
  user_id INT PRIMARY KEY,
  customer_code VARCHAR(20) UNIQUE NOT NULL,
  gender ENUM('Nam','Nữ'),
  birth_date DATE,
  province VARCHAR(60),
  district VARCHAR(80),
  address VARCHAR(255),
  occupation VARCHAR(100),
  lead_source VARCHAR(60),
  interested_product_id INT NULL,
  payment_preference ENUM('Trả thẳng','Trả góp'),
  registered_at DATE,
  status ENUM('Tiềm năng','Đang tư vấn','Đã mua','Ngừng liên hệ'),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (interested_product_id) REFERENCES products(id) ON DELETE SET NULL
);

START TRANSACTION;
-- Xóa dữ liệu nghiệp vụ mẫu từ file schema và dữ liệu đã nạp lần trước
DELETE FROM order_items;
DELETE FROM orders;
DELETE FROM inventory;
DELETE FROM customer_profiles;
DELETE FROM product_specs;
DELETE FROM product_variants;
DELETE FROM products;
DELETE FROM user_roles WHERE user_id > 100;
DELETE FROM users WHERE id > 100;

-- products
INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES (1, 'Wave Alpha 110', 'xe_so', 109, 1.6, 'Xe số phổ thông, bền bỉ, tiết kiệm nhiên liệu.');
INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES (2, 'Blade 110', 'xe_so', 109, 1.7, 'Xe số thiết kế thể thao, phù hợp đi làm hằng ngày.');
INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES (3, 'Future 125 FI', 'xe_so', 125, 1.6, 'Xe số cao cấp, phun xăng điện tử.');
INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES (4, 'Vision 110', 'tay_ga', 110, 1.8, 'Tay ga nhỏ gọn, cốp rộng, phù hợp đi phố.');
INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES (5, 'Lead 125', 'tay_ga', 125, 2, 'Tay ga cốp cực rộng, yên thấp.');
INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES (6, 'Air Blade 160', 'tay_ga', 157, 2.3, 'Tay ga thể thao, động cơ 160cc.');
INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES (7, 'SH Mode 125', 'tay_ga', 125, 2.1, 'Tay ga thời trang, thiết kế sang trọng.');
INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES (8, 'SH 160i', 'tay_ga', 157, 2.3, 'Tay ga cao cấp, phanh ABS, khóa thông minh.');
INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES (9, 'Winner X', 'con_tay', 149, 2, 'Xe côn tay thể thao 150cc.');
INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES (10, 'Vario 160', 'tay_ga', 157, 2.2, 'Tay ga thể thao, thiết kế mạnh mẽ.');

-- product_specs
INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty) VALUES (1, '4 thì, 1 xy-lanh, làm mát bằng không khí', 3.7, 97, 'Cơ / Tang trống', '3 năm hoặc 30.000 km');
INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty) VALUES (2, '4 thì, 1 xy-lanh, làm mát bằng không khí', 4, 99, 'Đĩa trước / Tang trống sau', '3 năm hoặc 30.000 km');
INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty) VALUES (3, '4 thì, 1 xy-lanh, phun xăng điện tử', 4.6, 104, 'Đĩa trước / Tang trống sau', '3 năm hoặc 30.000 km');
INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty) VALUES (4, '4 thì, 1 xy-lanh, phun xăng điện tử', 4.9, 96, 'Đĩa trước / Tang trống sau', '3 năm hoặc 30.000 km');
INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty) VALUES (5, '4 thì, 1 xy-lanh, phun xăng điện tử', 6, 113, 'Đĩa trước / Tang trống sau', '3 năm hoặc 30.000 km');
INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty) VALUES (6, '4 thì, 1 xy-lanh, làm mát bằng dung dịch', 4.4, 113, 'Đĩa trước / Đĩa sau (ABS bản cao cấp)', '3 năm hoặc 30.000 km');
INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty) VALUES (7, '4 thì, 1 xy-lanh, phun xăng điện tử', 5.6, 116, 'Đĩa trước / Tang trống sau (ABS bản cao cấp)', '3 năm hoặc 30.000 km');
INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty) VALUES (8, '4 thì, 1 xy-lanh, làm mát bằng dung dịch', 7.8, 134, 'Đĩa trước / Đĩa sau, ABS', '3 năm hoặc 30.000 km');
INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty) VALUES (9, '4 thì, 1 xy-lanh, làm mát bằng dung dịch', 4.5, 124, 'Đĩa trước / Đĩa sau (ABS bản cao cấp)', '3 năm hoặc 30.000 km');
INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty) VALUES (10, '4 thì, 1 xy-lanh, làm mát bằng dung dịch', 5.5, 113, 'Đĩa trước / Đĩa sau', '3 năm hoặc 30.000 km');

-- product_variants
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (1, 1, 'Wave Alpha 110 - Tiêu chuẩn - Đen', 18900000, 17300000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (2, 1, 'Wave Alpha 110 - Tiêu chuẩn - Trắng', 18900000, 17300000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (3, 1, 'Wave Alpha 110 - Tiêu chuẩn - Đỏ', 18900000, 17300000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (4, 2, 'Blade 110 - Phanh cơ - Đỏ đen', 19800000, 18100000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (5, 2, 'Blade 110 - Phanh đĩa - Xanh đen', 21200000, 19400000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (6, 3, 'Future 125 FI - Tiêu chuẩn - Xanh đen', 31000000, 28400000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (7, 3, 'Future 125 FI - Cao cấp - Đen nhám', 32500000, 29700000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (8, 4, 'Vision 110 - Tiêu chuẩn - Trắng', 31500000, 28800000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (9, 4, 'Vision 110 - Cao cấp - Đỏ', 33500000, 30700000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (10, 4, 'Vision 110 - Thể thao - Xám đen', 36500000, 33400000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (11, 5, 'Lead 125 - Tiêu chuẩn - Xanh', 40500000, 37100000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (12, 5, 'Lead 125 - Cao cấp - Xám', 43500000, 39800000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (13, 5, 'Lead 125 - Đặc biệt - Đen', 45500000, 41600000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (14, 6, 'Air Blade 160 - Tiêu chuẩn - Đỏ', 56500000, 51700000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (15, 6, 'Air Blade 160 - Đặc biệt - Đen', 57500000, 52600000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (16, 6, 'Air Blade 160 - Cao cấp ABS - Xám', 60500000, 55400000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (17, 7, 'SH Mode 125 - Tiêu chuẩn - Trắng', 58500000, 53500000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (18, 7, 'SH Mode 125 - Cao cấp - Xanh', 64500000, 59000000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (19, 7, 'SH Mode 125 - Thể thao - Đỏ', 66000000, 60400000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (20, 8, 'SH 160i - Tiêu chuẩn - Xám', 92500000, 84600000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (21, 8, 'SH 160i - Cao cấp - Đen', 96500000, 88300000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (22, 8, 'SH 160i - Thể thao - Đỏ đen', 100500000, 92000000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (23, 9, 'Winner X - Tiêu chuẩn - Đỏ', 46000000, 42100000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (24, 9, 'Winner X - Thể thao - Xanh', 50000000, 45800000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (25, 9, 'Winner X - Đặc biệt ABS - Đen', 52500000, 48000000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (26, 10, 'Vario 160 - Tiêu chuẩn - Xám', 51500000, 47100000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (27, 10, 'Vario 160 - Đặc biệt - Đen', 52500000, 48000000);
INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES (28, 10, 'Vario 160 - Thể thao - Đỏ', 54500000, 49900000);

-- inventory
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 1, 1);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 1, 5);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 1, 0);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 2, 3);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 2, 10);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 2, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 3, 12);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 3, 10);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 3, 9);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 4, 12);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 4, 8);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 4, 2);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 5, 0);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 5, 1);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 5, 0);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 6, 4);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 6, 1);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 6, 9);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 7, 0);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 7, 8);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 7, 4);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 8, 3);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 8, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 8, 3);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 9, 5);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 9, 5);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 9, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 10, 10);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 10, 1);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 10, 4);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 11, 1);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 11, 10);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 11, 3);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 12, 4);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 12, 8);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 12, 1);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 13, 12);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 13, 4);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 13, 0);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 14, 5);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 14, 5);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 14, 9);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 15, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 15, 1);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 15, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 16, 12);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 16, 10);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 16, 9);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 17, 1);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 17, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 17, 9);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 18, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 18, 10);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 18, 3);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 19, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 19, 8);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 19, 0);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 20, 12);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 20, 3);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 20, 1);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 21, 0);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 21, 10);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 21, 0);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 22, 12);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 22, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 22, 9);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 23, 2);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 23, 8);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 23, 2);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 24, 1);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 24, 8);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 24, 9);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 25, 10);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 25, 4);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 25, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 26, 4);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 26, 10);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 26, 9);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 27, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 27, 6);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 27, 2);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (1, 28, 4);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (2, 28, 4);
INSERT INTO inventory (branch_id, variant_id, quantity) VALUES (3, 28, 0);

-- users (khách hàng)
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (101, 'duy.ln72@example.com', 'Lê Ngọc Duy', '0904571784', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (102, 'chau.tb79@example.com', 'Trần Bích Châu', '0933190845', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (103, 'dung.dt65@example.com', 'Dương Thu Dung', '0966283601', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (104, 'lan.np76@example.com', 'Ngô Phương Lan', '0983695793', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (105, 'trang.nk21@example.com', 'Nguyễn Kim Trang', '0926468616', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (106, 'hai.hg13@example.com', 'Huỳnh Gia Hải', '0933017568', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (107, 'trung.vm86@example.com', 'Võ Minh Trung', '0982141621', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (108, 'son.nq33@example.com', 'Ngô Quốc Sơn', '0960013041', 'customer', 3, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (109, 'mai.lm50@example.com', 'Lý Mỹ Mai', '0945060454', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (110, 'lan.vd55@example.com', 'Võ Diễm Lan', '0992566636', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (111, 'vinh.dv23@example.com', 'Đỗ Văn Vinh', '0980845850', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (112, 'quyen.nk71@example.com', 'Nguyễn Kim Quyên', '0979432627', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (113, 'bao.nm74@example.com', 'Ngô Minh Bảo', '0906688281', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (114, 'nhung.db55@example.com', 'Đỗ Bích Nhung', '0958280258', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (115, 'trung.dv94@example.com', 'Đỗ Văn Trung', '0916494157', 'customer', 3, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (116, 'hanh.nm93@example.com', 'Ngô Mỹ Hạnh', '0976523735', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (117, 'uyen.pt70@example.com', 'Phạm Thu Uyên', '0943528144', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (118, 'yen.nt8@example.com', 'Nguyễn Thanh Yến', '0962048425', 'customer', 3, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (119, 'yen.pm80@example.com', 'Phan Mỹ Yến', '0951838012', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (120, 'thinh.hm24@example.com', 'Hồ Minh Thịnh', '0988375555', 'customer', 3, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (121, 'vy.vp28@example.com', 'Vũ Phương Vy', '0990618847', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (122, 'hanh.vp4@example.com', 'Võ Phương Hạnh', '0973368828', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (123, 'trung.dd74@example.com', 'Đỗ Đức Trung', '0900442248', 'customer', 3, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (124, 'mai.lt70@example.com', 'Lê Thu Mai', '0917625280', 'customer', 3, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (125, 'hieu.vn29@example.com', 'Võ Ngọc Hiếu', '0973528667', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (126, 'dung.nm55@example.com', 'Ngô Mỹ Dung', '0908244560', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (127, 'chau.pp97@example.com', 'Phan Phương Châu', '0941775888', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (128, 'nam.tn14@example.com', 'Trần Ngọc Nam', '0961284001', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (129, 'nhung.dt6@example.com', 'Dương Thu Nhung', '0973927319', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (130, 'chau.dt46@example.com', 'Đỗ Thị Châu', '0998281953', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (131, 'huong.dn33@example.com', 'Đặng Ngọc Hương', '0920381780', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (132, 'hai.vh10@example.com', 'Vũ Hữu Hải', '0982889837', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (133, 'duy.da52@example.com', 'Đỗ Anh Duy', '0942710512', 'customer', 3, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (134, 'yen.pt66@example.com', 'Phan Thu Yến', '0951904316', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (135, 'lan.dt15@example.com', 'Dương Thanh Lan', '0912098426', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (136, 'lan.lh94@example.com', 'Lê Hoài Lan', '0944796745', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (137, 'thinh.ph79@example.com', 'Phạm Hữu Thịnh', '0984886457', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (138, 'phuc.dn77@example.com', 'Dương Ngọc Phúc', '0985846388', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (139, 'quyen.lh96@example.com', 'Lý Hoài Quyên', '0901332796', 'customer', 3, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (140, 'vinh.vv31@example.com', 'Võ Văn Vinh', '0954011527', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (141, 'vinh.ph71@example.com', 'Phan Hữu Vinh', '0962107617', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (142, 'mai.vn19@example.com', 'Võ Ngọc Mai', '0999446135', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (143, 'hieu.hn38@example.com', 'Hồ Ngọc Hiếu', '0964397258', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (144, 'dat.pn78@example.com', 'Phan Ngọc Đạt', '0961567959', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (145, 'vy.dp15@example.com', 'Đặng Phương Vy', '0956464403', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (146, 'trung.lv15@example.com', 'Lê Văn Trung', '0911196027', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (147, 'dung.dp9@example.com', 'Đặng Phương Dung', '0979677204', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (148, 'uyen.pb51@example.com', 'Phạm Bích Uyên', '0910591483', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (149, 'vinh.hc33@example.com', 'Huỳnh Công Vinh', '0997533257', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (150, 'mai.lt27@example.com', 'Lý Thanh Mai', '0941461754', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (151, 'bao.ha88@example.com', 'Huỳnh Anh Bảo', '0958930597', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (152, 'trung.nd56@example.com', 'Ngô Đức Trung', '0970907276', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (153, 'dat.hq23@example.com', 'Huỳnh Quốc Đạt', '0962394246', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (154, 'phuong.pn71@example.com', 'Phạm Ngọc Phượng', '0913421723', 'customer', 3, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (155, 'mai.bm68@example.com', 'Bùi Mỹ Mai', '0986561141', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (156, 'quan.vn99@example.com', 'Võ Ngọc Quân', '0982446026', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (157, 'lan.lt57@example.com', 'Lý Thanh Lan', '0903927330', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (158, 'son.nt14@example.com', 'Nguyễn Thanh Sơn', '0946351102', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (159, 'hung.nt6@example.com', 'Nguyễn Thanh Hùng', '0912670812', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (160, 'chau.np26@example.com', 'Nguyễn Phương Châu', '0970271861', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (161, 'khoa.pn43@example.com', 'Phan Ngọc Khoa', '0916768259', 'customer', 3, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (162, 'khoa.lt85@example.com', 'Lê Thanh Khoa', '0992082422', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (163, 'son.dm2@example.com', 'Đặng Minh Sơn', '0941517801', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (164, 'phuong.pt83@example.com', 'Phan Thu Phượng', '0982196121', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (165, 'mai.nm51@example.com', 'Nguyễn Mỹ Mai', '0955013510', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (166, 'hoa.pm77@example.com', 'Phạm Mỹ Hoa', '0986801543', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (167, 'long.pv77@example.com', 'Phạm Văn Long', '0941834190', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (168, 'bao.da27@example.com', 'Đỗ Anh Bảo', '0978776040', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (169, 'quyen.ph40@example.com', 'Phan Hoài Quyên', '0947660471', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (170, 'hanh.dt30@example.com', 'Dương Thị Hạnh', '0938792687', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (171, 'nhung.hb17@example.com', 'Huỳnh Bích Nhung', '0966075689', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (172, 'dung.db74@example.com', 'Dương Bích Dung', '0953971100', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (173, 'lan.nt80@example.com', 'Ngô Thị Lan', '0984427820', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (174, 'thao.pb58@example.com', 'Phan Bích Thảo', '0992141534', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (175, 'trang.lp76@example.com', 'Lê Phương Trang', '0922713831', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (176, 'lan.tp44@example.com', 'Trần Phương Lan', '0965798371', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (177, 'long.hd53@example.com', 'Huỳnh Đức Long', '0909658450', 'customer', 2, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (178, 'dung.tb60@example.com', 'Trần Bích Dung', '0981959610', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (179, 'vy.db7@example.com', 'Dương Bích Vy', '0925490921', 'customer', 1, '$2b$12$placeholder');
INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES (180, 'yen.hd13@example.com', 'Hồ Diễm Yến', '0968542474', 'customer', 2, '$2b$12$placeholder');

-- user_roles: gán role customer
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (101, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (102, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (103, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (104, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (105, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (106, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (107, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (108, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (109, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (110, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (111, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (112, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (113, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (114, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (115, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (116, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (117, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (118, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (119, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (120, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (121, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (122, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (123, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (124, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (125, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (126, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (127, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (128, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (129, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (130, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (131, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (132, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (133, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (134, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (135, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (136, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (137, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (138, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (139, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (140, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (141, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (142, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (143, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (144, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (145, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (146, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (147, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (148, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (149, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (150, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (151, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (152, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (153, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (154, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (155, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (156, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (157, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (158, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (159, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (160, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (161, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (162, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (163, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (164, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (165, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (166, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (167, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (168, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (169, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (170, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (171, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (172, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (173, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (174, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (175, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (176, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (177, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (178, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (179, 7, NULL, 1);
INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES (180, 7, NULL, 1);

-- customer_profiles
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (101, 'KH0001', 'Nam', '1998-08-12', 'Phú Yên', 'Tuy Hòa', '249 Yersin', 'Nhân viên ngân hàng', 'Zalo', 7, 'Trả góp', '2026-06-08', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (102, 'KH0002', 'Nữ', '1980-04-24', 'Ninh Thuận', 'Phan Rang - Tháp Chàm', '8 Nguyễn Thiện Thuật', 'Sinh viên', 'Website', 5, 'Trả góp', '2025-01-01', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (103, 'KH0003', 'Nữ', '1974-10-05', 'Phú Yên', 'Tuy Hòa', '259 Hùng Vương', 'Kỹ sư', 'Website', 4, 'Trả thẳng', '2025-03-28', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (104, 'KH0004', 'Nữ', '1966-08-11', 'Khánh Hòa', 'Nha Trang', '63 Yersin', 'Y tá / Điều dưỡng', 'Hotline', 6, 'Trả thẳng', '2026-04-23', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (105, 'KH0005', 'Nữ', '1966-09-27', 'Khánh Hòa', 'Diên Khánh', '97 Yersin', 'Tài xế công nghệ', 'Zalo', 2, 'Trả góp', '2025-01-21', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (106, 'KH0006', 'Nam', '2006-07-10', 'Khánh Hòa', 'Nha Trang', '247 Yersin', 'Lập trình viên', 'Hotline', 5, 'Trả thẳng', '2025-05-03', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (107, 'KH0007', 'Nam', '1988-10-26', 'Khánh Hòa', 'Nha Trang', '144 Lạc Long Quân', 'Y tá / Điều dưỡng', 'Website', 7, 'Trả góp', '2026-08-05', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (108, 'KH0008', 'Nam', '1978-10-27', 'Khánh Hòa', 'Cam Lâm', '83 Hùng Vương', 'Giáo viên', 'Hotline', 1, 'Trả góp', '2025-09-20', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (109, 'KH0009', 'Nữ', '2003-06-20', 'Khánh Hòa', 'Nha Trang', '62 Ngô Gia Tự', 'Hướng dẫn viên du lịch', 'Website', 9, 'Trả góp', '2026-01-19', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (110, 'KH0010', 'Nữ', '1987-06-07', 'Khánh Hòa', 'Ninh Hòa', '58 Lê Hồng Phong', 'Y tá / Điều dưỡng', 'Zalo', 2, 'Trả thẳng', '2026-09-26', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (111, 'KH0011', 'Nam', '1993-07-09', 'Khánh Hòa', 'Nha Trang', '9 Hùng Vương', 'Y tá / Điều dưỡng', 'Website', 5, 'Trả thẳng', '2026-07-09', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (112, 'KH0012', 'Nữ', '2001-12-28', 'Khánh Hòa', 'Vạn Ninh', '120 Lạc Long Quân', 'Nhân viên văn phòng', 'Facebook', 4, 'Trả góp', '2025-10-10', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (113, 'KH0013', 'Nam', '1977-09-24', 'Khánh Hòa', 'Ninh Hòa', '52 Nguyễn Chánh', 'Giáo viên', 'Zalo', 5, 'Trả góp', '2025-01-19', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (114, 'KH0014', 'Nữ', '1966-10-22', 'Khánh Hòa', 'Nha Trang', '150 Hùng Vương', 'Sinh viên', 'Zalo', 3, 'Trả thẳng', '2026-07-09', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (115, 'KH0015', 'Nam', '1967-05-07', 'Khánh Hòa', 'Cam Ranh', '128 Lê Hồng Phong', 'Nhân viên ngân hàng', 'Website', 10, 'Trả thẳng', '2025-04-19', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (116, 'KH0016', 'Nữ', '1968-02-26', 'Khánh Hòa', 'Nha Trang', '116 Lê Hồng Phong', 'Lập trình viên', 'Facebook', 4, 'Trả góp', '2025-11-29', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (117, 'KH0017', 'Nữ', '1996-11-24', 'Khánh Hòa', 'Nha Trang', '61 Phạm Văn Đồng', 'Nông dân', 'Trực tiếp tại cửa hàng', 8, 'Trả góp', '2025-09-30', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (118, 'KH0018', 'Nữ', '1993-06-04', 'Khánh Hòa', 'Cam Lâm', '280 Lạc Long Quân', 'Nông dân', 'Hotline', 4, 'Trả góp', '2025-08-03', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (119, 'KH0019', 'Nữ', '1965-04-21', 'Khánh Hòa', 'Diên Khánh', '138 Phạm Văn Đồng', 'Công nhân', 'Zalo', 7, 'Trả góp', '2025-01-19', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (120, 'KH0020', 'Nam', '1968-07-23', 'Khánh Hòa', 'Cam Ranh', '69 Nguyễn Thiện Thuật', 'Nông dân', 'Trực tiếp tại cửa hàng', 3, 'Trả góp', '2025-01-29', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (121, 'KH0021', 'Nữ', '1966-08-05', 'Khánh Hòa', 'Diên Khánh', '130 Đường 23 Tháng 10', 'Nông dân', 'Website', 2, 'Trả góp', '2026-04-23', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (122, 'KH0022', 'Nữ', '1972-09-28', 'Khánh Hòa', 'Ninh Hòa', '271 Lạc Long Quân', 'Kinh doanh tự do', 'Facebook', 6, 'Trả góp', '2026-01-28', 'Ngừng liên hệ');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (123, 'KH0023', 'Nam', '2006-07-18', 'Khánh Hòa', 'Cam Ranh', '78 Nguyễn Trãi', 'Hướng dẫn viên du lịch', 'Facebook', 7, 'Trả thẳng', '2026-07-19', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (124, 'KH0024', 'Nữ', '1996-11-05', 'Khánh Hòa', 'Cam Ranh', '280 Trần Phú', 'Nhân viên ngân hàng', 'Website', 3, 'Trả thẳng', '2025-11-04', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (125, 'KH0025', 'Nam', '1978-01-06', 'Khánh Hòa', 'Diên Khánh', '47 2 Tháng 4', 'Nội trợ', 'Facebook', 2, 'Trả thẳng', '2026-03-20', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (126, 'KH0026', 'Nữ', '1990-02-07', 'Khánh Hòa', 'Nha Trang', '41 Phạm Văn Đồng', 'Nhân viên ngân hàng', 'Giới thiệu', 6, 'Trả góp', '2026-09-30', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (127, 'KH0027', 'Nữ', '2006-02-26', 'Khánh Hòa', 'Nha Trang', '184 Yersin', 'Giáo viên', 'Facebook', 6, 'Trả góp', '2026-01-22', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (128, 'KH0028', 'Nam', '1967-08-19', 'Khánh Hòa', 'Diên Khánh', '295 Yersin', 'Lập trình viên', 'Giới thiệu', 5, 'Trả thẳng', '2026-09-21', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (129, 'KH0029', 'Nữ', '2005-04-11', 'Khánh Hòa', 'Nha Trang', '125 2 Tháng 4', 'Nhân viên ngân hàng', 'Giới thiệu', 5, 'Trả góp', '2025-09-02', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (130, 'KH0030', 'Nữ', '2004-07-24', 'Khánh Hòa', 'Nha Trang', '72 Hùng Vương', 'Nông dân', 'Website', 9, 'Trả thẳng', '2025-09-04', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (131, 'KH0031', 'Nữ', '1998-07-13', 'Đắk Lắk', 'Buôn Ma Thuột', '27 Hùng Vương', 'Công nhân', 'Hotline', 5, 'Trả góp', '2025-06-23', 'Ngừng liên hệ');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (132, 'KH0032', 'Nam', '1966-02-06', 'Khánh Hòa', 'Nha Trang', '4 Hùng Vương', 'Nội trợ', 'Website', 6, 'Trả góp', '2026-09-25', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (133, 'KH0033', 'Nam', '1968-01-01', 'Khánh Hòa', 'Cam Ranh', '226 Ngô Gia Tự', 'Nông dân', 'Giới thiệu', 2, 'Trả thẳng', '2026-09-30', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (134, 'KH0034', 'Nữ', '1972-09-04', 'Khánh Hòa', 'Diên Khánh', '46 Lý Thái Tổ', 'Kinh doanh tự do', 'Facebook', 6, 'Trả thẳng', '2026-05-25', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (135, 'KH0035', 'Nữ', '2005-06-24', 'Khánh Hòa', 'Nha Trang', '50 Thống Nhất', 'Tài xế công nghệ', 'Website', 7, 'Trả góp', '2026-04-28', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (136, 'KH0036', 'Nữ', '1983-02-04', 'Khánh Hòa', 'Nha Trang', '35 Đường 23 Tháng 10', 'Nội trợ', 'Zalo', 10, 'Trả thẳng', '2026-01-30', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (137, 'KH0037', 'Nam', '1994-07-08', 'Ninh Thuận', 'Phan Rang - Tháp Chàm', '85 Võ Văn Ký', 'Kinh doanh tự do', 'Zalo', 3, 'Trả góp', '2025-04-14', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (138, 'KH0038', 'Nam', '1977-07-22', 'Khánh Hòa', 'Nha Trang', '193 Ngô Gia Tự', 'Tài xế công nghệ', 'Hotline', 6, 'Trả góp', '2026-05-24', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (139, 'KH0039', 'Nữ', '1974-07-17', 'Khánh Hòa', 'Cam Ranh', '187 Đường 23 Tháng 10', 'Nhân viên ngân hàng', 'Zalo', 6, 'Trả góp', '2025-09-07', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (140, 'KH0040', 'Nam', '1968-02-04', 'Khánh Hòa', 'Nha Trang', '308 Phạm Văn Đồng', 'Y tá / Điều dưỡng', 'Trực tiếp tại cửa hàng', 10, 'Trả thẳng', '2026-06-13', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (141, 'KH0041', 'Nam', '2001-06-20', 'Khánh Hòa', 'Nha Trang', '122 Lê Hồng Phong', 'Nhân viên ngân hàng', 'Website', 5, 'Trả góp', '2026-03-31', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (142, 'KH0042', 'Nữ', '1982-07-21', 'Khánh Hòa', 'Ninh Hòa', '269 Thống Nhất', 'Lập trình viên', 'Website', 1, 'Trả góp', '2026-03-11', 'Ngừng liên hệ');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (143, 'KH0043', 'Nam', '1978-10-28', 'Khánh Hòa', 'Nha Trang', '310 Lạc Long Quân', 'Tài xế công nghệ', 'Facebook', 5, 'Trả góp', '2025-07-05', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (144, 'KH0044', 'Nam', '1965-04-20', 'Khánh Hòa', 'Ninh Hòa', '63 Ngô Gia Tự', 'Kỹ sư', 'Facebook', 4, 'Trả thẳng', '2025-12-11', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (145, 'KH0045', 'Nữ', '1997-01-12', 'Khánh Hòa', 'Nha Trang', '12 Đường 23 Tháng 10', 'Kinh doanh tự do', 'Website', 5, 'Trả thẳng', '2025-10-29', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (146, 'KH0046', 'Nam', '2004-10-18', 'Khánh Hòa', 'Ninh Hòa', '275 Lạc Long Quân', 'Nội trợ', 'Giới thiệu', 6, 'Trả thẳng', '2026-10-11', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (147, 'KH0047', 'Nữ', '1993-08-07', 'Phú Yên', 'Tuy Hòa', '77 Hùng Vương', 'Lập trình viên', 'Website', 2, 'Trả thẳng', '2026-07-04', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (148, 'KH0048', 'Nữ', '1987-03-07', 'Khánh Hòa', 'Ninh Hòa', '152 Trần Phú', 'Kinh doanh tự do', 'Facebook', 2, 'Trả góp', '2025-04-16', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (149, 'KH0049', 'Nam', '1969-09-03', 'Khánh Hòa', 'Nha Trang', '179 Võ Văn Ký', 'Giáo viên', 'Hotline', 2, 'Trả thẳng', '2025-05-21', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (150, 'KH0050', 'Nữ', '2006-06-28', 'Phú Yên', 'Tuy Hòa', '243 Ngô Gia Tự', 'Tài xế công nghệ', 'Zalo', 9, 'Trả thẳng', '2025-02-04', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (151, 'KH0051', 'Nam', '2001-11-07', 'Phú Yên', 'Tuy Hòa', '162 Thống Nhất', 'Y tá / Điều dưỡng', 'Trực tiếp tại cửa hàng', 6, 'Trả góp', '2025-01-29', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (152, 'KH0052', 'Nam', '1973-05-18', 'Khánh Hòa', 'Nha Trang', '207 Lạc Long Quân', 'Giáo viên', 'Hotline', 6, 'Trả góp', '2025-03-24', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (153, 'KH0053', 'Nam', '1982-11-07', 'Khánh Hòa', 'Nha Trang', '5 Nguyễn Thiện Thuật', 'Tài xế công nghệ', 'Trực tiếp tại cửa hàng', 7, 'Trả góp', '2025-02-09', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (154, 'KH0054', 'Nữ', '1980-06-28', 'Khánh Hòa', 'Cam Ranh', '306 Nguyễn Trãi', 'Hướng dẫn viên du lịch', 'Zalo', 3, 'Trả góp', '2026-05-17', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (155, 'KH0055', 'Nữ', '2004-12-27', 'Khánh Hòa', 'Nha Trang', '24 Hùng Vương', 'Hướng dẫn viên du lịch', 'Website', 4, 'Trả thẳng', '2026-04-21', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (156, 'KH0056', 'Nam', '2004-05-20', 'Khánh Hòa', 'Nha Trang', '146 Nguyễn Chánh', 'Giáo viên', 'Giới thiệu', 6, 'Trả góp', '2025-06-24', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (157, 'KH0057', 'Nữ', '1996-01-03', 'Khánh Hòa', 'Nha Trang', '22 Ngô Gia Tự', 'Công nhân', 'Trực tiếp tại cửa hàng', 6, 'Trả thẳng', '2025-11-18', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (158, 'KH0058', 'Nam', '2006-08-15', 'Khánh Hòa', 'Ninh Hòa', '50 Nguyễn Chánh', 'Nhân viên văn phòng', 'Zalo', 10, 'Trả thẳng', '2026-03-07', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (159, 'KH0059', 'Nam', '1991-01-01', 'Khánh Hòa', 'Nha Trang', '227 Nguyễn Thiện Thuật', 'Lập trình viên', 'Giới thiệu', 5, 'Trả góp', '2026-03-18', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (160, 'KH0060', 'Nữ', '1990-03-19', 'Khánh Hòa', 'Nha Trang', '305 Đường 23 Tháng 10', 'Công nhân', 'Giới thiệu', 1, 'Trả thẳng', '2026-06-05', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (161, 'KH0061', 'Nam', '2003-08-01', 'Khánh Hòa', 'Cam Ranh', '175 Phạm Văn Đồng', 'Nhân viên ngân hàng', 'Zalo', 5, 'Trả góp', '2025-09-24', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (162, 'KH0062', 'Nam', '1984-11-22', 'Khánh Hòa', 'Nha Trang', '115 Đường 23 Tháng 10', 'Nhân viên văn phòng', 'Hotline', 4, 'Trả góp', '2026-02-21', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (163, 'KH0063', 'Nam', '1974-08-23', 'Đắk Lắk', 'Buôn Ma Thuột', '305 Ngô Gia Tự', 'Kinh doanh tự do', 'Zalo', 1, 'Trả thẳng', '2026-01-09', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (164, 'KH0064', 'Nữ', '1989-12-14', 'Khánh Hòa', 'Nha Trang', '241 Lạc Long Quân', 'Kinh doanh tự do', 'Giới thiệu', 9, 'Trả góp', '2025-05-24', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (165, 'KH0065', 'Nữ', '1965-03-07', 'Khánh Hòa', 'Vạn Ninh', '297 2 Tháng 4', 'Hướng dẫn viên du lịch', 'Hotline', 9, 'Trả thẳng', '2026-09-08', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (166, 'KH0066', 'Nữ', '1995-08-03', 'Phú Yên', 'Tuy Hòa', '139 Thống Nhất', 'Giáo viên', 'Trực tiếp tại cửa hàng', 6, 'Trả thẳng', '2025-08-30', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (167, 'KH0067', 'Nam', '1972-01-06', 'Khánh Hòa', 'Diên Khánh', '1 Phạm Văn Đồng', 'Nội trợ', 'Giới thiệu', 1, 'Trả thẳng', '2025-05-01', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (168, 'KH0068', 'Nam', '1999-06-26', 'Khánh Hòa', 'Nha Trang', '67 Lê Hồng Phong', 'Công nhân', 'Facebook', 10, 'Trả thẳng', '2025-06-29', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (169, 'KH0069', 'Nữ', '1993-05-22', 'Khánh Hòa', 'Nha Trang', '229 2 Tháng 4', 'Kinh doanh tự do', 'Giới thiệu', 8, 'Trả thẳng', '2025-10-03', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (170, 'KH0070', 'Nữ', '1979-05-19', 'Khánh Hòa', 'Vạn Ninh', '6 Nguyễn Trãi', 'Nhân viên ngân hàng', 'Website', 1, 'Trả thẳng', '2026-02-27', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (171, 'KH0071', 'Nữ', '1981-10-10', 'Khánh Hòa', 'Nha Trang', '125 Yersin', 'Kỹ sư', 'Facebook', 1, 'Trả thẳng', '2025-07-02', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (172, 'KH0072', 'Nữ', '1967-09-17', 'Khánh Hòa', 'Ninh Hòa', '128 Nguyễn Trãi', 'Lập trình viên', 'Giới thiệu', 2, 'Trả góp', '2026-03-18', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (173, 'KH0073', 'Nữ', '1972-09-26', 'Khánh Hòa', 'Diên Khánh', '253 Trần Phú', 'Hướng dẫn viên du lịch', 'Trực tiếp tại cửa hàng', 6, 'Trả thẳng', '2025-03-31', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (174, 'KH0074', 'Nữ', '1967-08-25', 'Khánh Hòa', 'Nha Trang', '198 Hùng Vương', 'Tài xế công nghệ', 'Trực tiếp tại cửa hàng', 2, 'Trả góp', '2025-08-04', 'Đã mua');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (175, 'KH0075', 'Nữ', '1967-10-19', 'Khánh Hòa', 'Nha Trang', '87 Nguyễn Thiện Thuật', 'Sinh viên', 'Giới thiệu', 7, 'Trả góp', '2025-05-11', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (176, 'KH0076', 'Nữ', '2002-11-05', 'Khánh Hòa', 'Diên Khánh', '192 Lê Hồng Phong', 'Nhân viên ngân hàng', 'Hotline', 2, 'Trả góp', '2026-09-23', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (177, 'KH0077', 'Nam', '1983-01-23', 'Khánh Hòa', 'Ninh Hòa', '162 Trần Phú', 'Nhân viên văn phòng', 'Trực tiếp tại cửa hàng', 1, 'Trả góp', '2025-03-14', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (178, 'KH0078', 'Nữ', '1969-01-04', 'Khánh Hòa', 'Nha Trang', '191 2 Tháng 4', 'Giáo viên', 'Website', 3, 'Trả thẳng', '2025-02-13', 'Đang tư vấn');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (179, 'KH0079', 'Nữ', '1977-02-12', 'Khánh Hòa', 'Nha Trang', '250 Phạm Văn Đồng', 'Nhân viên khách sạn', 'Hotline', 6, 'Trả thẳng', '2025-09-11', 'Tiềm năng');
INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES (180, 'KH0080', 'Nữ', '1975-02-26', 'Khánh Hòa', 'Nha Trang', '118 Thống Nhất', 'Tài xế công nghệ', 'Hotline', 6, 'Trả thẳng', '2026-01-27', 'Đang tư vấn');

-- orders + order_items (từ khách có trạng thái Đã mua)
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (1, 2, 103, 4, 2, 'delivered', 0, '2025-03-31 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (1, 10, 1, 36500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (2, 1, 110, 3, 2, 'delivered', 0, '2026-09-29 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (2, 5, 1, 21200000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (3, 1, 111, 3, 2, 'delivered', 500000, '2026-07-12 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (3, 13, 1, 45500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (4, 2, 112, 4, 2, 'delivered', 1000000, '2025-10-13 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (4, 10, 1, 36500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (5, 2, 114, 4, 2, 'delivered', 0, '2026-07-12 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (5, 6, 1, 31000000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (6, 2, 121, 4, 2, 'delivered', 0, '2026-04-26 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (6, 13, 1, 45500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (7, 3, 123, 3, 2, 'delivered', 500000, '2026-07-22 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (7, 19, 1, 66000000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (8, 1, 126, 3, 2, 'delivered', 1000000, '2026-10-03 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (8, 15, 1, 57500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (9, 1, 128, 3, 2, 'delivered', 0, '2026-09-24 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (9, 5, 1, 21200000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (10, 1, 130, 3, 2, 'delivered', 0, '2025-09-07 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (10, 25, 1, 52500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (11, 3, 133, 3, 2, 'delivered', 500000, '2026-10-03 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (11, 5, 1, 21200000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (12, 2, 135, 4, 2, 'delivered', 1000000, '2026-05-01 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (12, 22, 1, 100500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (13, 1, 137, 3, 2, 'delivered', 0, '2025-04-17 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (13, 7, 1, 32500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (14, 2, 143, 4, 2, 'delivered', 0, '2025-07-08 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (14, 12, 1, 43500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (15, 1, 146, 3, 2, 'delivered', 500000, '2026-10-12 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (15, 15, 1, 57500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (16, 2, 149, 4, 2, 'delivered', 1000000, '2025-05-24 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (16, 4, 1, 19800000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (17, 1, 150, 3, 2, 'delivered', 0, '2025-02-07 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (17, 25, 1, 52500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (18, 2, 151, 4, 2, 'delivered', 0, '2025-02-01 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (18, 16, 1, 60500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (19, 3, 154, 3, 2, 'delivered', 500000, '2026-05-20 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (19, 7, 1, 32500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (20, 1, 156, 3, 2, 'delivered', 1000000, '2025-06-27 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (20, 15, 1, 57500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (21, 1, 157, 3, 2, 'delivered', 0, '2025-11-21 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (21, 14, 1, 56500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (22, 1, 159, 3, 2, 'delivered', 0, '2026-03-21 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (22, 13, 1, 45500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (23, 3, 161, 3, 2, 'delivered', 500000, '2025-09-27 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (23, 11, 1, 40500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (24, 1, 162, 3, 2, 'delivered', 1000000, '2026-02-24 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (24, 19, 1, 66000000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (25, 2, 163, 4, 2, 'delivered', 0, '2026-01-12 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (25, 4, 1, 19800000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (26, 2, 165, 4, 2, 'delivered', 0, '2026-09-11 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (26, 24, 1, 50000000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (27, 1, 166, 3, 2, 'delivered', 500000, '2025-09-02 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (27, 15, 1, 57500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (28, 2, 169, 4, 2, 'delivered', 1000000, '2025-10-06 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (28, 22, 1, 100500000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (29, 2, 172, 4, 2, 'delivered', 0, '2026-03-21 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (29, 5, 1, 21200000);
INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES (30, 2, 174, 4, 2, 'delivered', 0, '2025-08-07 10:00:00');
INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES (30, 5, 1, 21200000);

COMMIT;

-- Kiểm tra số dòng sau khi nạp (kỳ vọng: 10 / 28 / 84 / 80 / 80 / số khách 'Đã mua')
SELECT 'products' AS tbl, COUNT(*) AS n FROM products
UNION ALL SELECT 'product_variants', COUNT(*) FROM product_variants
UNION ALL SELECT 'inventory', COUNT(*) FROM inventory
UNION ALL SELECT 'customers (users > 100)', COUNT(*) FROM users WHERE id > 100
UNION ALL SELECT 'customer_profiles', COUNT(*) FROM customer_profiles
UNION ALL SELECT 'orders', COUNT(*) FROM orders;
