# ==========================================================
# Tên file: database_service.py
# Mục đích của file: Tầng dịch vụ truy xuất dữ liệu (Data Access Layer - DAL) cho ứng dụng Web.
# File này dùng để làm gì:
#   - Cung cấp các hàm hỗ trợ kết nối tới CSDL SQLite (`database.db`).
#   - Đếm số lượng bản ghi hiển thị thống kê tổng quan (Dashboard widgets).
#   - Truy vấn danh sách sản phẩm sắp hết hàng (tồn kho < 10) phục vụ cảnh báo kho.
#   - Truy vấn danh sách khách hàng tiềm năng, VIP, mới phục vụ hiển thị trên giao diện Dashboard.
# Khi nào file được gọi:
#   - Được gọi bởi các route trong app.py (`GET /api/dashboard`, `GET /api/low-stock`, `GET /api/potential-customers`).
# Luồng hoạt động tổng quát:
#   [Request GET từ REST API app.py]
#           ↓
#   [Mở kết nối CSDL via get_connection()]
#           ↓
#   [Thực thi câu lệnh SQL SELECT]
#           ↓
#   [Chuyển đổi kết quả Row object sang dict chuẩn]
#           ↓
#   [Đóng kết nối & Trả về dữ liệu cho app.py mã hóa JSON]
# ==========================================================

import sqlite3
from database_path import DATABASE_PATH

# ---------------------------------------------------------
# Hằng số tên file Cơ sở dữ liệu SQLite
# ---------------------------------------------------------
DB_NAME = str(DATABASE_PATH)


# ==========================================================
# Hàm get_connection:
# - Hàm dùng để làm gì: Tạo kết nối tới SQLite và thiết lập `row_factory = sqlite3.Row`.
# - Tham số đầu vào: Không có.
# - Giá trị trả về:
#     + conn (sqlite3.Connection): Đối tượng kết nối CSDL.
# - Hàm này được gọi ở đâu: Được gọi trong `get_count()`, `get_low_stock_products()`, `get_potential_customers()`.
# - Vai trò trong hệ thống: Hàm khởi tạo kết nối dùng chung (Connection Factory).
# ==========================================================
def get_connection():
    """
    Tạo và trả về kết nối đến database SQLite.
    row_factory = sqlite3.Row cho phép truy cập cột theo tên (row["name"]).
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Kết nối tới file database.db
    # - conn.row_factory = sqlite3.Row: Giúp truy cập các giá trị cột bằng tên chuỗi `row['name']` thay vì chỉ số số nguyên `row[0]`.
    # ---------------------------------------------------------
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================================
# Hàm get_count:
# - Hàm dùng để làm gì: Đếm tổng số dòng dữ liệu trong một bảng CSDL bất kỳ.
# - Tham số đầu vào:
#     + table_name (str): Tên bảng cần đếm bản ghi (VD: 'customers', 'inventory').
# - Giá trị trả về:
#     + int: Tổng số bản ghi thu được từ hàm đếm SQL COUNT(*).
# - Hàm này được gọi ở đâu: Được gọi bên trong hàm `get_dashboard_stats()`.
# - Vai trò trong hệ thống: Hàm tiện ích tính toán số liệu đếm tổng quát.
# ==========================================================
def get_count(table_name):
    """
    Đếm tổng số dòng dữ liệu trong một bảng.

    Args:
        table_name (str): Tên bảng cần đếm (vd: 'customers', 'inventory')

    Returns:
        int: Số lượng bản ghi trong bảng
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Lấy kết nối và tạo cursor
    # ---------------------------------------------------------
    conn = get_connection()
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # Câu lệnh SQL: SELECT COUNT(*) AS total FROM <table_name>
    # - Thao tác dùng để làm gì: Đếm số bản ghi trong bảng `table_name`.
    # - Ý nghĩa: `COUNT(*)` đếm tất cả các dòng, đặt tên cột trả về là `total`.
    # ---------------------------------------------------------
    cursor.execute(f"SELECT COUNT(*) AS total FROM {table_name}")
    result = cursor.fetchone()

    # ---------------------------------------------------------
    # Bước 2 trong hàm: Đóng kết nối và trả về kết quả integer
    # ---------------------------------------------------------
    conn.close()
    return result["total"]


