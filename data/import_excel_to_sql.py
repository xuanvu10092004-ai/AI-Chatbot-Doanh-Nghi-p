#!/usr/bin/env python3
"""
Đọc honda_dataset_khach_hang_san_pham.xlsx và sinh ra honda_import_data.sql
để nạp vào CSDL `honda_chatbot` (đã tạo bằng honda_chatbot_rbac.sql).

Cách dùng:
    pip install pandas openpyxl
    python import_excel_to_sql.py [file.xlsx] [out.sql]

Sau đó chạy:
    mysql -u root -p --default-character-set=utf8mb4 < honda_import_data.sql

Ánh xạ:
    Excel San_pham   -> products, product_variants, product_specs (bảng mới)
    Excel Ton_kho    -> inventory
    Excel Khach_hang -> users (+ user_roles role customer), customer_profiles (bảng mới), orders, order_items
Các cột công thức (Tuổi, Giá trị mua, Lợi nhuận, Tồn kho tổng) là dữ liệu dẫn xuất nên KHÔNG nạp.
"""
import sys
import datetime as dt
import pandas as pd

XLSX = sys.argv[1] if len(sys.argv) > 1 else "honda_dataset_khach_hang_san_pham.xlsx"
OUT = sys.argv[2] if len(sys.argv) > 2 else "honda_import_data.sql"

BRANCH_ID = {"NT01": 1, "NT02": 2, "CR01": 3}                 # khớp bảng branches
SEGMENT = {"Xe số": "xe_so", "Tay ga": "tay_ga", "Côn tay": "con_tay"}
CUSTOMER_ROLE_ID = 7                                           # role 'customer'
SALES_BY_BRANCH = {"NT01": 3, "NT02": 4, "CR01": 3}            # user tạo đơn (sales_staff)
APPROVER_ID = 2                                                # branch_manager duyệt đơn
USER_ID_OFFSET = 100                                           # KH0001 -> users.id = 101
TODAY = dt.date(2026, 10, 12)

DESCRIPTIONS = {
    "Wave Alpha 110": "Xe số phổ thông, bền bỉ, tiết kiệm nhiên liệu.",
    "Blade 110": "Xe số thiết kế thể thao, phù hợp đi làm hằng ngày.",
    "Future 125 FI": "Xe số cao cấp, phun xăng điện tử.",
    "Vision 110": "Tay ga nhỏ gọn, cốp rộng, phù hợp đi phố.",
    "Lead 125": "Tay ga cốp cực rộng, yên thấp.",
    "Air Blade 160": "Tay ga thể thao, động cơ 160cc.",
    "SH Mode 125": "Tay ga thời trang, thiết kế sang trọng.",
    "SH 160i": "Tay ga cao cấp, phanh ABS, khóa thông minh.",
    "Winner X": "Xe côn tay thể thao 150cc.",
    "Vario 160": "Tay ga thể thao, thiết kế mạnh mẽ.",
}


