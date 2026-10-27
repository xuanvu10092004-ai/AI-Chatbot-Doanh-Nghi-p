-- Synthetic fixture only. No live import/PII is included.

-- =====================================================================
-- MÔ PHỎNG CSDL RBAC CHO CHATBOT ĐẠI LÝ XE MÁY HONDA
-- Engine: MySQL 8.0.16+ (cần CHECK constraint)
-- Toàn bộ dữ liệu (tên, giá, tồn kho, chính sách) là DỮ LIỆU GIẢ LẬP.
-- =====================================================================
-- Ý tưởng chính:
--   1. RBAC chuẩn: users -> roles -> permissions
--   2. Mỗi tài liệu tri thức (RAG) thuộc 1 danh mục, mỗi danh mục yêu cầu 1 permission
--   3. Mỗi "intent" của chatbot yêu cầu 1 permission -> chặn trước khi truy vấn dữ liệu
--   4. Phạm vi chi nhánh (branch scope) trong user_roles
--   5. Audit log cho mọi lượt hỏi, kể cả bị từ chối
-- =====================================================================

DROP DATABASE IF EXISTS honda_chatbot_test;
CREATE DATABASE honda_chatbot_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE honda_chatbot_test;

-- =====================================================================
-- 1. NHÓM RBAC
-- =====================================================================

CREATE TABLE branches (
  id INT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(20) UNIQUE NOT NULL,
  name VARCHAR(150) NOT NULL,
  city VARCHAR(80) NOT NULL
);

CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  email VARCHAR(255) UNIQUE NOT NULL,
  full_name VARCHAR(150) NOT NULL,
  phone VARCHAR(20),
  user_type ENUM('staff','customer') NOT NULL,
  home_branch_id INT NULL,
  password_hash VARCHAR(255) NOT NULL,           -- placeholder, thực tế dùng bcrypt/argon2
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (home_branch_id) REFERENCES branches(id)
);

CREATE TABLE roles (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) UNIQUE NOT NULL,
  description VARCHAR(255)
);

CREATE TABLE permissions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(100) UNIQUE NOT NULL,             -- dạng resource:action
  description VARCHAR(255)
);

-- scope_branch_id: NULL = toàn hệ thống, có giá trị = chỉ trong chi nhánh đó
CREATE TABLE user_roles (
  user_id INT NOT NULL,
  role_id INT NOT NULL,
  scope_branch_id INT NULL,
  granted_by INT NULL,
  granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, role_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
  FOREIGN KEY (scope_branch_id) REFERENCES branches(id),
  FOREIGN KEY (granted_by) REFERENCES users(id)
);

