# ==========================================================
# Tên file: sql_service.py
# Mục đích của file: Tầng xử lý Text-to-SQL theo quy tắc (Rule-based Text-to-SQL Engine).
# File này dùng để làm gì:
#   - Tiếp nhận các câu hỏi đã được `routing.py` phân loại thuộc luồng "SQL".
#   - Phân tích từ khóa trong câu hỏi (cả bản gốc có dấu và bản đã chuẩn hóa bỏ dấu) để khớp với 17 mẫu truy vấn nghiệp vụ.
#   - Tự động sinh ra câu lệnh SQL tương ứng (SELECT COUNT, SELECT WHERE, SUM, ORDER BY, LIMIT).
#   - Thực thi câu lệnh SQL vừa sinh trên Cơ sở dữ liệu SQLite (`database.db`).
#   - Format kết quả trả về từ CSDL thành dạng chuỗi văn bản thuần (Text Context) dễ đọc.
#   - Gửi chuỗi Text Context này cho `ai_service.py` để Groq LLM diễn giải thành câu trả lời hoàn chỉnh.
# Khi nào file được gọi:
#   - Được gọi bởi app.py trong route POST /chat khi routing trả về type == "SQL".
#   - Được gọi bởi `test_sql.py` và `test_ai.py` để kiểm tra khả năng sinh SQL và lấy dữ liệu thật.
# Luồng hoạt động tổng quát Text-to-SQL:
#   Câu hỏi người dùng
#           ↓
#   [Phân tích từ khóa trong answer_sql_question(question)]
#           ↓
#   [Sinh câu lệnh SQL chuẩn + Thực thi qua fetch_all() / fetch_one()]
#           ↓
#   [SQLite trả về danh sách bản ghi]
#           ↓
#   [Format kết quả bằng format_customers / inventory / quotes / opportunities]
#           ↓
#   [Trả về Context cho ai_service.py để Groq LLM diễn giải]
#           ↓
#   [Trả câu trả lời tự nhiên về cho giao diện người dùng]
# ==========================================================

import sqlite3
import re
from routing import normalize_question  # Hàm chuẩn hóa: lowercase + bỏ dấu
from database_path import DATABASE_PATH

# ---------------------------------------------------------
# Hằng số tên file CSDL SQLite
# ---------------------------------------------------------
DB_NAME = str(DATABASE_PATH)


# ==========================================================
# Hàm get_connection:
# - Hàm dùng để làm gì: Tạo và trả về kết nối CSDL SQLite với cấu hình `conn.row_factory = sqlite3.Row`.
# - Tham số đầu vào: Không có.
# - Giá trị trả về: sqlite3.Connection object.
# - Hàm này được gọi ở đâu: `fetch_all()`, `fetch_one()`.
# - Vai trò trong hệ thống: Hàm hỗ trợ kết nối CSDL dùng chung trong sql_service.
# ==========================================================
def get_connection():
    """
    Tạo và trả về kết nối đến database SQLite.
    row_factory giúp truy cập cột theo tên (row["name"]).
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================================
# Hàm fetch_all:
# - Hàm dùng để làm gì: Thực thi câu lệnh SQL và trả về danh sách NHIỀU dòng kết quả dưới dạng từ điển list[dict].
# - Tham số đầu vào:
#     + sql (str): Câu lệnh SQL SELECT cần chạy.
#     + params (tuple): Tham số an toàn nhúng vào SQL (tránh lỗi SQL Injection).
# - Giá trị trả về:
#     + list[dict]: Danh sách các bản ghi, mỗi bản ghi là một dict với key là tên cột.
# - Hàm này được gọi ở đâu: Được gọi rộng rãi trong hàm `answer_sql_question()`.
# - Vai trò trong hệ thống: Hàm tiện ích truy vấn dữ liệu tập hợp (Collection Data Fetcher).
# ==========================================================
def fetch_all(sql, params=()):
    """
    Thực thi câu SQL và trả về NHIỀU kết quả.

    Args:
        sql (str): Câu lệnh SQL cần thực thi
        params (tuple): Các tham số truyền vào SQL (tránh SQL Injection)

    Returns:
        list[dict]: Danh sách các dòng kết quả, mỗi dòng là một dict
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Mở kết nối, tạo con trỏ và thực thi SQL
    # ---------------------------------------------------------
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    # ---------------------------------------------------------
    # Bước 2 trong hàm: Ép kiểu danh sách sqlite3.Row thành list[dict] và trả về
    # ---------------------------------------------------------
    return [dict(row) for row in rows]


