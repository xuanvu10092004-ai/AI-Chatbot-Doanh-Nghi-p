# ==========================================================
# Tên file: import_excel_to_db.py
# Mục đích của file: Đọc dữ liệu từ file Excel và nạp (import) vào Cơ sở dữ liệu SQLite (database.db).
# File này dùng để làm gì:
#   - Đọc từng trang (sheet) trong file Excel `data_ai_chatbot_doanh_nghiep.xlsx`.
#   - Ánh xạ (rename) tên cột tiêu đề tiếng Việt có chứa chú thích về chuẩn tên cột trong CSDL SQLite.
#   - Xóa dữ liệu cũ (reset bảng và giá trị AUTO INCREMENT) trước khi chèn dữ liệu mới.
#   - Làm sạch dữ liệu rỗng (bỏ dòng trống, chuyển NaN thành None tương thích với NULL của SQLite).
#   - Ghi dữ liệu vào từng bảng tương ứng (`customers`, `inventory`, `opportunities`, `quotes`, `documents`, `chat_logs`).
# Khi nào file được gọi:
#   - Chạy thủ công từ dòng lệnh khi cần khởi tạo hoặc khôi phục lại dữ liệu mẫu từ Excel vào database.
# Luồng hoạt động tổng quát:
#   [Đọc cấu hình file Excel]
#           ↓
#   [Mở kết nối SQLite & Bật khóa ngoại]
#           ↓
#   [Xóa dữ liệu cũ theo thứ tự xóa bảng con trước, bảng cha sau]
#           ↓
#   [Reset bảng sqlite_sequence cho các ID tự tăng]
#           ↓
#   [Vòng lặp qua từng Sheet Excel: Đọc -> Rename cột -> Bỏ dòng rỗng -> Lọc cột hợp lệ -> to_sql()]
#           ↓
#   [Đóng kết nối CSDL và thông báo hoàn tất]
# ==========================================================

import sys
import sqlite3
import pandas as pd  # Thư viện đọc và xử lý bảng dữ liệu Pandas
from database_path import DATABASE_PATH, EXCEL_PATH

# Cấu hình lại mã hóa đầu ra của console thành UTF-8 để không bị lỗi hiển thị tiếng Việt trên Terminal Windows
sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------
# Khai báo tên file CSDL SQLite và file Excel đầu vào
# ---------------------------------------------------------
DB_NAME = str(DATABASE_PATH)
EXCEL_FILE = str(EXCEL_PATH)

# ---------------------------------------------------------
# Từ điển (Dictionary) ánh xạ tên cột từ Excel sang tên cột chuẩn trong SQLite
# ---------------------------------------------------------
COLUMN_RENAME_MAP = {
    # Sheet: inventory (Sản phẩm & Tồn kho)
    "product_name (Tên sản phẩm/dịch vụ)":                   "product_name",
    "category (Nhóm sản phẩm)":                               "category",
    "quantity ( Số lượng tồn kho)":                           "quantity",
    "unit (Đơn vị tính)":                                     "unit",
    "price ( Giá sản phẩm )":                                 "price",
    "supplier ( Nhà cung cấp / Bộ phận phụ trách)":           "supplier",
    "created_at ( Ngày tạo dữ liệu )":                        "created_at",

    # Sheet: opportunities (Cơ hội bán hàng)
    "id ":                                                     "id",
    "customer_id (Mã khách hàng liên quan)":                  "customer_id",
    "title ( Tên cơ hội bán hàng )":                          "title",
    "description ( Mô tả chi tiết cơ hội )":                  "description",
    "value ( Giá trị cơ hội )":                               "value",
    "stage ( Giai đoạn bán hàng )":                           "stage",
    "probability ( Xác suất chốt (%))":                       "probability",
    "expected_close_date ( Ngày dự kiến chốt)":               "expected_close_date",
    "created_at ( Ngày tạo cơ hội )":                         "created_at",

    # Sheet: quotes (Báo giá)
    "customer_id ( Mã khách hàng)":                           "customer_id",
    "product_id ( Mã sản phẩm )":                             "product_id",
    "quote_code ( Mã báo giá)":                               "quote_code",
    "quantity ( Số lượng )":                                   "quantity",
    "total_amount ( Tổng tiền)":                              "total_amount",
    "status (Trạng thái)":                                     "status",
    "created_at ( Ngày tạo )":                                "created_at",
}


