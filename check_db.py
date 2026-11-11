# ==========================================================
# Tên file: check_db.py
# Mục đích của file: Công cụ tiện ích (utility script) để kiểm tra nhanh tình trạng Cơ sở dữ liệu.
# File này dùng để làm gì:
#   - Mở kết nối tới `database.db`.
#   - Duyệt qua danh sách 6 bảng trong hệ thống để đếm số lượng dòng dữ liệu hiện có trong mỗi bảng.
#   - Trích xuất 5 khách hàng mẫu trong bảng `customers` để hiển thị định dạng mẫu.
# Khi nào file được gọi:
#   - chạy thủ công từ dòng lệnh để sanity check (kiểm tra nhanh) xem CSDL đã được khởi tạo và nạp dữ liệu thành công hay chưa.
# Luồng hoạt động tổng quát:
#   [Chạy script check_db.py]
#           ↓
#   [Kết nối SQLite database.db]
#           ↓
#   [Vòng lặp FOR qua 6 bảng: Thực thi SELECT COUNT(*) -> In số lượng bản ghi]
#           ↓
#   [Thực thi SELECT 5 khách hàng mẫu -> In danh sách dạng tuple]
#           ↓
#   [Đóng kết nối CSDL và kết thúc]
# ==========================================================

import sqlite3
from database_path import DATABASE_PATH

# ---------------------------------------------------------
# Khai báo tên file database SQLite
# ---------------------------------------------------------
DB_NAME = str(DATABASE_PATH)


# ==========================================================
# Hàm check_database:
# - Hàm dùng để làm gì: Đếm bản ghi của tất cả các bảng và hiển thị 5 bản ghi mẫu khách hàng.
# - Tham số đầu vào: Không có.
# - Giá trị trả về: Không có (None).
# - Hàm này được gọi ở đâu: Khối `if __name__ == "__main__":` khi chạy trực tiếp script.
# - Vai trò trong hệ thống: Hàm kiểm tra sức khỏe và tính sẵn sàng của dữ liệu (Database Health Checker).
# ==========================================================
def check_database():
    """
    Kết nối đến database, đếm số dòng trong từng bảng,
    và in ra 5 khách hàng đầu tiên để kiểm tra dữ liệu.
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Tạo kết nối và đối tượng con trỏ SQLite
    # ---------------------------------------------------------
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Danh sách tất cả các bảng cần kiểm tra
    tables = [
        "customers",      # Khách hàng
        "inventory",      # Kho hàng
        "opportunities",  # Cơ hội bán hàng
        "quotes",         # Báo giá
        "documents",      # Tài liệu nội bộ (dùng cho RAG)
        "chat_logs"       # Lịch sử hội thoại chatbot
    ]

    print("Kết quả kiểm tra database:")
    print("-" * 40)

    # ---------------------------------------------------------
    # Vòng lặp FOR 1: Duyệt đếm số dòng từng bảng
    # - Vòng lặp duyệt cái gì: Duyệt lần lượt từng tên bảng trong danh sách `tables`.
    # - Mỗi lần lặp xử lý gì:
    #     1. Thực thi câu lệnh SQL `SELECT COUNT(*) FROM <table_name>`.
    #     2. Lấy giá trị đếm đầu tiên `cursor.fetchone()[0]`.
    #     3. In kết quả đếm dòng ra màn hình.
    # - Khi kết thúc vòng lặp sẽ thu được gì: Bảng tổng hợp số lượng bản ghi của 6 bảng CSDL.
    # ---------------------------------------------------------
    for table in tables:
        # Câu lệnh SQL: SELECT COUNT(*) FROM <table_name>
        # Giải thích: Đếm tổng số lượng bản ghi có trong bảng tương ứng.
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]  # Lấy giá trị đầu tiên trong tuple kết quả
        print(f"Bảng {table}: {count} dòng dữ liệu")

    print("-" * 40)

    # ---------------------------------------------------------
    # Câu lệnh SQL: SELECT name, company, status FROM customers LIMIT 5
    # - Thao tác dùng để làm gì: Trích xuất 5 dòng dữ liệu khách hàng đầu tiên.
    # - Ý nghĩa từng cột: name (tên), company (công ty), status (trạng thái).
    # ---------------------------------------------------------
    cursor.execute("SELECT name, company, status FROM customers LIMIT 5")
    customers = cursor.fetchall()

    print("5 khách hàng đầu tiên:")

    # ---------------------------------------------------------
    # Vòng lặp FOR 2: Duyệt và in thông tin 5 khách hàng mẫu
    # - Vòng lặp duyệt cái gì: Duyệt từng tuple đại diện cho một khách hàng trong danh sách `customers`.
    # - Mỗi lần lặp xử lý gì: In tuple ra console (VD: ('Nguyễn Văn A', 'Công ty X', 'vip')).
    # ---------------------------------------------------------
    for customer in customers:
        print(customer)  # In dưới dạng tuple: (name, company, status)

    # ---------------------------------------------------------
    # Bước 3 trong hàm: Giải phóng kết nối CSDL
    # ---------------------------------------------------------
    conn.close()


# ==========================================================
# Khối lệnh kiểm tra điểm chạy trực tiếp (Main Execution Entry Point):
# - __name__ là gì: Biến hệ thống chứa tên của file script.
# - __main__ là gì: Giá trị khi file được khởi chạy trực tiếp (`python check_db.py`).
# - Vì sao phải dùng: Bảo đảm script chỉ chạy khi thực thi trực tiếp, không chạy khi import vào file khác.
# - Khi import: __name__ != "__main__" -> Không gọi check_database().
# - Khi chạy trực tiếp: __name__ == "__main__" -> Gọi check_database() hiển thị báo cáo.
# ==========================================================
if __name__ == "__main__":
    check_database()