CREATE TABLE role_permissions (
  role_id INT NOT NULL,
  permission_id INT NOT NULL,
  PRIMARY KEY (role_id, permission_id),
  FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
  FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- =====================================================================
-- 2. NHÓM DỮ LIỆU KINH DOANH
-- =====================================================================

CREATE TABLE products (
  id INT PRIMARY KEY AUTO_INCREMENT,
  model_name VARCHAR(100) NOT NULL,
  segment ENUM('xe_so','tay_ga','con_tay') NOT NULL,
  engine_cc SMALLINT NOT NULL,
  fuel_consumption_l100km DECIMAL(3,1),
  description TEXT
);

CREATE TABLE product_variants (
  id INT PRIMARY KEY AUTO_INCREMENT,
  product_id INT NOT NULL,
  variant_name VARCHAR(100) NOT NULL,            -- phiên bản + màu
  list_price BIGINT NOT NULL,                    -- giá niêm yết (công khai)
  cost_price BIGINT NOT NULL,                    -- giá vốn (NHẠY CẢM: price:cost:read)
  FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE inventory (
  branch_id INT NOT NULL,
  variant_id INT NOT NULL,
  quantity INT NOT NULL DEFAULT 0 CHECK (quantity >= 0),
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (branch_id, variant_id),
  FOREIGN KEY (branch_id) REFERENCES branches(id),
  FOREIGN KEY (variant_id) REFERENCES product_variants(id)
);

CREATE TABLE orders (
  id INT PRIMARY KEY AUTO_INCREMENT,
  branch_id INT NOT NULL,
  customer_id INT NOT NULL,
  created_by INT NOT NULL,
  approved_by INT NULL,
  status ENUM('pending','approved','paid','delivered','cancelled') NOT NULL DEFAULT 'pending',
  discount_amount BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (branch_id) REFERENCES branches(id),
  FOREIGN KEY (customer_id) REFERENCES users(id),
  FOREIGN KEY (created_by) REFERENCES users(id),
  FOREIGN KEY (approved_by) REFERENCES users(id),
  -- Separation of Duties: người tạo đơn không được tự duyệt
  CONSTRAINT chk_sod CHECK (approved_by IS NULL OR approved_by <> created_by)
);

CREATE TABLE order_items (
  order_id INT NOT NULL,
  variant_id INT NOT NULL,
  quantity INT NOT NULL DEFAULT 1,
  unit_price BIGINT NOT NULL,
  PRIMARY KEY (order_id, variant_id),
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY (variant_id) REFERENCES product_variants(id)
);

-- =====================================================================
-- 3. NHÓM CHATBOT
-- =====================================================================

-- Danh mục tri thức: mỗi danh mục gắn với 1 permission cần có để đọc
CREATE TABLE kb_categories (
  id INT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(150) NOT NULL,
  required_permission_id INT NOT NULL,
  FOREIGN KEY (required_permission_id) REFERENCES permissions(id)
);

-- Tài liệu cho RAG. branch_id NULL = áp dụng toàn hệ thống
CREATE TABLE kb_documents (
  id INT PRIMARY KEY AUTO_INCREMENT,
  category_id INT NOT NULL,
  branch_id INT NULL,
  title VARCHAR(255) NOT NULL,
  content TEXT NOT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (category_id) REFERENCES kb_categories(id),
  FOREIGN KEY (branch_id) REFERENCES branches(id)
);

-- Intent -> permission: chatbot kiểm tra TRƯỚC khi gọi tool/truy vấn dữ liệu
CREATE TABLE chatbot_intents (
  id INT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(60) UNIQUE NOT NULL,
  description VARCHAR(255),
  required_permission_id INT NOT NULL,
  data_source VARCHAR(100) NOT NULL,             -- bảng/tool mà intent sẽ đọc
  FOREIGN KEY (required_permission_id) REFERENCES permissions(id)
);

CREATE TABLE chat_sessions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NULL,                              -- NULL = khách vãng lai (guest)
  channel ENUM('web','zalo','facebook','internal_app') NOT NULL,
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE chat_messages (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id INT NOT NULL,
  sender ENUM('user','bot') NOT NULL,
  content TEXT NOT NULL,
  detected_intent_id INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (detected_intent_id) REFERENCES chatbot_intents(id)
);

CREATE TABLE chatbot_audit_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id INT NOT NULL,
  user_id INT NULL,
  intent_id INT NULL,
  decision ENUM('allowed','denied') NOT NULL,
  reason VARCHAR(255),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
  FOREIGN KEY (intent_id) REFERENCES chatbot_intents(id)
);

-- =====================================================================
-- 4. DỮ LIỆU MẪU: RBAC
-- =====================================================================

INSERT INTO branches (id, code, name, city) VALUES
(1, 'NT01', 'Head Honda Nha Trang 1', 'Nha Trang'),
(2, 'NT02', 'Head Honda Nha Trang 2', 'Nha Trang'),
(3, 'CR01', 'Head Honda Cam Ranh',    'Cam Ranh');

INSERT INTO roles (id, name, description) VALUES
(1, 'super_admin',    'Quản trị toàn hệ thống'),
(2, 'branch_manager', 'Quản lý chi nhánh'),
(3, 'sales_staff',    'Nhân viên bán hàng'),
(4, 'technician',     'Kỹ thuật viên bảo hành/bảo dưỡng'),
(5, 'accountant',     'Kế toán'),
(6, 'marketing',      'Nhân viên marketing'),
(7, 'customer',       'Khách hàng đã đăng ký tài khoản'),
(8, 'guest',          'Khách vãng lai, chưa đăng nhập');

INSERT INTO permissions (id, code, description) VALUES
(1,  'chatbot:use',       'Được dùng chatbot'),
(2,  'kb:public:read',    'Đọc tri thức công khai (giá niêm yết, thông số, khuyến mãi)'),
(3,  'kb:sales:read',     'Đọc tri thức bán hàng nội bộ (chiết khấu, kịch bản tư vấn)'),
(4,  'kb:technical:read', 'Đọc tri thức kỹ thuật (quy trình bảo dưỡng, mã lỗi)'),
(5,  'kb:finance:read',   'Đọc tri thức tài chính (công nợ, quy trình hoàn tiền)'),
(6,  'kb:internal:read',  'Đọc quy định nội bộ (nhân sự, quy chế)'),
(7,  'inventory:read',    'Xem tồn kho'),
(8,  'order:read',        'Xem đơn hàng'),
(9,  'order:create',      'Tạo đơn hàng'),
(10, 'order:approve',     'Duyệt đơn hàng'),
(11, 'customer:read',     'Xem thông tin khách hàng'),
(12, 'price:cost:read',   'Xem giá vốn / biên lợi nhuận'),
(13, 'kb:manage',         'Thêm/sửa/xóa tài liệu tri thức'),
(14, 'user:manage',       'Quản lý người dùng và phân quyền'),
(15, 'audit:read',        'Xem audit log chatbot'),
(16, 'discount:approve',  'Duyệt mức giảm giá vượt khung');

INSERT INTO role_permissions (role_id, permission_id) VALUES
-- guest: chỉ xem thông tin công khai
(8, 2),
-- customer
(7, 1), (7, 2),
-- sales_staff
(3, 1), (3, 2), (3, 3), (3, 7), (3, 8), (3, 9), (3, 11),
-- technician
(4, 1), (4, 2), (4, 4), (4, 7),
-- accountant
(5, 1), (5, 2), (5, 5), (5, 8), (5, 12),
-- marketing
(6, 1), (6, 2), (6, 3), (6, 13),
-- branch_manager
(2, 1), (2, 2), (2, 3), (2, 4), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10), (2, 11), (2, 16);