# ==========================================================
# Hàm get_table_columns:
# - Hàm dùng để làm gì: Trích xuất danh sách các tên cột hiện có của một bảng trong SQLite.
# - Tham số đầu vào:
#     + cursor: Đối tượng con trỏ SQLite đang kết nối.
#     + table_name (str): Tên bảng cần lấy danh sách cột (VD: 'customers').
# - Giá trị trả về:
#     + list[str]: Danh sách tên các cột dạng chuỗi (VD: ['id', 'name', 'phone', ...]).
# - Hàm này được gọi ở đâu: Được gọi bên trong hàm `import_excel_to_db()` tại bước lọc cột hợp lệ trước khi chèn SQL.
# - Vai trò trong hệ thống: Hàm tiện ích giúp kiểm tra cấu trúc Schema động.
# ==========================================================
def get_table_columns(cursor, table_name):
    """
    Lấy danh sách tên cột của một bảng trong database.
    Dùng để lọc chỉ import những cột hợp lệ từ Excel.

    Args:
        cursor: Con trỏ database SQLite
        table_name (str): Tên bảng cần lấy cột

    Returns:
        list[str]: Danh sách tên cột trong bảng
    """
    # ---------------------------------------------------------
    # Câu lệnh SQL: PRAGMA table_info(table_name)
    # - Thao tác dùng để làm gì: Lấy danh sách siêu dữ liệu (metadata) của bảng.
    # - Trả về các tuple chứa: (cid, name, type, notnull, dflt_value, pk).
    # - Vòng lặp list comprehension: Duyệt qua kết quả fetchall() để trích lấy phần tử column[1] (tên cột).
    # ---------------------------------------------------------
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [column[1] for column in cursor.fetchall()]


