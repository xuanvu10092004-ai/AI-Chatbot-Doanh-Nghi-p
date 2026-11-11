# ==========================================================
# Tên file: init_db.py
# Mục đích của file: Khởi tạo Cơ sở dữ liệu SQLite cho hệ thống AI Chatbot Doanh Nghiệp.
# File này dùng để làm gì:
#   - Khởi tạo file cơ sở dữ liệu SQLite mang tên `database.db`.
#   - Thiết lập các bảng lưu trữ thông tin nghiệp vụ bao gồm:
#       1. `customers`    : Quản lý thông tin khách hàng (Phần CRM).
#       2. `inventory`    : Quản lý hàng hóa, tồn kho và bảng giá (Phần Warehouse).
#       3. `opportunities`: Quản lý các cơ hội bán hàng (Phần Sales Opportunity).
#       4. `quotes`       : Quản lý báo giá gửi tới khách hàng (Phần Sales Quote).
#       5. `documents`    : Lưu trữ tài liệu nội bộ, quy trình, chính sách (Phần RAG Pipeline).
#       6. `chat_logs`    : Lưu trữ nhật ký cuộc hội thoại giữa người dùng và Chatbot AI.
# Khi nào file được gọi:
#   - Được chạy trực tiếp MỘT LẦN duy nhất ở bước thiết lập môi trường đầu tiên (Setup phase).
# Luồng hoạt động tổng quát:
#   [Chạy script init_db.py]
#           ↓
#   [Kết nối / Tạo mới file database.db]
#           ↓
#   [Bật ràng buộc Khóa ngoại PRAGMA foreign_keys = ON]
#           ↓
#   [Thực thi các câu lệnh CREATE TABLE IF NOT EXISTS cho 6 bảng]
#           ↓
#   [Lưu thay đổi Commit & Đóng kết nối Database]
#           ↓
#   [In thông báo thành công ra màn hình Terminal]
# ==========================================================

import sqlite3
from database_path import DATABASE_PATH

# ---------------------------------------------------------
# Khai báo tên file CSDL SQLite dùng chung trong toàn hệ thống
# ---------------------------------------------------------
DB_NAME = str(DATABASE_PATH)