-- super_admin: tất cả permission
INSERT INTO role_permissions (role_id, permission_id) SELECT 1, id FROM permissions;

INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES
(1, 'admin@honda-nt.example',     'Quản Trị Hệ Thống', '0900000001', 'staff',    NULL, '$2b$12$placeholder'),
(2, 'minh.nv@honda-nt.example',   'Nguyễn Văn Minh',   '0900000002', 'staff',    1,    '$2b$12$placeholder'),
(3, 'lan.tt@honda-nt.example',    'Trần Thị Lan',      '0900000003', 'staff',    1,    '$2b$12$placeholder'),
(4, 'bao.lq@honda-nt.example',    'Lê Quốc Bảo',       '0900000004', 'staff',    2,    '$2b$12$placeholder'),
(5, 'hung.pv@honda-nt.example',   'Phạm Văn Hùng',     '0900000005', 'staff',    1,    '$2b$12$placeholder'),
(6, 'hoa.vt@honda-nt.example',    'Võ Thị Hoa',        '0900000006', 'staff',    NULL, '$2b$12$placeholder'),
(7, 'mkt@honda-nt.example',       'Đặng Thu Marketing','0900000007', 'staff',    NULL, '$2b$12$placeholder'),
(8, 'mai.nt@example.com',         'Nguyễn Thị Mai',    '0911111111', 'customer', NULL, '$2b$12$placeholder'),
(9, 'nam.tv@example.com',         'Trần Văn Nam',      '0922222222', 'customer', NULL, '$2b$12$placeholder');

INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES
(1, 1, NULL, 1),
(2, 2, 1,    1),    -- quản lý chỉ trong NT01
(3, 3, 1,    2),    -- sales NT01
(4, 3, 2,    1),    -- sales NT02
(5, 4, 1,    2),    -- kỹ thuật NT01
(6, 5, NULL, 1),    -- kế toán toàn hệ thống
(7, 6, NULL, 1),
(8, 7, NULL, 1),
(9, 7, NULL, 1);

-- =====================================================================
-- 5. DỮ LIỆU MẪU: SẢN PHẨM, TỒN KHO, ĐƠN HÀNG (giá giả lập)
-- =====================================================================

INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES
(1,  'Wave Alpha 110',  'xe_so',   110, 1.6, 'Xe số phổ thông, bền bỉ, tiết kiệm nhiên liệu.'),
(2,  'Blade 110',       'xe_so',   110, 1.7, 'Xe số thiết kế thể thao, phù hợp đi làm hằng ngày.'),
(3,  'Future 125 FI',   'xe_so',   125, 1.6, 'Xe số cao cấp, phun xăng điện tử.'),
(4,  'Vision 110',      'tay_ga',  110, 1.8, 'Tay ga nhỏ gọn, cốp rộng, phù hợp đi phố.'),
(5,  'Lead 125',        'tay_ga',  125, 2.0, 'Tay ga cốp cực rộng, yên thấp.'),
(6,  'Air Blade 160',   'tay_ga',  160, 2.3, 'Tay ga thể thao, động cơ 160cc.'),
(7,  'SH Mode 125',     'tay_ga',  125, 2.1, 'Tay ga thời trang, thiết kế sang trọng.'),
(8,  'SH 160i',         'tay_ga',  160, 2.3, 'Tay ga cao cấp, phanh ABS, khóa thông minh.'),
(9,  'Winner X',        'con_tay', 150, 2.0, 'Xe côn tay thể thao 150cc.'),
(10, 'Vario 160',       'tay_ga',  160, 2.2, 'Tay ga thể thao, thiết kế mạnh mẽ.');

INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES
(1,  1,  'Wave Alpha 110 - Đen',            18900000, 17200000),
(2,  2,  'Blade 110 - Đỏ đen',              19800000, 18000000),
(3,  3,  'Future 125 FI - Xanh đen',        31000000, 28300000),
(4,  4,  'Vision 110 - Tiêu chuẩn - Trắng', 31500000, 28800000),
(5,  5,  'Lead 125 - Cao cấp - Xám',        40500000, 37000000),
(6,  6,  'Air Blade 160 - Đặc biệt - Đen',  57500000, 52500000),
(7,  7,  'SH Mode 125 - Thể thao - Đỏ',     66000000, 60500000),
(8,  8,  'SH 160i - Cao cấp - Đen',         96500000, 89000000),
(9,  9,  'Winner X - Thể thao - Xanh',      50000000, 45500000),
(10, 10, 'Vario 160 - Đặc biệt - Xám',      52500000, 48000000);