def q(v):
    """Chuyển giá trị Python thành literal SQL an toàn."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
        return "NULL"
    if isinstance(v, (pd.Timestamp, dt.datetime)):
        return "'" + v.strftime("%Y-%m-%d") + "'"
    if isinstance(v, dt.date):
        return "'" + v.isoformat() + "'"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(int(v)) if float(v).is_integer() else repr(float(v))
    s = str(v).replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


# ------------------------------------------------------------------ đọc Excel
sp = pd.read_excel(XLSX, "San_pham")
tk = pd.read_excel(XLSX, "Ton_kho")
kh = pd.read_excel(XLSX, "Khach_hang", dtype={"Số điện thoại": str})

tk = tk[tk["Mã SP"].astype(str).str.startswith("SP")]          # bỏ dòng "Tổng"
sp = sp[sp["Mã SP"].astype(str).str.startswith("SP")]

# products: mỗi mẫu xe duy nhất 1 dòng, id theo thứ tự xuất hiện
model_names = list(dict.fromkeys(sp["Mẫu xe"]))
product_id = {name: i for i, name in enumerate(model_names, 1)}
first_row = sp.drop_duplicates("Mẫu xe").set_index("Mẫu xe")
price_by_sku = dict(zip(sp["Mã SP"], sp["Giá niêm yết (VNĐ)"]))
model_by_sku = dict(zip(sp["Mã SP"], sp["Mẫu xe"]))


def vid(code):
    return int(code[2:])                                        # SP012 -> 12


L = []
w = L.append
w("-- Sinh tự động bởi import_excel_to_sql.py - dữ liệu giả lập")
w("USE honda_chatbot;")
w("SET NAMES utf8mb4;\n")

# ------------------------------------------------------------------ bảng bổ sung
w("""CREATE TABLE IF NOT EXISTS product_specs (
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
""")

# ------------------------------------------------------------------ dọn dữ liệu mẫu cũ (chạy lại an toàn)
w("START TRANSACTION;")
w("-- Xóa dữ liệu nghiệp vụ mẫu từ file schema và dữ liệu đã nạp lần trước")
for stmt in [
    "DELETE FROM order_items;", "DELETE FROM orders;", "DELETE FROM inventory;",
    "DELETE FROM customer_profiles;", "DELETE FROM product_specs;",
    "DELETE FROM product_variants;", "DELETE FROM products;",
    f"DELETE FROM user_roles WHERE user_id > {USER_ID_OFFSET};",
    f"DELETE FROM users WHERE id > {USER_ID_OFFSET};",
]:
    w(stmt)
w("")

# ------------------------------------------------------------------ products / specs / variants
w("-- products")
for name, pid in product_id.items():
    r = first_row.loc[name]
    w("INSERT INTO products (id, model_name, segment, engine_cc, fuel_consumption_l100km, description) VALUES "
      f"({pid}, {q(name)}, {q(SEGMENT[r['Phân khúc']])}, {round(float(r['Dung tích (cc)']))}, "
      f"{q(float(r['Tiêu hao (L/100km)']))}, {q(DESCRIPTIONS.get(name))});")
w("\n-- product_specs")
for name, pid in product_id.items():
    r = first_row.loc[name]
    w("INSERT INTO product_specs (product_id, engine_type, fuel_tank_l, weight_kg, brake_type, warranty) VALUES "
      f"({pid}, {q(r['Loại động cơ'])}, {q(float(r['Dung tích bình xăng (L)']))}, {int(r['Khối lượng (kg)'])}, "
      f"{q(r['Phanh'])}, {q(r['Bảo hành'])});")
w("\n-- product_variants")
for _, r in sp.iterrows():
    variant_name = f"{r['Mẫu xe']} - {r['Phiên bản']} - {r['Màu sắc']}"
    w("INSERT INTO product_variants (id, product_id, variant_name, list_price, cost_price) VALUES "
      f"({vid(r['Mã SP'])}, {product_id[r['Mẫu xe']]}, {q(variant_name)}, "
      f"{int(r['Giá niêm yết (VNĐ)'])}, {int(r['Giá vốn (VNĐ)'])});")

# ------------------------------------------------------------------ inventory
w("\n-- inventory")
for _, r in tk.iterrows():
    for code in ("NT01", "NT02", "CR01"):
        w("INSERT INTO inventory (branch_id, variant_id, quantity) VALUES "
          f"({BRANCH_ID[code]}, {vid(r['Mã SP'])}, {int(r[code])});")

# ------------------------------------------------------------------ users / roles / profiles
w("\n-- users (khách hàng)")
uid = lambda ma_kh: USER_ID_OFFSET + int(ma_kh[2:])             # KH0001 -> 101
for _, r in kh.iterrows():
    w("INSERT INTO users (id, email, full_name, phone, user_type, home_branch_id, password_hash) VALUES "
      f"({uid(r['Mã KH'])}, {q(r['Email'])}, {q(r['Họ và tên'])}, {q(str(r['Số điện thoại']))}, "
      f"'customer', {BRANCH_ID[r['Chi nhánh phụ trách']]}, '$2b$12$placeholder');")

w("\n-- user_roles: gán role customer")
for _, r in kh.iterrows():
    w("INSERT INTO user_roles (user_id, role_id, scope_branch_id, granted_by) VALUES "
      f"({uid(r['Mã KH'])}, {CUSTOMER_ROLE_ID}, NULL, 1);")

w("\n-- customer_profiles")
for _, r in kh.iterrows():
    w("INSERT INTO customer_profiles (user_id, customer_code, gender, birth_date, province, district, address, "
      "occupation, lead_source, interested_product_id, payment_preference, registered_at, status) VALUES "
      f"({uid(r['Mã KH'])}, {q(r['Mã KH'])}, {q(r['Giới tính'])}, {q(r['Ngày sinh'])}, {q(r['Tỉnh/Thành phố'])}, "
      f"{q(r['Quận/Huyện'])}, {q(r['Địa chỉ'])}, {q(r['Nghề nghiệp'])}, {q(r['Nguồn khách'])}, "
      f"{product_id[r['Mẫu xe quan tâm']]}, {q(r['Hình thức thanh toán'])}, {q(r['Ngày đăng ký'])}, {q(r['Trạng thái'])});")

# ------------------------------------------------------------------ orders cho khách "Đã mua"
w("\n-- orders + order_items (từ khách có trạng thái Đã mua)")
bought = kh[kh["Mã SP đã mua"].notna()].reset_index(drop=True)
for i, r in bought.iterrows():
    oid = i + 1
    sku = r["Mã SP đã mua"]
    branch = r["Chi nhánh phụ trách"]
    created = min(pd.Timestamp(r["Ngày đăng ký"]).date() + dt.timedelta(days=3), TODAY)
    discount = (0, 0, 500000, 1000000)[i % 4]
    w("INSERT INTO orders (id, branch_id, customer_id, created_by, approved_by, status, discount_amount, created_at) VALUES "
      f"({oid}, {BRANCH_ID[branch]}, {uid(r['Mã KH'])}, {SALES_BY_BRANCH[branch]}, {APPROVER_ID}, "
      f"'delivered', {discount}, '{created.isoformat()} 10:00:00');")
    w("INSERT INTO order_items (order_id, variant_id, quantity, unit_price) VALUES "
      f"({oid}, {vid(sku)}, 1, {int(price_by_sku[sku])});")

w("\nCOMMIT;")

# ------------------------------------------------------------------ kiểm tra nhanh sau khi nạp
w("""
-- Kiểm tra số dòng sau khi nạp (kỳ vọng: 10 / 28 / 84 / 80 / 80 / số khách 'Đã mua')
SELECT 'products' AS tbl, COUNT(*) AS n FROM products
UNION ALL SELECT 'product_variants', COUNT(*) FROM product_variants
UNION ALL SELECT 'inventory', COUNT(*) FROM inventory
UNION ALL SELECT 'customers (users > 100)', COUNT(*) FROM users WHERE id > 100
UNION ALL SELECT 'customer_profiles', COUNT(*) FROM customer_profiles
UNION ALL SELECT 'orders', COUNT(*) FROM orders;""")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print(f"Đã ghi {OUT}: {len(model_names)} mẫu xe, {len(sp)} phiên bản, {len(tk)*3} dòng tồn kho, "
      f"{len(kh)} khách hàng, {len(bought)} đơn hàng")
