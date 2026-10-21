# Kiểm thử phân loại câu hỏi và truy vấn SQL trên dữ liệu mô phỏng.
__test__ = False
from routing import route_question  # Chọn luồng SQL hoặc RAG cho câu hỏi.
from sql_service import answer_sql_question  # Lấy dữ liệu có cấu trúc từ MySQL.
from ai_service import generate_answer  # Diễn đạt bằng chứng thành câu trả lời tiếng Việt.


# Kiểm thử việc định tuyến, truy vấn SQL và gọi model với một câu hỏi.
def test_pipeline(question):
    print("=" * 60)
    print(f"Câu hỏi : {question}")

    # Lấy loại xử lý và nhãn module để chọn nguồn dữ liệu.
    route         = route_question(question)
    question_type = route["type"]    # "SQL" hoặc "RAG"
    module        = route["module"]  # Tên module nghiệp vụ

    print(f"Loại    : {question_type}")
    print(f"Module  : {module}")

    # File này chỉ gọi SQL; câu hỏi RAG được đánh dấu là chưa xử lý.
    if question_type == "SQL":
        context = answer_sql_question(question)
    else:
        context = "(RAG - không xử lý trong file test này)"

    print(f"Context :\n{context}")

    # Gửi câu hỏi và context tới model để in câu trả lời.
    answer = generate_answer(question, context)
    print(f"Groq AI :\n{answer.strip()}")
    print("=" * 60)
    print()


# Chạy danh sách câu hỏi mẫu chỉ khi gọi file trực tiếp.
if __name__ == "__main__":

    print("\nKiểm tra pipeline SQL + Groq AI với dữ liệu thật\n")

    # Gồm câu hỏi khách hàng, kho, báo giá, cơ hội và dashboard.
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

    # Chạy lần lượt pipeline cho từng câu hỏi mẫu.
    for q in test_cases:
        test_pipeline(q)
