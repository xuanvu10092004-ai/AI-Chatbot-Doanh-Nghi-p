# ==========================================================
# Tên file: test_sql.py
# Mục đích của file: Script kiểm thử tự động toàn bộ pipeline xử lý Text-to-SQL độc lập.
# File này dùng để làm gì:
#   - Nhận danh sách các câu hỏi test thuộc luồng SQL.
#   - Gọi `routing.route_question` để phân loại và xác định module.
#   - Gọi `sql_service.answer_sql_question` để truy vấn CSDL SQLite lấy dữ liệu ngữ cảnh thực tế (context).
#   - Gọi `ai_service.generate_answer` truyền context tới Groq AI LLM sinh câu trả lời tự nhiên.
#   - In kết quả kiểm thử (Loại, Module, Context, Groq AI response) ra màn hình terminal.
# Khi nào file được gọi:
#   - Được lập trình viên/sinh viên chạy trực tiếp từ terminal (`python test_sql.py`) để đánh giá chất lượng phản hồi của luồng SQL.
# Luồng hoạt động tổng quát:
#   Câu hỏi thử nghiệm
#           ↓
#   [routing.route_question -> Xác định "SQL" & tên Module]
#           ↓
#   [sql_service.answer_sql_question -> Truy vấn SQLite lấy dữ liệu]
#           ↓
#   [ai_service.generate_answer -> Groq AI sinh văn bản trả lời]
#           ↓
#   [In nhật ký kiểm thử chi tiết ra màn hình Terminal]
# ==========================================================

from routing import route_question           # Phân loại câu hỏi: SQL hay RAG
from sql_service import answer_sql_question  # Truy vấn database lấy context thật
from ai_service import generate_answer       # Gọi Groq AI sinh câu trả lời tự nhiên


# ==========================================================
# Hàm test_pipeline:
# - Hàm dùng để làm gì: Thực thi quy trình kiểm thử 3 bước cho một câu hỏi đơn lẻ và in ra màn hình.
# - Tham số đầu vào:
#     + question (str): Câu hỏi thử nghiệm.
# - Giá trị trả về: Không có (None).
# - Hàm này được gọi ở đâu: Được gọi trong vòng lặp FOR ở khối `if __name__ == "__main__":`.
# - Vai trò trong hệ thống: Hàm thực thi một kịch bản test (Test Runner).
# ==========================================================
def test_pipeline(question):
    """
    Chạy toàn bộ pipeline cho một câu hỏi:
    routing -> sql_service -> ai_service -> in kết quả.

    Args:
        question (str): Câu hỏi muốn kiểm tra
    """
    print("=" * 60)
    print(f"Câu hỏi : {question}")

    # ---------------------------------------------------------
    # Bước 1 trong hàm: Phân loại câu hỏi bằng routing.py
    # ---------------------------------------------------------
    route         = route_question(question)
    question_type = route["type"]    # "SQL" hoặc "RAG"
    module        = route["module"]  # Tên module nghiệp vụ

    print(f"Loại    : {question_type}")
    print(f"Module  : {module}")

    # ---------------------------------------------------------
    # Bước 2 trong hàm: Lấy context dữ liệu từ cơ sở dữ liệu SQLite
    # - Điều kiện IF / ELSE:
    #     + Khi TRUE (SQL): Gọi `answer_sql_question(question)` lấy ngữ cảnh thực tế từ `database.db`.
    #     + Khi FALSE (RAG): Đặt giá trị thông báo bỏ qua RAG trong file test này.
    # ---------------------------------------------------------
    if question_type == "SQL":
        context = answer_sql_question(question)
    else:
        context = "(RAG - không xử lý trong file test này)"

    print(f"Context :\n{context}")

    # ---------------------------------------------------------
    # Bước 3 trong hàm: Truyền (question + context) vào Groq AI sinh câu trả lời tự nhiên
    # ---------------------------------------------------------
    answer = generate_answer(question, context)
    print(f"Groq AI :\n{answer.strip()}")
    print("=" * 60)
    print()


# ==========================================================
# Khối lệnh kiểm tra điểm chạy trực tiếp (Main Execution Entry Point):
# - __name__ là gì: Biến hệ thống Python lưu tên file.
# - __main__ là gì: Giá trị chuỗi mặc định khi file được chạy trực tiếp (`python test_sql.py`).
# - Vì sao phải dùng: Bảo đảm danh sách bộ test chỉ chạy khi thực thi trực tiếp script này.
# - Khi import sang file khác: __name__ != "__main__" -> Ngăn việc chạy tự động bộ test.
# - Khi chạy trực tiếp: __name__ == "__main__" -> Chạy duyệt danh sách 11 câu hỏi test cases.
# ==========================================================
if __name__ == "__main__":

    print("\nKiểm tra pipeline SQL + Groq AI với dữ liệu thật\n")

    # Danh sách câu hỏi test cases thuộc 5 module nghiệp vụ khác nhau
    test_cases = [
        # --- CRM ---
        "Có bao nhiêu khách hàng?",
        "Liệt kê khách hàng VIP",
        "Khách hàng nào đang tiềm năng?",
        "Cho tôi danh sách tất cả khách hàng",

        # --- Warehouse ---
        "Sản phẩm nào sắp hết hàng?",
        "Liệt kê tất cả sản phẩm trong kho",

        # --- Quote ---
        "Báo giá nào đã được duyệt?",
        "Doanh thu hiện tại là bao nhiêu?",

        # --- Opportunity ---
        "Cơ hội nào có giá trị cao nhất?",
        "Liệt kê tất cả cơ hội bán hàng",

        # --- Dashboard ---
        "Thống kê tổng quan hệ thống",
    ]

    # ---------------------------------------------------------
    # Vòng lặp FOR: Duyệt từng câu hỏi trong danh sách test_cases để chạy kiểm thử
    # - Vòng lặp duyệt cái gì: Duyệt chuỗi câu hỏi q trong danh sách `test_cases`.
    # - Mỗi lần lặp xử lý gì: Gọi hàm `test_pipeline(q)`.
    # - Khi kết thúc vòng lặp thu được gì: Hoàn tất in báo cáo test toàn bộ 11 câu hỏi mẫu.
    # ---------------------------------------------------------
    for q in test_cases:
        test_pipeline(q)