INSERT INTO inventory (branch_id, variant_id, quantity) VALUES
(1, 1, 12), (1, 4, 8),  (1, 6, 5),  (1, 8, 2),  (1, 9, 4),
(2, 2, 10), (2, 5, 6),  (2, 7, 3),  (2, 8, 0),  (2, 10, 7),
(3, 1, 6),  (3, 3, 4),  (3, 4, 9);

INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES
(1, 1, 8, 3, 2,    'delivered', 500000,  '2026-09-20 10:15:00'),
(2, 1, 9, 3, NULL, 'pending',   1500000, '2026-10-10 14:30:00'),
(3, 2, 8, 4, NULL, 'pending',   0,       '2026-10-12 09:00:00');

INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES
(1, 4, 1, 31500000),
(2, 8, 1, 96500000),
(3, 5, 1, 40500000);

-- =====================================================================
-- 6. DỮ LIỆU MẪU: CHATBOT
-- =====================================================================

INSERT INTO kb_categories (id, code, name, required_permission_id) VALUES
(1, 'public',    'Thông tin công khai',        2),
(2, 'sales',     'Nghiệp vụ bán hàng nội bộ',  3),
(3, 'technical', 'Kỹ thuật & bảo dưỡng',       4),
(4, 'finance',   'Tài chính & kế toán',        5),
(5, 'internal',  'Quy định nội bộ',            6);

INSERT INTO kb_documents (id, category_id, branch_id, title, content) VALUES
(1, 1, NULL, 'Bảng giá niêm yết Honda (mô phỏng)',
   'Giá niêm yết tham khảo: Wave Alpha 110 từ 18,9 triệu; Vision 110 từ 31,5 triệu; Air Blade 160 từ 57,5 triệu; SH 160i từ 96,5 triệu. Giá chưa gồm thuế trước bạ và phí đăng ký.'),
(2, 1, NULL, 'Thủ tục mua xe trả thẳng',
   'Khách mang CCCD bản gốc. Đại lý hỗ trợ đăng ký biển số trong 7-10 ngày làm việc. Có thể thanh toán tiền mặt hoặc chuyển khoản.'),
(3, 1, NULL, 'Mua xe trả góp',
   'Trả trước từ 10-30% tùy mẫu xe, kỳ hạn 6-36 tháng. Cần CCCD và giấy tờ chứng minh thu nhập. Chương trình phụ thuộc công ty tài chính đối tác.'),
(4, 1, NULL, 'Lịch bảo dưỡng định kỳ',
   'Bảo dưỡng lần đầu sau 1.000 km hoặc 1 tháng; các lần sau mỗi 2.000 km hoặc 3 tháng, tùy điều kiện nào đến trước. (Số liệu mô phỏng.)'),
(5, 1, 1,    'Khuyến mãi tháng 10 - Chi nhánh NT01',
   'Tặng mũ bảo hiểm và 1 lần bảo dưỡng miễn phí khi mua Vision 110 hoặc Lead 125 tại NT01 trong tháng 10.'),
(6, 2, NULL, 'Khung chiết khấu cho nhân viên bán hàng',
   'Nhân viên được giảm tối đa 1.000.000đ/xe. Vượt mức này phải được quản lý chi nhánh duyệt. Không tiết lộ khung chiết khấu cho khách.'),
(7, 2, NULL, 'Kịch bản tư vấn SH 160i',
   'Nhấn mạnh phanh ABS, khóa thông minh, giá trị bán lại cao. So sánh với đối thủ cùng phân khúc, tránh chê bai đối thủ.'),
(8, 3, NULL, 'Quy trình kiểm tra hệ thống phun xăng PGM-FI',
   'Bước 1: đọc mã lỗi qua số lần nhấp nháy đèn MIL. Bước 2: kiểm tra cảm biến và giắc cắm. Bước 3: xóa mã lỗi và chạy thử. (Nội dung mô phỏng.)'),
(9, 3, NULL, 'Chính sách bảo hành',
   'Bảo hành 3 năm hoặc 30.000 km tùy điều kiện nào đến trước. Không bảo hành hư hỏng do va chạm, ngập nước, tự ý độ chế.'),
(10, 4, NULL, 'Quy trình hoàn tiền đặt cọc',
   'Hoàn cọc trong 7 ngày làm việc nếu hủy trước khi xe về đại lý. Sau thời điểm đó khấu trừ 5% phí xử lý. Kế toán là người duyệt chi.'),