# ==========================================================
# Hàm create_database:
# - Hàm dùng để làm gì: Tạo file database.db và thực thi chuỗi câu lệnh SQL khởi tạo 6 bảng dữ liệu.
# - Tham số đầu vào: Không có.
# - Giá trị trả về: Không có (None).
# - Hàm này được gọi ở đâu: Được gọi trực tiếp trong khối `if __name__ == "__main__":` khi chạy script này.
# - Vai trò trong hệ thống: Tầng định nghĩa Schema cơ sở dữ liệu (Database Schema Initialization).
# ==========================================================
def create_database():
    """
    Kết nối đến database (tạo mới nếu chưa tồn tại),
    rồi tạo tất cả các bảng cần thiết cho hệ thống AI Chatbot doanh nghiệp.
    """

    # ---------------------------------------------------------
    # Bước 1: Mở kết nối đến Cơ sở dữ liệu SQLite
    # - Bước này đang làm gì: Mở hoặc tạo mới file database.db và lấy đối tượng con trỏ (cursor).
    # - Vì sao cần bước này: SQLite cần một đường truyền kết nối và con trỏ cursor để thực thi các câu lệnh SQL.
    # - Dữ liệu đi từ đâu đến đâu: Từ ổ đĩa tệp tin -> Nạp trình kết nối SQLite driver vào bộ nhớ RAM.
    # - Sau bước này chương trình sẽ làm gì tiếp: Bật chế độ ràng buộc khóa ngoại (Foreign Keys).
    # ---------------------------------------------------------
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # Câu lệnh SQL: PRAGMA foreign_keys = ON
    # SQLite sẽ kiểm tra và thực thi các mối quan hệ giữa các bảng thông qua FOREIGN KEY
    # - Mục đích: Bật tính năng kiểm tra ràng buộc khóa ngoại (Foreign Key Constraints).
    # - Vì sao cần: Mặc định SQLite TẮT kiểm tra khóa ngoại để tương thích ngược. Bật tính năng này giúp đảm bảo tính toàn vẹn dữ liệu (VD: Không thể xóa khách hàng nếu còn báo giá liên quan).
    # ---------------------------------------------------------
    cursor.execute("PRAGMA foreign_keys = ON")

    # ---------------------------------------------------------
    # Bước 2: Tạo bảng `customers` (Quản lý khách hàng - CRM)
    # ---------------------------------------------------------
    # Câu lệnh SQL: CREATE TABLE IF NOT EXISTS customers
    # - Bảng dùng để làm gì: Lưu trữ thông tin chi tiết của tất cả đối tác/khách hàng.
    # - Tại sao dùng IF NOT EXISTS: Tránh gây ra lỗi crash chương trình nếu bảng đã tồn tại sẵn từ trước.
    # - Ý nghĩa từng cột:
    #     + id: Khóa chính (PRIMARY KEY), tự động tăng số nguyên (AUTOINCREMENT).
    #     + name: Tên khách hàng (Bắt buộc NOT NULL).
    #     + phone: Số điện thoại liên hệ.
    #     + email: Địa chỉ Email.
    #     + company: Tên công ty/Tổ chức công tác.
    #     + address: Địa chỉ công ty/nhà riêng.
    #     + status: Trạng thái phân loại ('new': mới, 'potential': tiềm năng, 'vip': khách VIP). Mặc định là 'new'.
    #     + note: Ghi chú bổ sung thông tin.
    #     + created_at: Thời điểm tạo bản ghi (Tự động lấy thời gian hệ thống CURRENT_TIMESTAMP).
    # - Quan hệ với bảng khác: Là bảng CHA, được tham chiếu bởi `opportunities.customer_id` và `quotes.customer_id`.
    # ---------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        company TEXT,
        address TEXT,
        status TEXT DEFAULT 'new',
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------------------------------------------------------
    # Bước 3: Tạo bảng `inventory` (Quản lý hàng hóa / kho hàng)
    # ---------------------------------------------------------
    # Câu lệnh SQL: CREATE TABLE IF NOT EXISTS inventory
    # - Bảng dùng để làm gì: Theo dõi danh mục sản phẩm, số lượng tồn kho và giá bán.
    # - Tại sao dùng IF NOT EXISTS: Giúp chạy lại script an toàn mà không làm mất bảng đã có.
    # - Ý nghĩa từng cột:
    #     + id: Khóa chính tự tăng.
    #     + product_name: Tên sản phẩm / dịch vụ (NOT NULL).
    #     + category: Phân loại danh mục (vd: Thiết bị, Phần mềm, Dịch vụ).
    #     + quantity: Số lượng tồn kho (Số nguyên, mặc định = 0).
    #     + unit: Đơn vị tính (Bộ, Cái, Gói, Tháng...).
    #     + price: Giá bán đơn vị (Số thực REAL, mặc định = 0).
    #     + supplier: Nhà cung cấp hàng hóa.
    #     + note: Ghi chú chi tiết sản phẩm.
    #     + created_at: Ngày giờ nhập dữ liệu sản phẩm.
    # - Quan hệ với bảng khác: Là bảng CHA, được tham chiếu bởi `quotes.product_id`.
    # ---------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        category TEXT,
        quantity INTEGER DEFAULT 0,
        unit TEXT,
        price REAL DEFAULT 0,
        supplier TEXT,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------------------------------------------------------
    # Bước 4: Tạo bảng `opportunities` (Quản lý cơ hội bán hàng)
    # ---------------------------------------------------------
    # Câu lệnh SQL: CREATE TABLE IF NOT EXISTS opportunities
    # - Bảng dùng để làm gì: Lưu vết các dự án/thương vụ tiềm năng theo từng giai đoạn bán hàng.
    # - Tại sao dùng IF NOT EXISTS: Tránh lỗi khi chạy khởi tạo nhiều lần.
    # - Ý nghĩa từng cột:
    #     + id: Khóa chính tự tăng.
    #     + customer_id: Khóa ngoại liên kết tới `customers(id)` để biết cơ hội này thuộc về khách hàng nào.
    #     + title: Tiêu đề cơ hội kinh doanh (NOT NULL).
    #     + description: Mô tả nhu cầu khách hàng.
    #     + value: Giá trị hợp đồng dự kiến (VNĐ).
    #     + stage: Giai đoạn thương lượng ('new', 'negotiation', 'won', 'lost').
    #     + probability: Tỷ lệ chốt hợp đồng thành công (0 đến 100%).
    #     + expected_close_date: Ngày dự kiến chốt hợp đồng.
    #     + created_at: Ngày tạo cơ hội.
    # - Quan hệ với bảng khác: Bảng CON của `customers` qua `FOREIGN KEY (customer_id) REFERENCES customers(id)`.
    # ---------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        value REAL DEFAULT 0,
        stage TEXT DEFAULT 'new',
        probability INTEGER DEFAULT 0,
        expected_close_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    # ---------------------------------------------------------
    # Bước 5: Tạo bảng `quotes` (Quản lý báo giá)
    # ---------------------------------------------------------
    # Câu lệnh SQL: CREATE TABLE IF NOT EXISTS quotes
    # - Bảng dùng để làm gì: Lưu trữ các đơn báo giá kinh doanh phát hành cho khách hàng.
    # - Tại sao dùng IF NOT EXISTS: Đảm bảo tính lặp lại an toàn của script.
    # - Ý nghĩa từng cột:
    #     + id: Khóa chính tự tăng.
    #     + customer_id: Khóa ngoại tham chiếu `customers(id)`.
    #     + product_id: Khóa ngoại tham chiếu `inventory(id)`.
    #     + quote_code: Mã quản lý báo giá (ví dụ: BG-2026-001).
    #     + quantity: Số lượng sản phẩm báo giá.
    #     + total_amount: Tổng số tiền báo giá (VNĐ).
    #     + status: Trạng thái duyệt báo giá ('draft', 'pending', 'approved', 'rejected').
    #     + note: Điều khoản hoặc ghi chú báo giá.
    #     + created_at: Ngày phát hành báo giá.
    # - Quan hệ với bảng khác: Bảng CON tham chiếu tới cả `customers` và `inventory`.
    # ---------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        product_id INTEGER,
        quote_code TEXT,
        quantity INTEGER DEFAULT 1,
        total_amount REAL DEFAULT 0,
        status TEXT DEFAULT 'draft',
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (product_id) REFERENCES inventory(id)
    )
    """)

    # ---------------------------------------------------------
    # Bước 6: Tạo bảng `documents` (Lưu tài liệu kiến thức RAG)
    # ---------------------------------------------------------
    # Câu lệnh SQL: CREATE TABLE IF NOT EXISTS documents
    # - Bảng dùng để làm gì: Lưu trữ các đoạn văn bản tài liệu nội bộ, chính sách công ty để phục vụ tra cứu RAG (Retrieval-Augmented Generation).
    # - Tại sao dùng IF NOT EXISTS: Tránh đè cấu trúc bảng nếu đã tồn tại.
    # - Ý nghĩa từng cột:
    #     + id: Khóa chính tự tăng.
    #     + title: Tiêu đề văn bản/tài liệu (NOT NULL).
    #     + content: Nội dung chi tiết văn bản (NOT NULL, dùng để tìm kiếm từ khóa LIKE).
    #     + source: Tên file nguồn hoặc xuất xứ tài liệu.
    #     + document_type: Loại văn bản ('policy': chính sách, 'guide': hướng dẫn quy trình).
    #     + created_at: Ngày cập nhật tài liệu.
    # - Quan hệ với bảng khác: Bảng độc lập dùng riêng cho `rag_service.py`.
    # ---------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        source TEXT,
        document_type TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------------------------------------------------------
    # Bước 6.5: Tạo bảng `bookings` (Quản lý giao dịch/đặt chỗ)
    # ---------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        booking_date TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'confirmed',
        note TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    # ---------------------------------------------------------
    # Bước 7: Tạo bảng `chat_logs` (Lưu lịch sử hội thoại Chatbot)
    # ---------------------------------------------------------
    # Câu lệnh SQL: CREATE TABLE IF NOT EXISTS chat_logs
    # - Bảng dùng để làm gì: Theo dõi, ghi nhật ký tương tác người dùng - AI Chatbot.
    # - Ý nghĩa từng cột:
    #     + id: Khóa chính tự tăng.
    #     + user_question: Câu hỏi người dùng gửi lên (NOT NULL).
    #     + ai_answer: Câu trả lời do AI/Hệ thống phản hồi.
    #     + module: Tên module đã xử lý câu hỏi (AI CRM, AI Warehouse, RAG...).
    #     + created_at: Thời điểm diễn ra cuộc trò chuyện.
    # ---------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_question TEXT NOT NULL,
        ai_answer TEXT,
        module TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------------------------------------------------------
    # Bước 8: Commit lưu thay đổi và đóng kết nối CSDL
    # - Bước này đang làm gì: Ghi nhận tất cả thao tác DDL (Data Definition Language) vào file database.db và giải phóng tài nguyên conn.
    # - Vì sao cần bước này: Nếu không commit, các câu lệnh tạo bảng sẽ nằm ở bộ nhớ đệm và không ghi chính thức vào file ổ đĩa.
    # - Sau bước này chương trình sẽ làm gì tiếp: In thông báo hoàn tất ra màn hình console.
    # ---------------------------------------------------------
    conn.commit()
    conn.close()

    # In thông báo xác nhận đã tạo thành công
    print("Tạo database.db thành công!")
    print("Đã tạo các bảng:")
    print("- customers")
    print("- inventory")
    print("- opportunities")
    print("- quotes")
    print("- documents")
    print("- bookings")
    print("- chat_logs")


# ==========================================================
# Khối lệnh kiểm tra điểm chạy trực tiếp (Main Execution Entry Point):
# - __name__ là gì: Biến đặc biệt trong Python chứa tên của module hiện tại.
# - __main__ là gì: Giá trị chuỗi mặc định của __name__ khi file được thực thi trực tiếp từ dòng lệnh.
# - Vì sao phải dùng khối lệnh này: Để phân biệt khi chạy file trực tiếp với khi được import làm thư viện ở file khác.
# - Khi import module này sang file khác (VD: `import init_db`): __name__ sẽ bằng "init_db", điều kiện == "__main__" trả về FALSE -> Hàm `create_database()` KHÔNG tự động chạy.
# - Khi chạy trực tiếp file này (`python init_db.py`): __name__ bằng "__main__", điều kiện trả về TRUE -> Hàm `create_database()` được kích hoạt ngay lập tức.
# ==========================================================
if __name__ == "__main__":
    create_database()