# ==========================================================
# Hàm get_dashboard_stats:
# - Hàm dùng để làm gì: Tổng hợp số lượng bản ghi của tất cả 6 bảng chính trong CSDL.
# - Tham số đầu vào: Không có.
# - Giá trị trả về:
#     + dict: Từ khiển chứa số lượng của từng bảng với key tương ứng.
# - Hàm này được gọi ở đâu: app.py (route `GET /api/dashboard`).
# - Vai trò trong hệ thống: Cung cấp dữ liệu chỉ số KPI tổng quan cho trang Dashboard Web.
# ==========================================================
def get_dashboard_stats():
    """
    Lấy số liệu tổng quan cho trang Dashboard.
    Gọi get_count() cho từng bảng trong database.

    Returns:
        dict: Số lượng bản ghi của 6 bảng chính.
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Gọi get_count() lần lượt cho 6 bảng
    # - Dữ liệu đi từ đâu đến đâu: Gọi get_count -> Truy vấn SQL -> Ghép vào Dictionary.
    # ---------------------------------------------------------
    stats = {
        "customers": get_count("customers"),         # Số khách hàng
        "inventory": get_count("inventory"),         # Số sản phẩm trong kho
        "opportunities": get_count("opportunities"), # Số cơ hội bán hàng
        "quotes": get_count("quotes"),               # Số báo giá
        "documents": get_count("documents"),         # Số tài liệu nội bộ
        "chat_logs": get_count("chat_logs")          # Số lượt hội thoại
    }
    return stats


# ==========================================================
# Hàm get_low_stock_products:
# - Hàm dùng để làm gì: Truy vấn danh sách các sản phẩm có số lượng tồn kho thấp hơn 10 đơn vị.
# - Tham số đầu vào:
#     + limit (int): Số lượng sản phẩm tối đa trả về (mặc định = 5).
# - Giá trị trả về:
#     + list[dict]: Danh sách từ điển các sản phẩm chứa thông tin: product_name, category, quantity, unit, price.
# - Hàm này được gọi ở đâu: app.py (route `GET /api/low-stock`).
# - Vai trò trong hệ thống: Cung cấp dữ liệu danh sách widget sản phẩm cần nhập hàng bổ sung.
# ==========================================================
def get_low_stock_products(limit=5):
    """
    Lấy danh sách sản phẩm sắp hết hàng (quantity < 10),
    sắp xếp tăng dần theo tồn kho (ít nhất hiển thị trước).

    Args:
        limit (int): Số sản phẩm tối đa cần lấy (mặc định 5)

    Returns:
        list[dict]: Danh sách sản phẩm với key: product_name, category, quantity, unit, price
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # Câu lệnh SQL: SELECT product_name, category, quantity, unit, price FROM inventory WHERE quantity < 10 ORDER BY quantity ASC LIMIT ?
    # - Thao tác dùng để làm gì: Lọc danh sách mặt hàng có tồn kho < 10.
    # - Ý nghĩa từng điều kiện:
    #     + WHERE quantity < 10: Điều kiện lọc tồn kho thấp.
    #     + ORDER BY quantity ASC: Sắp xếp các sản phẩm có số lượng ít nhất lên trên cùng.
    #     + LIMIT ?: Giới hạn số dòng kết quả bằng biến truyền vào `limit` (sử dụng placeholder tuple `(limit,)` chống lỗi SQL Injection).
    # ---------------------------------------------------------
    cursor.execute("""
        SELECT product_name, category, quantity, unit, price
        FROM inventory
        WHERE quantity < 10
        ORDER BY quantity ASC
        LIMIT ?
    """, (limit,))  # Dùng placeholder (?) để tránh SQL Injection

    products = cursor.fetchall()
    conn.close()

    # ---------------------------------------------------------
    # Bước 2 trong hàm: Ép kiểu danh sách sqlite3.Row thành list[dict]
    # - Vòng lặp list comprehension `[dict(product) for product in products]` giúp chuyển đối tượng Row sang dict thuần của Python để Flask jsonify hỗ trợ chuyển sang JSON trả về cho Frontend.
    # ---------------------------------------------------------
    return [dict(product) for product in products]


# ==========================================================
# Hàm get_potential_customers:
# - Hàm dùng để làm gì: Lấy danh sách khách hàng thuộc phân loại 'potential', 'vip', hoặc 'new'.
# - Tham số đầu vào:
#     + limit (int): Số lượng bản ghi tối đa (mặc định = 5).
# - Giá trị trả về:
#     + list[dict]: Danh sách thông tin khách hàng: name, phone, email, company, status.
# - Hàm này được gọi ở đâu: app.py (route `GET /api/potential-customers`).
# - Vai trò trong hệ thống: Cung cấp danh sách các đối tác trọng tâm cần chăm sóc bán hàng.
# ==========================================================
def get_potential_customers(limit=5):
    """
    Lấy danh sách khách hàng tiềm năng / VIP / mới.

    Args:
        limit (int): Số khách hàng tối đa cần lấy (mặc định 5)

    Returns:
        list[dict]: Danh sách khách hàng với key: name, phone, email, company, status
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # Câu lệnh SQL: SELECT name, phone, email, company, status FROM customers WHERE status IN ('potential', 'vip', 'new') LIMIT ?
    # - Thao tác dùng để làm gì: Lọc khách hàng có trạng thái quan trọng.
    # - Ý nghĩa: `WHERE status IN (...)` cho phép lọc theo nhiều giá trị cùng lúc.
    # ---------------------------------------------------------
    cursor.execute("""
        SELECT name, phone, email, company, status
        FROM customers
        WHERE status IN ('potential', 'vip', 'new')
        LIMIT ?
    """, (limit,))

    customers = cursor.fetchall()
    conn.close()

    # Chuyển đổi các đối tượng Row sang dict để trả về
    return [dict(customer) for customer in customers]


# ==========================================================
# Khối lệnh kiểm tra điểm chạy trực tiếp (Main Execution Entry Point):
# - __name__ là gì: Biến đặc biệt chứa tên module.
# - __main__ là gì: Giá trị khi thực thi trực tiếp bằng lệnh `python database_service.py`.
# - Vì sao phải dùng: Khi app.py import file này (`from database_service import ...`), khối test này sẽ KHÔNG bị chạy tự động.
# - Khi chạy trực tiếp: In ra console kết quả quả đếm thống kê và dữ liệu thử nghiệm để kiểm tra tính đúng đắn của SQL queries.
# ==========================================================
if __name__ == "__main__":
    print("Kiểm tra kết nối database:")
    print(get_dashboard_stats())

    print("\nSản phẩm sắp hết hàng:")

    # ---------------------------------------------------------
    # Vòng lặp FOR 1: Duyệt qua từng sản phẩm tồn kho thấp thu được
    # ---------------------------------------------------------
    for product in get_low_stock_products():
        print(product)

    print("\nKhách hàng tiềm năng:")

    # ---------------------------------------------------------
    # Vòng lặp FOR 2: Duyệt qua từng khách hàng tiềm năng
    # ---------------------------------------------------------
    for customer in get_potential_customers():
        print(customer)