(11, 5, NULL, 'Quy chế làm việc và nghỉ phép',
   'Nhân viên nghỉ phép nộp đơn trước 3 ngày làm việc cho quản lý trực tiếp. (Nội dung mô phỏng.)');

INSERT INTO chatbot_intents (id, code, description, required_permission_id, data_source) VALUES
(1, 'ask_price_list',        'Hỏi giá niêm yết, thông số xe',            2,  'product_variants(list_price)'),
(2, 'ask_promotion',         'Hỏi khuyến mãi, thủ tục mua xe',           2,  'kb_documents[public]'),
(3, 'ask_stock',             'Hỏi tồn kho theo chi nhánh',               7,  'inventory'),
(4, 'ask_order_status',      'Tra cứu tình trạng đơn hàng',              8,  'orders'),
(5, 'ask_customer_info',     'Tra cứu thông tin khách hàng',             11, 'users[customer]'),
(6, 'ask_sales_policy',      'Hỏi chiết khấu, kịch bản tư vấn',          3,  'kb_documents[sales]'),
(7, 'ask_tech_procedure',    'Hỏi quy trình kỹ thuật, mã lỗi',           4,  'kb_documents[technical]'),
(8, 'ask_cost_margin',       'Hỏi giá vốn, biên lợi nhuận',              12, 'product_variants(cost_price)'),
(9, 'ask_finance_procedure', 'Hỏi quy trình tài chính, hoàn tiền',       5,  'kb_documents[finance]'),
(10,'ask_hr_policy',         'Hỏi quy định nhân sự nội bộ',              6,  'kb_documents[internal]'),
(11,'view_audit_log',        'Xem nhật ký chatbot',                      15, 'chatbot_audit_log');

INSERT INTO chat_sessions (id, user_id, channel, started_at) VALUES
(1, NULL, 'web',          '2026-10-13 08:00:00'),   -- khách vãng lai
(2, 8,    'zalo',         '2026-10-13 08:10:00'),   -- khách hàng Mai
(3, 3,    'internal_app', '2026-10-13 08:20:00'),   -- sales Lan
(4, 5,    'internal_app', '2026-10-13 08:30:00');   -- kỹ thuật Hùng

INSERT INTO chat_messages (session_id, sender, content, detected_intent_id, created_at) VALUES
(1, 'user', 'SH 160i giá bao nhiêu vậy shop?',                1, '2026-10-13 08:00:10'),
(1, 'user', 'Giá vốn SH 160i của shop là bao nhiêu?',         8, '2026-10-13 08:01:00'),
(2, 'user', 'Đơn hàng của mình đến đâu rồi?',                 4, '2026-10-13 08:10:20'),
(3, 'user', 'Chiết khấu tối đa cho khách mua Vision là bao nhiêu?', 6, '2026-10-13 08:20:15'),
(3, 'user', 'Mẫu SH 160i còn hàng ở chi nhánh 2 không?',      3, '2026-10-13 08:21:00'),
(4, 'user', 'Cách đọc mã lỗi PGM-FI trên Air Blade?',         7, '2026-10-13 08:30:30'),
(4, 'user', 'Giá vốn của Air Blade 160?',                     8, '2026-10-13 08:31:00');

INSERT INTO chatbot_audit_log (session_id, user_id, intent_id, decision, reason, created_at) VALUES
(1, NULL, 1, 'allowed', 'guest có kb:public:read',            '2026-10-13 08:00:10'),
(1, NULL, 8, 'denied',  'thiếu quyền price:cost:read',        '2026-10-13 08:01:00'),
(2, 8,    4, 'allowed', 'chỉ trả đơn của chính khách hàng',   '2026-10-13 08:10:20'),
(3, 3,    6, 'allowed', 'sales_staff có kb:sales:read',       '2026-10-13 08:20:15'),
(3, 3,    3, 'allowed', 'sales_staff có inventory:read',      '2026-10-13 08:21:00'),
(4, 5,    7, 'allowed', 'technician có kb:technical:read',    '2026-10-13 08:30:30'),
(4, 5,    8, 'denied',  'thiếu quyền price:cost:read',        '2026-10-13 08:31:00');

-- =====================================================================
-- 7. VIEW HỖ TRỢ
-- =====================================================================

-- Mọi permission hiệu lực của từng user (kèm phạm vi chi nhánh)
CREATE VIEW v_user_permissions AS
SELECT ur.user_id, u.full_name, r.name AS role_name, p.code AS permission_code,
       ur.scope_branch_id
FROM user_roles ur
JOIN users u            ON u.id = ur.user_id
JOIN roles r            ON r.id = ur.role_id
JOIN role_permissions rp ON rp.role_id = ur.role_id
JOIN permissions p       ON p.id = rp.permission_id;