# ==========================================================
# Hàm fetch_one:
# - Hàm dùng để làm gì: Thực thi SQL và trả về duy nhất MỘT dòng kết quả (hoặc None nếu không có).
# - Tham số đầu vào:
#     + sql (str): Câu lệnh SQL SELECT (ví dụ: SELECT COUNT, SELECT SUM...).
#     + params (tuple): Các tham số truyền vào.
# - Giá trị trả về:
#     + dict | None: Từ điển thông tin bản ghi đầu tiên hoặc None.
# - Hàm này được gọi ở đâu: Được gọi trong các truy vấn đếm COUNT(*), tính SUM(total_amount).
# - Vai trò trong hệ thống: Hàm tiện ích truy vấn dữ liệu đơn lẻ (Single Row Data Fetcher).
# ==========================================================
def fetch_one(sql, params=()):
    """
    Thực thi câu SQL và trả về MỘT kết quả duy nhất.

    Args:
        sql (str): Câu lệnh SQL cần thực thi
        params (tuple): Các tham số truyền vào SQL

    Returns:
        dict | None: Dòng kết quả đầu tiên dưới dạng dict, hoặc None nếu không có
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Thực thi SQL fetchone()
    # ---------------------------------------------------------
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    row = cursor.fetchone()
    conn.close()

    # ---------------------------------------------------------
    # Bước 2 trong hàm: Trả về dict nếu row tồn tại, ngược lại trả về None
    # ---------------------------------------------------------
    return dict(row) if row else None


# ============================================================
# CÁC HÀM HELPER FORMAT DỮ LIỆU THÀNH CHUỖI VĂN BẢN (TEXT CONTEXT)
# ============================================================

# ==========================================================
# Hàm format_customers:
# - Hàm dùng để làm gì: Chuyển đổi danh sách bản ghi khách hàng từ dạng dict sang chuỗi văn bản tiếng Việt dễ đọc.
# - Tham số đầu vào:
#     + rows (list[dict]): Danh sách các bản ghi khách hàng.
#     + title (str): Tiêu đề danh sách (mặc định "Danh sách khách hàng").
# - Giá trị trả về:
#     + str: Chuỗi văn bản đã định dạng dòng.
# ==========================================================
def format_customers(rows, title="Danh sách khách hàng"):
    """Format danh sách khách hàng thành chuỗi text."""
    # Điều kiện IF: Kiểm tra danh sách rỗng
    if not rows:
        return "Không tìm thấy khách hàng nào phù hợp."

    lines = [f"{title} ({len(rows)} người):"]

    # Vòng lặp FOR: Duyệt từng dòng khách hàng và format thông tin
    for i, row in enumerate(rows, 1):
        lines.append(
            f"{i}. {row['name']} | {row['company']} | {row['phone']} | {row['email']} | trạng thái: {row['status']}"
        )
    return "\n".join(lines)


# ==========================================================
# Hàm format_inventory:
# - Hàm dùng để làm gì: Định dạng danh sách sản phẩm kho hàng thành chuỗi văn bản.
# - Tham số đầu vào:
#     + rows (list[dict]): Danh sách các sản phẩm.
#     + title (str): Tiêu đề bảng.
# - Giá trị trả về:
#     + str: Chuỗi text đã định dạng.
# ==========================================================
def format_inventory(rows, title="Danh sách sản phẩm"):
    """Format danh sách sản phẩm tồn kho thành chuỗi text."""
    # Điều kiện IF: Kiểm tra nếu không có sản phẩm
    if not rows:
        return "Không tìm thấy sản phẩm nào phù hợp."

    lines = [f"{title} ({len(rows)} sản phẩm):"]

    # Vòng lặp FOR: Duyệt từng sản phẩm và tạo dòng văn bản
    for i, row in enumerate(rows, 1):
        lines.append(
            f"{i}. {row['product_name']} | danh mục: {row['category']} | tồn kho: {row['quantity']} {row['unit']} | giá: {row['price']:,.0f} VNĐ"
        )
    return "\n".join(lines)


# ==========================================================
# Hàm format_quotes:
# - Hàm dùng để làm gì: Định dạng danh sách báo giá thành chuỗi văn bản.
# - Tham số đầu vào:
#     + rows (list[dict]): Danh sách báo giá.
#     + title (str): Tiêu đề hiển thị.
# - Giá trị trả về:
#     + str: Chuỗi văn bản format.
# ==========================================================
def format_quotes(rows, title="Danh sách báo giá"):
    """Format danh sách báo giá thành chuỗi text."""
    # Điều kiện IF: Kiểm tra danh sách báo giá rỗng
    if not rows:
        return "Không tìm thấy báo giá nào phù hợp."

    lines = [f"{title} ({len(rows)} báo giá):"]

    # Vòng lặp FOR: Duyệt từng báo giá
    for i, row in enumerate(rows, 1):
        lines.append(
            f"{i}. {row['quote_code']} | tổng tiền: {row['total_amount']:,.0f} VNĐ | trạng thái: {row['status']}"
        )
    return "\n".join(lines)


# ==========================================================
# Hàm format_opportunities:
# - Hàm dùng để làm gì: Định dạng danh sách cơ hội bán hàng thành chuỗi text.
# - Tham số đầu vào:
#     + rows (list[dict]): Danh sách các cơ hội kinh doanh.
#     + title (str): Tiêu đề hiển thị.
# - Giá trị trả về:
#     + str: Chuỗi text kết quả.
# ==========================================================
def format_opportunities(rows, title="Danh sách cơ hội bán hàng"):
    """Format danh sách cơ hội bán hàng thành chuỗi text."""
    # Điều kiện IF: Kiểm tra danh sách rỗng
    if not rows:
        return "Không tìm thấy cơ hội bán hàng nào phù hợp."

    lines = [f"{title} ({len(rows)} cơ hội):"]

    # Vòng lặp FOR: Duyệt từng cơ hội
    for i, row in enumerate(rows, 1):
        lines.append(
            f"{i}. {row['title']} | giá trị: {row['value']:,.0f} VNĐ | giai đoạn: {row['stage']} | xác suất: {row['probability']}%"
        )
    return "\n".join(lines)


# ============================================================
# HÀM CHÍNH XỬ LÝ CÂU HỎI SQL
# ============================================================

# ==========================================================
# Hàm answer_sql_question:
# - Hàm dùng để làm gì: Phân tích từ khóa câu hỏi, quyết định câu SQL phù hợp, truy vấn SQLite và format dữ liệu trả về Context.
# - Tham số đầu vào:
#     + question (str): Câu hỏi gốc của người dùng.
# - Giá trị trả về:
#     + str: Ngữ cảnh dữ liệu thu được từ CSDL dưới dạng văn bản.
# - Hàm này được gọi ở đâu: app.py, test_sql.py, test_ai.py.
# - Vai trò trong hệ thống: Trái tim của bộ xử lý Text-to-SQL (Core Text-to-SQL Engine).
# ==========================================================
def answer_sql_question(question):
    """
    Hàm chính xử lý câu hỏi SQL.
    Phân tích từ khóa trong câu hỏi (có dấu & không dấu),
    chọn truy vấn SQL phù hợp và trả về context dạng text
    để ai_service.py gửi sang Groq sinh câu trả lời tự nhiên.

    Args:
        question (str): Câu hỏi gốc của người dùng

    Returns:
        str: Context dữ liệu từ database (chưa qua AI)
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Chuẩn hóa câu hỏi dạng có dấu (q) và không dấu (q_na)
    # ---------------------------------------------------------
    q, q_na = normalize_question(question)

    # ============================================================
    # MODULE CRM - KHÁCH HÀNG
    # ============================================================

    # ---------------------------------------------------------
    # 0. Top 10 khách hàng doanh thu cao nhất (Module 1)
    # ---------------------------------------------------------
    if (
        "top" in q or "doanh thu cao" in q or "doanh thu cao nhat" in q_na
    ) and (
        "khách" in q or "khach" in q_na or "company" in q
    ):
        rows = fetch_all("""
            SELECT c.name, c.company, c.phone, c.email, c.status, SUM(q.total_amount) as total_revenue
            FROM customers c
            JOIN quotes q ON c.id = q.customer_id
            WHERE q.status = 'approved'
            GROUP BY c.id
            ORDER BY total_revenue DESC
            LIMIT 10
        """)
        if not rows:
            return "Chưa có đủ dữ liệu báo giá để tính toán top khách hàng doanh thu cao nhất."
        lines = ["Top khách hàng có doanh thu cao nhất:"]
        for i, r in enumerate(rows, 1):
            lines.append(f"{i}. {r['name']} ({r['company']}) | Doanh thu: {r['total_revenue']:,.0f} VNĐ")
        return "\n".join(lines)

    # ---------------------------------------------------------
    # 0.1. Khách hàng chưa booking trong 90 ngày (Module 2)
    # ---------------------------------------------------------
    if (
        "chưa" in q or "chua" in q_na
    ) and (
        "booking" in q or "giao dịch" in q or "giao dich" in q_na
    ) and (
        "90 ngày" in q or "90 ngay" in q_na or "ngày" in q or "ngay" in q_na
    ):
        rows = fetch_all("""
            SELECT name, company, phone, email, status
            FROM customers
            WHERE id NOT IN (
                SELECT customer_id FROM bookings
                WHERE booking_date >= date('now', '-90 days')
            )
            ORDER BY name
        """)
        return format_customers(rows, "Khách hàng chưa phát sinh booking trong 90 ngày qua")

    # ---------------------------------------------------------
    # 1. Đếm tổng số khách hàng
    # - Điều kiện IF kiểm tra: "bao nhiêu" VÀ "khách"
    # ---------------------------------------------------------
    if (
        ("bao nhiêu" in q or "bao nhieu" in q_na)
        and ("khách" in q or "khach" in q_na)
    ):
        if "vip" in q:
            result = fetch_one("SELECT COUNT(*) AS total FROM customers WHERE status = 'vip'")
            return f"Tổng số khách hàng VIP trong hệ thống: {result['total']} khách hàng."
        elif "tiềm năng" in q or "tiem nang" in q_na:
            result = fetch_one("SELECT COUNT(*) AS total FROM customers WHERE status = 'potential'")
            return f"Tổng số khách hàng tiềm năng trong hệ thống: {result['total']} khách hàng."
        elif "mới" in q or "moi" in q_na:
            result = fetch_one("SELECT COUNT(*) AS total FROM customers WHERE status = 'new'")
            return f"Tổng số khách hàng mới trong hệ thống: {result['total']} khách hàng."
        else:
            # Câu lệnh SQL: SELECT COUNT(*) AS total FROM customers
            result = fetch_one("SELECT COUNT(*) AS total FROM customers")
            return f"Tổng số khách hàng trong hệ thống: {result['total']} khách hàng."

    # ---------------------------------------------------------
    # 2. Danh sách khách hàng VIP
    # - Điều kiện IF kiểm tra: "vip" + các từ khóa danh sách/khách
    # ---------------------------------------------------------
    if "vip" in q and (
        "khách" in q or "khach" in q_na
        or "danh sách" in q or "danh sach" in q_na
        or "liệt kê" in q or "liet ke" in q_na
        or "là ai" in q or "la ai" in q_na
        or "nào" in q or "nao" in q_na
    ):
        # Câu lệnh SQL: SELECT name, company, phone, email, status FROM customers WHERE status = 'vip' ORDER BY name
        rows = fetch_all("""
            SELECT name, company, phone, email, status
            FROM customers
            WHERE status = 'vip'
            ORDER BY name
        """)
        return format_customers(rows, "Danh sách khách hàng VIP")

    # ---------------------------------------------------------
    # 3. Danh sách khách hàng tiềm năng
    # - Điều kiện IF kiểm tra: "tiềm năng" / "tiem nang"
    # ---------------------------------------------------------
    if "tiềm năng" in q or "tiem nang" in q_na:
        # Câu lệnh SQL: SELECT ... FROM customers WHERE status = 'potential' ORDER BY name
        rows = fetch_all("""
            SELECT name, company, phone, email, status
            FROM customers
            WHERE status = 'potential'
            ORDER BY name
        """)
        return format_customers(rows, "Danh sách khách hàng tiềm năng")

    # ---------------------------------------------------------
    # 4. Danh sách khách hàng mới (status = 'new')
    # - Điều kiện IF kiểm tra: "khách hàng mới"
    # ---------------------------------------------------------
    if (
        ("khách mới" in q or "khach moi" in q_na)
        or ("khách hàng mới" in q or "khach hang moi" in q_na)
        or ("khách" in q and "mới" in q)
    ):
        # Câu lệnh SQL: SELECT ... FROM customers WHERE status = 'new' ORDER BY name
        rows = fetch_all("""
            SELECT name, company, phone, email, status
            FROM customers
            WHERE status = 'new'
            ORDER BY name
        """)
        return format_customers(rows, "Danh sách khách hàng mới")

    # ---------------------------------------------------------
    # 5. Liệt kê TẤT CẢ khách hàng
    # - Điều kiện IF kiểm tra: "khách" + "danh sách" / "tất cả"
    # ---------------------------------------------------------
    if (
        "khách" in q or "khach" in q_na
        or "customer" in q
    ) and (
        "liệt kê" in q or "liet ke" in q_na
        or "danh sách" in q or "danh sach" in q_na
        or "tất cả" in q or "tat ca" in q_na
        or "toàn bộ" in q or "toan bo" in q_na
        or "all" in q
    ):
        # Câu lệnh SQL: SELECT name, company, phone, email, status FROM customers ORDER BY name LIMIT 60
        rows = fetch_all("""
            SELECT name, company, phone, email, status
            FROM customers
            ORDER BY name
            LIMIT 60
        """)
        return format_customers(rows, "Danh sách toàn bộ khách hàng")

    # ============================================================
    # MODULE WAREHOUSE - KHO HÀNG / SẢN PHẨM
    # ============================================================

    # ---------------------------------------------------------
    # 6. Đếm tổng số sản phẩm
    # - Điều kiện IF kiểm tra: "bao nhiêu" + "sản phẩm"
    # ---------------------------------------------------------
    if (
        ("bao nhiêu" in q or "bao nhieu" in q_na)
        and ("sản phẩm" in q or "san pham" in q_na)
    ):
        # Câu lệnh SQL: SELECT COUNT(*) AS total FROM inventory
        result = fetch_one("SELECT COUNT(*) AS total FROM inventory")
        return f"Tổng số sản phẩm trong kho: {result['total']} sản phẩm."

    # ---------------------------------------------------------
    # 7. Sản phẩm sắp hết hàng (quantity < 10 hoặc mức tùy chỉnh)
    # - Điều kiện IF kiểm tra: "sắp hết" / "tồn kho thấp" / "hết hàng"
    # ---------------------------------------------------------
    if (
        "sắp hết" in q or "sap het" in q_na
        or "tồn kho thấp" in q or "ton kho thap" in q_na
        or ("hết hàng" in q or "het hang" in q_na)
        or ("tồn kho" in q and ("thấp" in q or "thap" in q_na or "ít" in q or "it" in q_na))
    ):
        # Trích xuất mức tối thiểu động (ví dụ: "mức tối thiểu 50")
        match = re.search(r'\d+', q)
        limit_val = max(1, min(int(match.group()), 1000)) if match else 10

        rows = fetch_all("""
            SELECT product_name, category, quantity, unit, price
            FROM inventory
            WHERE quantity < ?
            ORDER BY quantity ASC
        """, (limit_val,))
        # Điều kiện IF sub: Nếu không có sản phẩm tồn kho < mức
        if not rows:
            return f"Hiện không có sản phẩm nào sắp hết hàng (tồn kho < {limit_val})."
        return format_inventory(rows, f"Sản phẩm sắp hết hàng (tồn kho < {limit_val})")

    # ---------------------------------------------------------
    # 8. Liệt kê tất cả sản phẩm / tồn kho
    # - Điều kiện IF kiểm tra: "sản phẩm" / "tồn kho" + "danh sách" / "tất cả"
    # ---------------------------------------------------------
    if (
        "sản phẩm" in q or "san pham" in q_na
        or "tồn kho" in q or "ton kho" in q_na
        or "kho hàng" in q or "kho hang" in q_na
        or "inventory" in q
    ) and (
        "liệt kê" in q or "liet ke" in q_na
        or "danh sách" in q or "danh sach" in q_na
        or "tất cả" in q or "tat ca" in q_na
        or "toàn bộ" in q or "toan bo" in q_na
        or "nào" in q or "nao" in q_na
    ):
        # Câu lệnh SQL: SELECT product_name, category, quantity, unit, price FROM inventory ORDER BY quantity ASC LIMIT 50
        rows = fetch_all("""
            SELECT product_name, category, quantity, unit, price
            FROM inventory
            ORDER BY quantity ASC
            LIMIT 50
        """)
        return format_inventory(rows, "Danh sách sản phẩm trong kho (tối đa 50)")

    # ============================================================
    # MODULE QUOTE - BÁO GIÁ
    # ============================================================

    # ---------------------------------------------------------
    # 8.5. Tạo báo giá tự động (Module 4)
    # - "Tạo quote cho ABC", "Tạo báo giá cho XYZ"
    # ---------------------------------------------------------
    if "tạo quote cho" in q or "tạo báo giá cho" in q or "tao quote cho" in q_na or "tao bao gia cho" in q_na:
        # Trích xuất tên công ty/khách hàng từ câu hỏi gốc (để giữ nguyên chữ HOA/thường)
        match = re.search(r'tạo (?:quote|báo giá) cho (.*)', question, re.IGNORECASE)
        if not match:
            match = re.search(r'tao (?:quote|bao gia) cho (.*)', question, re.IGNORECASE)

        if match:
            customer_name_original = match.group(1).strip()
            # Dùng lowercase để tìm kiếm LIKE
            customer_name_lower = customer_name_original.lower()

            conn = get_connection()
            cursor = conn.cursor()
            # Tìm ID khách hàng
            cursor.execute("SELECT id FROM customers WHERE LOWER(name) LIKE ? OR LOWER(company) LIKE ? LIMIT 1", (f"%{customer_name_lower}%", f"%{customer_name_lower}%"))
            customer = cursor.fetchone()

            if customer:
                c_id = customer["id"]
                msg = f"Đã tìm thấy khách hàng hiện hữu và tự động tạo báo giá (nháp) cho: {customer_name_original}."
            else:
                # Tự động tạo khách hàng mới
                cursor.execute("""
                    INSERT INTO customers (name, company, phone, email, address, status, note)
                    VALUES (?, ?, 'Chưa có', 'Chưa có', 'Chưa có', 'new', 'Tạo tự động từ AI Chatbot')
                """, (customer_name_original, customer_name_original))
                c_id = cursor.lastrowid
                msg = f"Đã tự động THÊM MỚI khách hàng '{customer_name_original}' vào hệ thống và tạo báo giá (nháp) thành công."

            cursor.execute("""
                INSERT INTO quotes (customer_id, product_id, quote_code, quantity, total_amount, status, note)
                VALUES (?, NULL, 'AUTO-QUOTE', 1, 0, 'draft', 'Auto-generated quote')
            """, (c_id,))
            conn.commit()
            conn.close()
            return msg + " Cần cập nhật thêm chi tiết sản phẩm và số tiền sau."
        else:
            return "Vui lòng chỉ định rõ tên khách hàng để tạo báo giá (VD: Tạo quote cho ABC)."

    # ---------------------------------------------------------
    # 9. Báo giá đã được duyệt (status = 'approved')
    # - Điều kiện IF kiểm tra: "báo giá" + "duyệt"
    # ---------------------------------------------------------
    if (
        "báo giá" in q or "bao gia" in q_na
        or "quote" in q
    ) and (
        "duyệt" in q or "duyet" in q_na
        or "approved" in q
    ) and not (
        "chờ" in q
        or "cho duyet" in q_na
        or "cho phe duyet" in q_na
        or "pending" in q
        or "chưa duyệt" in q
        or "chua duyet" in q_na
    ):
        # Câu lệnh SQL: SELECT quote_code, total_amount, status FROM quotes WHERE status = 'approved' ORDER BY total_amount DESC
        rows = fetch_all("""
            SELECT quote_code, total_amount, status
            FROM quotes
            WHERE status = 'approved'
            ORDER BY total_amount DESC
        """)
        return format_quotes(rows, "Báo giá đã được duyệt")

    # ---------------------------------------------------------
    # 10. Báo giá đang chờ duyệt (status = 'pending')
    # - Điều kiện IF kiểm tra: "báo giá" + "chờ" / "pending"
    # ---------------------------------------------------------
    if (
        "báo giá" in q or "bao gia" in q_na
        or "quote" in q
    ) and (
        "chờ" in q or "cho duyet" in q_na or "cho phe duyet" in q_na
        or "pending" in q
        or "chưa duyệt" in q or "chua duyet" in q_na
    ):
        # Câu lệnh SQL: SELECT quote_code, total_amount, status FROM quotes WHERE status = 'pending' ORDER BY total_amount DESC
        rows = fetch_all("""
            SELECT quote_code, total_amount, status
            FROM quotes
            WHERE status = 'pending'
            ORDER BY total_amount DESC
        """)
        return format_quotes(rows, "Báo giá đang chờ duyệt")

    # ---------------------------------------------------------
    # 11. Doanh thu = tổng tiền từ báo giá đã duyệt
    # - Điều kiện IF kiểm tra: "doanh thu"
    # ---------------------------------------------------------
    if "doanh thu" in q:
        # Câu lệnh SQL: SELECT SUM(total_amount) AS total FROM quotes WHERE status = 'approved'
        result = fetch_one("""
            SELECT SUM(total_amount) AS total
            FROM quotes
            WHERE status = 'approved'
        """)
        total = result["total"] or 0
        return f"Doanh thu hiện tại của doanh nghiệp là {total:,.0f} VNĐ (tính từ {total and 'các' or 'chưa có'} báo giá đã được duyệt)."

    # ---------------------------------------------------------
    # 12. Tổng giá trị TẤT CẢ báo giá
    # - Điều kiện IF kiểm tra: "tổng" + "báo giá"
    # ---------------------------------------------------------
    if (
        ("tổng" in q or "tong" in q_na)
        and ("báo giá" in q or "bao gia" in q_na or "quote" in q)
    ):
        # Câu lệnh SQL: SELECT SUM(total_amount) AS total FROM quotes
        result = fetch_one("SELECT SUM(total_amount) AS total FROM quotes")
        total = result["total"] or 0
        return f"Tổng giá trị tất cả báo giá hiện tại: {total:,.0f} VNĐ."

    # ---------------------------------------------------------
    # 13. Liệt kê tất cả báo giá
    # - Điều kiện IF kiểm tra: "báo giá" + "danh sách" / "tất cả"
    # ---------------------------------------------------------
    if (
        "báo giá" in q or "bao gia" in q_na
        or "quote" in q
    ) and (
        "liệt kê" in q or "liet ke" in q_na
        or "danh sách" in q or "danh sach" in q_na
        or "tất cả" in q or "tat ca" in q_na
        or "hiện có" in q or "hien co" in q_na
        or "xem" in q or "nào" in q or "nao" in q_na
    ):
        # Câu lệnh SQL: SELECT quote_code, total_amount, status FROM quotes ORDER BY total_amount DESC LIMIT 20
        rows = fetch_all("""
            SELECT quote_code, total_amount, status
            FROM quotes
            ORDER BY total_amount DESC
            LIMIT 20
        """)
        return format_quotes(rows, "Danh sách báo giá (tối đa 20)")

    # ============================================================
    # MODULE OPPORTUNITY - CƠ HỘI BÁN HÀNG
    # ============================================================

    if (
        "cơ hội" in q or "co hoi" in q_na or "opportunity" in q
    ) and any(term in q or term in q_na for term in (
        "chờ xử lý", "cho xu ly", "đang chờ", "dang cho",
        "chưa xử lý", "chua xu ly",
    )):
        rows = fetch_all("""
            SELECT title, value, stage, probability
            FROM opportunities
            WHERE stage NOT IN ('won', 'lost')
            ORDER BY value DESC
            LIMIT 20
        """)
        return format_opportunities(rows, "Cơ hội đang chờ xử lý")

    # ---------------------------------------------------------
    # 14. Cơ hội có khả năng chốt cao nhất / giá trị cao nhất
    # - Điều kiện IF kiểm tra: "cơ hội" + "cao nhất" / "khả năng chốt"
    # ---------------------------------------------------------
    if (
        "cơ hội" in q or "co hoi" in q_na
        or "opportunity" in q
    ) and (
        "cao nhất" in q or "cao nhat" in q_na
        or "lớn nhất" in q or "lon nhat" in q_na
        or "giá trị" in q or "gia tri" in q_na
        or "khả năng chốt" in q or "kha nang chot" in q_na
        or "tỷ lệ" in q or "ty le" in q_na
        or "top" in q
    ):
        # Sắp xếp theo xác suất (probability) nếu câu hỏi có từ khóa "khả năng" hoặc "tỷ lệ"
        order_col = "probability" if ("khả năng" in q or "kha nang" in q_na or "tỷ lệ" in q or "ty le" in q_na) else "value"
        rows = fetch_all(f"""
            SELECT title, value, stage, probability
            FROM opportunities
            ORDER BY {order_col} DESC
            LIMIT 5
        """)
        return format_opportunities(rows, f"Top 5 cơ hội bán hàng ({'tỷ lệ chốt' if order_col == 'probability' else 'giá trị'} cao nhất)")

    # ---------------------------------------------------------
    # 15. Cơ hội đã thắng (stage = 'won')
    # - Điều kiện IF kiểm tra: "cơ hội" + "thắng" / "won"
    # ---------------------------------------------------------
    if (
        "cơ hội" in q or "co hoi" in q_na
        or "opportunity" in q
    ) and (
        "won" in q
        or "thắng" in q or "thang" in q_na
        or "thành công" in q or "thanh cong" in q_na
    ):
        # Câu lệnh SQL: SELECT title, value, stage, probability FROM opportunities WHERE stage = 'won' ORDER BY value DESC
        rows = fetch_all("""
            SELECT title, value, stage, probability
            FROM opportunities
            WHERE stage = 'won'
            ORDER BY value DESC
        """)
        return format_opportunities(rows, "Cơ hội bán hàng đã thắng")

    # ---------------------------------------------------------
    # 16. Liệt kê tất cả cơ hội bán hàng
    # - Điều kiện IF kiểm tra: "cơ hội"
    # ---------------------------------------------------------
    if (
        "cơ hội" in q or "co hoi" in q_na
        or "opportunity" in q
    ):
        # Câu lệnh SQL: SELECT title, value, stage, probability FROM opportunities ORDER BY value DESC LIMIT 20
        rows = fetch_all("""
            SELECT title, value, stage, probability
            FROM opportunities
            ORDER BY value DESC
            LIMIT 20
        """)
        return format_opportunities(rows, "Danh sách cơ hội bán hàng (tối đa 20)")

    # ============================================================
    # MODULE DASHBOARD - THỐNG KÊ TỔNG QUAN
    # ============================================================

    # ---------------------------------------------------------
    # 17. Thống kê tổng quan hệ thống
    # - Điều kiện IF kiểm tra: "tổng quan" / "dashboard" / "thống kê"
    # ---------------------------------------------------------
    if (
        "tổng quan" in q or "tong quan" in q_na
        or "dashboard" in q
        or "thống kê" in q or "thong ke" in q_na
        or ("tất cả" in q and "bảng" in q)
        or ("tóm tắt" in q or "tom tat" in q_na)
    ):
        # Thực thi 6 câu lệnh SQL lấy chỉ số tổng hợp các bảng
        kh   = fetch_one("SELECT COUNT(*) AS total FROM customers")
        sp   = fetch_one("SELECT COUNT(*) AS total FROM inventory")
        bg   = fetch_one("SELECT COUNT(*) AS total FROM quotes")
        ch   = fetch_one("SELECT COUNT(*) AS total FROM opportunities")
        bk   = fetch_one("SELECT COUNT(*) AS total FROM bookings")
        dt   = fetch_one("SELECT SUM(total_amount) AS total FROM quotes WHERE status='approved'")
        return (
            f"Thống kê tổng quan hệ thống:\n"
            f"- Khách hàng   : {kh['total']} người\n"
            f"- Sản phẩm kho : {sp['total']} sản phẩm\n"
            f"- Báo giá      : {bg['total']} báo giá\n"
            f"- Cơ hội KD    : {ch['total']} cơ hội\n"
            f"- Booking      : {bk['total']} giao dịch\n"
            f"- Doanh thu DK : {(dt['total'] or 0):,.0f} VNĐ"
        )

    # ============================================================
    # KHÔNG KHỚP TỪ KHÓA NÀO
    # ============================================================
    return "Hệ thống chưa có truy vấn SQL phù hợp cho câu hỏi này."