# ==========================================================
# Hàm import_excel_to_db:
# - Hàm dùng để làm gì: Đọc file Excel, dọn dẹp CSDL cũ, làm sạch dữ liệu và nạp dữ liệu mới vào SQLite.
# - Tham số đầu vào: Không có.
# - Giá trị trả về: Không có (None).
# - Hàm này được gọi ở đâu: Được gọi trực tiếp trong khối `if __name__ == "__main__":`.
# - Vai trò trong hệ thống: Bộ điều phối quá trình ETL (Extract - Transform - Load dữ liệu Excel).
# ==========================================================
def import_excel_to_db():
    """
    Hàm chính thực hiện import toàn bộ dữ liệu từ Excel vào database.

    Quy trình:
    1. Kết nối database
    2. XÓA SẠCH toàn bộ dữ liệu cũ (theo thứ tự tránh lỗi khóa ngoại)
    3. Reset ID tự tăng (AUTO INCREMENT)
    4. Đọc từng sheet từ file Excel
    5. Đổi tên cột (nếu cần) để khớp với tên cột trong database
    6. Làm sạch dữ liệu (bỏ dòng rỗng, thay NaN bằng None)
    7. Lọc chỉ giữ cột hợp lệ với database
    8. Ghi dữ liệu vào bảng tương ứng
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Khởi tạo kết nối CSDL và bật khóa ngoại
    # - Bước này đang làm gì: Tạo đối tượng conn/cursor và bật PRAGMA foreign_keys = ON.
    # - Vì sao cần bước này: Đảm bảo duy trì tính toàn vẹn dữ liệu chuẩn relational database.
    # ---------------------------------------------------------
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON")

    # ---------------------------------------------------------
    # Bước 2 trong hàm: Khai báo danh sách các bảng cần dọn dẹp
    # - Thứ tự xóa cực kỳ QUAN TRỌNG:
    #     1. `chat_logs`     : Độc lập
    #     2. `quotes`        : Bảng con (chứa khóa ngoại tới customers và inventory) -> Phải xóa TRƯỚC
    #     3. `opportunities` : Bảng con (chứa khóa ngoại tới customers) -> Phải xóa TRƯỚC
    #     4. `documents`     : Độc lập
    #     5. `inventory`     : Bảng cha
    #     6. `customers`     : Bảng cha
    # ---------------------------------------------------------
    tables = [
        "chat_logs",     # Không có khóa ngoại -> xóa trước cũng được
        "quotes",        # Tham chiếu customers và inventory
        "opportunities", # Tham chiếu customers
        "documents",     # Không có khóa ngoại
        "inventory",     # Bảng cha (được tham chiếu bởi quotes)
        "customers"      # Bảng cha (được tham chiếu bởi quotes, opportunities)
    ]

    # ---------------------------------------------------------
    # Vòng lặp FOR 1: Xóa dữ liệu cũ trong các bảng
    # - Vòng lặp duyệt cái gì: Duyệt qua từng tên bảng trong danh sách `tables`.
    # - Mỗi lần lặp xử lý gì: Thực thi câu lệnh SQL `DELETE FROM <table_name>`.
    # - Khi kết thúc vòng lặp sẽ thu được gì: Tất cả 6 bảng dữ liệu được dọn dẹp về trạng thái rỗng.
    # ---------------------------------------------------------
    for table in tables:
        # Câu lệnh SQL: DELETE FROM <table_name>
        # Giải thích: Xóa toàn bộ các dòng dữ liệu đang có trong bảng.
        cursor.execute(f"DELETE FROM {table}")

    # ---------------------------------------------------------
    # Vòng lặp FOR 2: Reset chỉ số tự tăng (AUTOINCREMENT) trong SQLite
    # - Vòng lặp duyệt cái gì: Duyệt qua từng tên bảng trong danh sách `tables`.
    # - Mỗi lần lặp xử lý gì: Thực thi SQL xóa bản ghi quản lý chuỗi ID trong bảng hệ thống `sqlite_sequence`.
    # - Khi kết thúc vòng lặp sẽ thu được gì: Chỉ số ID tự tăng của các bảng sẽ bắt đầu lại từ 1 khi chèn bản ghi mới.
    # ---------------------------------------------------------
    for table in tables:
        # Câu lệnh SQL: DELETE FROM sqlite_sequence WHERE name = ?
        # Giải thích: Reset bộ đếm ID tự tăng của SQLite về 0 cho bảng tương ứng.
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))

    # Lưu thay đổi dọn dẹp dữ liệu cũ vào ổ đĩa
    conn.commit()

    # ---------------------------------------------------------
    # Bước 3 trong hàm: Ánh xạ Tên Sheet trong Excel -> Tên Bảng tương ứng trong SQLite
    # ---------------------------------------------------------
    sheet_table_map = {
        "customers": "customers",
        "inventory": "inventory",
        "opportunities": "opportunities",
        "quotes": "quotes",
        "documents": "documents",
        "chat_logs": "chat_logs"
    }

    # ---------------------------------------------------------
    # Vòng lặp FOR 3: Đọc, làm sạch và nạp dữ liệu từng sheet từ Excel vào Database
    # - Vòng lặp duyệt cái gì: Duyệt qua từng cặp (sheet_name, table_name) trong `sheet_table_map.items()`.
    # - Mỗi lần lặp xử lý gì:
    #     1. Đọc sheet Excel thành Pandas DataFrame (`pd.read_excel`).
    #     2. Đổi tên cột theo `COLUMN_RENAME_MAP`.
    #     3. Loại bỏ các dòng trống hoàn toàn (`dropna(how="all")`).
    #     4. Chuyển giá trị thiếu NaN thành None (`where(pd.notnull(df), None)`).
    #     5. Lọc chỉ lấy các cột trùng với cấu trúc bảng trong CSDL.
    #     6. Thực hiện `df.to_sql(..., if_exists="append")` để chèn dữ liệu.
    # - Khi kết thúc vòng lặp sẽ thu được gì: Toàn bộ dữ liệu từ Excel đã được lưu an toàn vào database.db.
    # ---------------------------------------------------------
    for sheet_name, table_name in sheet_table_map.items():
        # Đọc dữ liệu từ file Excel vào DataFrame
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)

        # ---------------------------------------------------------
        # Đổi tên cột theo bảng ánh xạ COLUMN_RENAME_MAP
        # ---------------------------------------------------------
        df = df.rename(columns=COLUMN_RENAME_MAP)

        # ---------------------------------------------------------
        # Làm sạch dữ liệu
        # - dropna(how="all"): Bỏ dòng rỗng toàn bộ.
        # - where(pd.notnull(df), None): Thay NaN bằng None (SQLite nhận diện thành NULL).
        # ---------------------------------------------------------
        df = df.dropna(how="all")
        df = df.where(pd.notnull(df), None)

        # Trích xuất danh sách cột thực tế của bảng CSDL
        table_columns = get_table_columns(cursor, table_name)

        # Lọc danh sách cột hợp lệ có mặt ở cả Excel và SQLite Schema
        valid_columns = [col for col in df.columns if col in table_columns]
        df = df[valid_columns]

        # ---------------------------------------------------------
        # Thao tác chèn dữ liệu: df.to_sql()
        # - if_exists="append": Thêm mới các dòng dữ liệu vào bảng đã có sẵn cấu trúc.
        # - index=False: Không lưu chỉ số dòng 0, 1, 2... của Pandas vào CSDL.
        # ---------------------------------------------------------
        df.to_sql(
            table_name,
            conn,
            if_exists="append",  # Thêm dữ liệu vào bảng đã tồn tại
            index=False          # Không ghi index của pandas vào database
        )

        print(f"Đã import sheet '{sheet_name}' -> bảng '{table_name}': {len(df)} dòng, cột: {list(df.columns)}")

    # ---------------------------------------------------------
    # Bước 4 trong hàm: Đóng kết nối CSDL và kết thúc
    # ---------------------------------------------------------
    conn.close()
    print("\nImport dữ liệu từ Excel vào database.db thành công!")


# ==========================================================
# Khối lệnh kiểm tra điểm chạy trực tiếp (Main Execution Entry Point):
# - __name__ là gì: Biến hệ thống Python lưu tên module.
# - __main__ là gì: Giá trị khi file được chạy trực tiếp từ dòng lệnh.
# - Vì sao phải dùng: Ngăn việc tự động xóa và nạp dữ liệu khi file này được import ở nơi khác.
# - Khi import module này: __name__ != "__main__" -> Không chạy import_excel_to_db().
# - Khi chạy trực tiếp (`python import_excel_to_db.py`): __name__ == "__main__" -> Thực thi quá trình import.
# ==========================================================
if __name__ == "__main__":
    import_excel_to_db()