-- Tài liệu KB mà từng user được phép đọc (đã xét permission + chi nhánh)
CREATE VIEW v_user_kb_access AS
SELECT DISTINCT vup.user_id, d.id AS doc_id, d.title, c.code AS category
FROM v_user_permissions vup
JOIN permissions p   ON p.code = vup.permission_code
JOIN kb_categories c ON c.required_permission_id = p.id
JOIN kb_documents d  ON d.category_id = c.id
WHERE d.branch_id IS NULL
   OR vup.scope_branch_id IS NULL
   OR d.branch_id = vup.scope_branch_id;

-- =====================================================================
-- 8. TRUY VẤN MẪU MÔ PHỎNG LUỒNG CHATBOT
-- =====================================================================

-- 8.1 Liệt kê quyền của một user (ví dụ: sales Lan, id=3)
SELECT DISTINCT permission_code FROM v_user_permissions WHERE user_id = 3;

-- 8.2 Kiểm tra intent: user có được phép hỏi 'ask_cost_margin' không?
--     (trả 1 = allowed, 0 = denied). Thử với user 3 (sales) và 6 (kế toán).
SELECT EXISTS (
  SELECT 1
  FROM chatbot_intents ci
  JOIN permissions p ON p.id = ci.required_permission_id
  JOIN v_user_permissions vup ON vup.permission_code = p.code
  WHERE ci.code = 'ask_cost_margin' AND vup.user_id = 3
) AS is_allowed;

-- 8.3 RAG retrieval có lọc quyền: chỉ lấy tài liệu user được đọc,
--     rồi mới đưa vào context của LLM (ví dụ từ khóa "chiết khấu", user = 3)
-- (Demo dùng LIKE; thực tế thay bằng FULLTEXT hoặc vector search)
SELECT d.id, d.title, d.content
FROM kb_documents d
JOIN v_user_kb_access a ON a.doc_id = d.id
WHERE a.user_id = 3
  AND (d.title LIKE '%chiết khấu%' OR d.content LIKE '%chiết khấu%');

-- 8.4 Khách vãng lai (guest, không có user_id): chỉ thấy tài liệu public
SELECT d.id, d.title
FROM kb_documents d
JOIN kb_categories c ON c.id = d.category_id
JOIN role_permissions rp ON rp.permission_id = c.required_permission_id
JOIN roles r ON r.id = rp.role_id AND r.name = 'guest'
WHERE d.branch_id IS NULL;

-- 8.5 Tồn kho theo phạm vi chi nhánh:
--     user có scope = NULL thấy tất cả, ngược lại chỉ thấy chi nhánh của mình
SELECT b.code AS branch, p.model_name, pv.variant_name, i.quantity
FROM inventory i
JOIN branches b          ON b.id = i.branch_id
JOIN product_variants pv ON pv.id = i.variant_id
JOIN products p          ON p.id = pv.product_id
WHERE EXISTS (
  SELECT 1 FROM v_user_permissions vup
  WHERE vup.user_id = 3 AND vup.permission_code = 'inventory:read'
    AND (vup.scope_branch_id IS NULL OR vup.scope_branch_id = i.branch_id)
);

-- 8.6 Khách hàng chỉ xem đơn của chính mình (row-level security, user = 8)
SELECT o.id, o.status, o.created_at
FROM orders o
WHERE o.customer_id = 8;

-- 8.7 Giá vốn: chỉ trả về nếu có price:cost:read (user 6 = kế toán thì có dữ liệu)
SELECT pv.variant_name, pv.list_price, pv.cost_price,
       pv.list_price - pv.cost_price AS gross_margin
FROM product_variants pv
WHERE EXISTS (
  SELECT 1 FROM v_user_permissions
  WHERE user_id = 6 AND permission_code = 'price:cost:read'
);

-- 8.8 Ghi audit log khi bị từ chối (mẫu INSERT mà backend sẽ gọi)
INSERT INTO chatbot_audit_log (session_id, user_id, intent_id, decision, reason)
VALUES (1, NULL, 8, 'denied', 'thiếu quyền price:cost:read');

-- 8.9 Thống kê số lần bị từ chối theo intent (phát hiện hành vi dò quyền)
SELECT ci.code AS intent, COUNT(*) AS denied_count
FROM chatbot_audit_log l
JOIN chatbot_intents ci ON ci.id = l.intent_id
WHERE l.decision = 'denied'
GROUP BY ci.code
ORDER BY denied_count DESC;

-- 8.10 Kiểm thử Separation of Duties: lệnh này PHẢI báo lỗi CHECK constraint
-- UPDATE orders SET approved_by = 3 WHERE id = 2;   -- Lan tạo đơn 2, không được tự duyệt
-- Duyệt hợp lệ bởi quản lý (id=2):
UPDATE orders SET approved_by = 2, status = 'approved' WHERE id = 2;