# ==========================================================
# Khối lệnh kiểm tra điểm chạy trực tiếp (Main Execution Entry Point):
# - __name__ là gì: Biến môi trường chứa tên module.
# - __main__ là gì: Giá trị khi thực thi trực tiếp script này (`python sql_service.py`).
# - Vì sao phải dùng: Cho phép test thử 12 mẫu câu hỏi SQL trực tiếp trên màn hình console mà không cần khởi động Flask server.
# - Khi import module này sang file khác: __name__ != "__main__" -> Ngăn khối lệnh test tự động thực thi.
# - Khi chạy trực tiếp: __name__ == "__main__" -> Chạy vòng lặp test 12 câu hỏi và in ngữ cảnh CSDL thu được.
# ==========================================================
if __name__ == "__main__":
    test_questions = [
        "Có bao nhiêu khách hàng?",
        "Liệt kê khách hàng VIP",
        "Khách hàng nào đang tiềm năng?",
        "Danh sách tất cả khách hàng",
        "Sản phẩm nào sắp hết hàng?",
        "Liệt kê tất cả sản phẩm trong kho",
        "Báo giá nào đã được duyệt?",
        "Báo giá nào đang chờ duyệt?",
        "Cơ hội nào có giá trị cao nhất?",
        "Liệt kê tất cả cơ hội bán hàng",
        "Doanh thu hiện tại là bao nhiêu?",
        "Thống kê tổng quan hệ thống",
    ]

    # Vòng lặp FOR: Duyệt qua từng câu hỏi thử nghiệm Text-to-SQL
    for q in test_questions:
        print(f"\nCâu hỏi: {q}")
        print("-" * 50)
        print(answer_sql_question(q))