CREATE TABLE customer_profiles (
  user_id INT PRIMARY KEY,
  customer_code VARCHAR(30) UNIQUE NOT NULL,
  gender VARCHAR(20), birth_date DATE, province VARCHAR(80), district VARCHAR(80),
  address VARCHAR(255), occupation VARCHAR(100), lead_source VARCHAR(50),
  interested_product_id INT NULL, payment_preference VARCHAR(30),
  registered_at DATE, status VARCHAR(40) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (interested_product_id) REFERENCES products(id)
);
INSERT INTO customer_profiles
(user_id, customer_code, gender, birth_date, province, district, address, occupation,
 lead_source, interested_product_id, payment_preference, registered_at, status) VALUES
(8, 'TEST-KH-001', 'Nữ', '1990-01-01', 'Khánh Hòa', 'Nha Trang', 'Địa chỉ synthetic 1', 'Nhân viên', 'Website', 8, 'Trả thẳng', '2026-01-01', 'Đã mua'),
(9, 'TEST-KH-002', 'Nam', '1992-02-02', 'Khánh Hòa', 'Cam Ranh', 'Địa chỉ synthetic 2', 'Kỹ thuật', 'Hotline', 6, 'Trả góp', '2026-01-02', 'Tiềm năng');

USE honda_chatbot_test;
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


USE honda_chatbot_test;

-- Tạo FULLTEXT index cho RAG bằng ngram; kiểm tra trước để chạy lại không lỗi.
SET @index_exists = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'kb_documents'
      AND INDEX_NAME = 'ft_kb_documents_title_content'
);
SET @sql = IF(
    @index_exists = 0,
    IF(VERSION() LIKE '%MariaDB%',
       'ALTER TABLE kb_documents ADD FULLTEXT INDEX ft_kb_documents_title_content (title, content)',
       'ALTER TABLE kb_documents ADD FULLTEXT INDEX ft_kb_documents_title_content (title, content) WITH PARSER ngram'),
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Index lọc đơn hàng theo khách hàng.
SET @index_exists = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'orders'
      AND INDEX_NAME = 'idx_orders_customer_id'
);
SET @sql = IF(
    @index_exists = 0,
    'CREATE INDEX idx_orders_customer_id ON orders (customer_id)',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Index lọc đơn hàng theo chi nhánh và trạng thái.
SET @index_exists = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'orders'
      AND INDEX_NAME = 'idx_orders_branch_status'
);
SET @sql = IF(
    @index_exists = 0,
    'CREATE INDEX idx_orders_branch_status ON orders (branch_id, status)',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- Mở rộng thuộc tính đăng nhập, phạm vi quyền và nhật ký quản trị động.
USE honda_chatbot_test;
-- Bổ sung trạng thái khóa tài khoản và thông tin đăng nhập gần nhất.
ALTER TABLE users ADD last_login_at DATETIME NULL,
 ADD failed_login_count INT NOT NULL DEFAULT 0, ADD locked_until DATETIME NULL,
 ADD must_change_password BOOLEAN NOT NULL DEFAULT FALSE, ADD password_updated_at DATETIME NULL;
ALTER TABLE roles ADD is_system BOOLEAN NOT NULL DEFAULT FALSE,
-- Ghi nhận phạm vi dữ liệu và thời hạn gán vai trò.
 ADD is_active BOOLEAN NOT NULL DEFAULT TRUE,
 ADD landing_path VARCHAR(100) NOT NULL DEFAULT '/dashboard', ADD priority INT NOT NULL DEFAULT 100;
ALTER TABLE role_permissions ADD data_scope ENUM('all','branch','own') NOT NULL DEFAULT 'all';
ALTER TABLE user_roles ADD expires_at DATETIME NULL;
UPDATE roles SET is_system=TRUE WHERE name IN ('super_admin','branch_manager','sales_staff','technician','accountant','marketing','customer','guest');
-- Tạo nhật ký thay đổi RBAC để truy vết thao tác quản trị.
UPDATE roles SET landing_path='/chat' WHERE name IN ('customer','guest');
UPDATE roles SET priority=id*10;
UPDATE role_permissions rp JOIN roles r ON r.id=rp.role_id
SET rp.data_scope=CASE WHEN r.name IN ('sales_staff','technician','branch_manager') THEN 'branch' WHEN r.name='customer' THEN 'own' ELSE 'all' END;
CREATE TABLE rbac_audit_log (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, actor_user_id INT NULL, action VARCHAR(80) NOT NULL,
-- Cập nhật các quyền bổ sung cho dashboard và quản trị RBAC.
 target_type VARCHAR(40) NOT NULL, target_id INT NULL, before_json JSON NULL, after_json JSON NULL,
 ip_address VARCHAR(45) NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX ix_rbac_audit_created(created_at), FOREIGN KEY(actor_user_id) REFERENCES users(id)
);
CREATE TABLE rbac_meta(id TINYINT PRIMARY KEY, version INT NOT NULL);
INSERT INTO rbac_meta VALUES(1,1);
INSERT INTO permissions(code,description) VALUES
 ('dashboard:view','Voir dashboard / Xem tổng quan'),('dashboard:finance','Xem tài chính trên dashboard'),('rbac:manage','Quản trị vai trò và quyền');
INSERT INTO role_permissions(role_id,permission_id,data_scope)
SELECT r.id,p.id,CASE WHEN r.name IN ('branch_manager','sales_staff','technician') THEN 'branch' ELSE 'all' END
FROM roles r JOIN permissions p ON p.code='dashboard:view'
-- Tạo các view quyền dùng chung cho kiểm tra truy cập và tài liệu.
WHERE r.name IN ('super_admin','branch_manager','sales_staff','technician','accountant','marketing');
INSERT INTO role_permissions(role_id,permission_id,data_scope)
SELECT r.id,p.id,'all' FROM roles r JOIN permissions p ON p.code='dashboard:finance' WHERE r.name IN ('super_admin','accountant');
INSERT INTO role_permissions(role_id,permission_id,data_scope)
SELECT r.id,p.id,'all' FROM roles r JOIN permissions p ON p.code='rbac:manage' WHERE r.name='super_admin';
CREATE OR REPLACE VIEW v_user_permissions AS
SELECT u.id AS user_id,r.name AS role_name,p.code AS permission_code,
 CASE WHEN r.name='super_admin' OR rp.data_scope='all' THEN NULL
      WHEN rp.data_scope='branch' THEN COALESCE(ur.scope_branch_id,u.home_branch_id) ELSE NULL END AS scope_branch_id,
 CASE WHEN r.name='super_admin' THEN 'all' ELSE rp.data_scope END AS data_scope
FROM users u JOIN user_roles ur ON ur.user_id=u.id JOIN roles r ON r.id=ur.role_id
JOIN permissions p ON r.name='super_admin' OR EXISTS (SELECT 1 FROM role_permissions rp2 WHERE rp2.role_id=r.id AND rp2.permission_id=p.id)
LEFT JOIN role_permissions rp ON rp.role_id=r.id AND rp.permission_id=p.id
WHERE u.is_active=TRUE AND r.is_active=TRUE AND (ur.expires_at IS NULL OR ur.expires_at>NOW());
CREATE OR REPLACE VIEW v_user_kb_access AS
SELECT DISTINCT vp.user_id,d.id AS doc_id,d.title,c.code AS category
FROM v_user_permissions vp JOIN permissions p ON p.code=vp.permission_code
JOIN kb_categories c ON c.required_permission_id=p.id JOIN kb_documents d ON d.category_id=c.id
WHERE d.branch_id IS NULL OR vp.data_scope='all' OR (vp.data_scope='branch' AND d.branch_id=vp.scope_branch_id);
-- Khai báo các mục điều hướng cùng quyền bắt buộc tương ứng.
CREATE TABLE nav_items (
 code VARCHAR(50) PRIMARY KEY,label VARCHAR(100) NOT NULL,path VARCHAR(100) NOT NULL,
 required_permission_id INT NULL,sort_order INT NOT NULL DEFAULT 100,is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
 FOREIGN KEY(required_permission_id) REFERENCES permissions(id)
);
INSERT INTO nav_items(code,label,path,required_permission_id,sort_order,is_enabled)
SELECT v.code,v.label,v.path,p.id,v.ord,v.enabled FROM (
 SELECT 'dashboard' code,'Tổng quan' label,'/dashboard' path,'dashboard:view' perm,10 ord,1 enabled
 UNION ALL SELECT 'chat','Trợ lý AI','/chat','kb:public:read',20,1
 UNION ALL SELECT 'customers','Khách hàng','/customers','customer:read',30,1
 UNION ALL SELECT 'inventory','Tồn kho','/inventory','inventory:read',40,1
 UNION ALL SELECT 'revenue','Doanh thu','/dashboard#revenue','order:read',50,1
 UNION ALL SELECT 'quotes','Báo giá','/quotes','order:read',60,0
 UNION ALL SELECT 'opportunities','Cơ hội','/opportunities','order:read',70,0
 UNION ALL SELECT 'bookings','Đặt lịch','/bookings','kb:public:read',80,0
 UNION ALL SELECT 'users','Tài khoản','/admin/users','user:manage',100,1
 UNION ALL SELECT 'roles','Vai trò','/admin/roles','rbac:manage',110,1
 UNION ALL SELECT 'permissions','Quyền','/admin/permissions','rbac:manage',120,1
 UNION ALL SELECT 'audit','Nhật ký','/admin/audit','audit:read',130,1
) v JOIN permissions p ON p.code=v.perm;

