# Kiểm thử pipeline trả lời AI với bằng chứng dữ liệu và API model tùy cấu hình.
import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.

import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.


from routing import route_question  # Chọn nhánh SQL hoặc RAG cho câu hỏi.
from sql_service import answer_sql_question  # Lấy bằng chứng có cấu trúc từ MySQL.
from rag_service import search_documents  # Tìm tài liệu nằm trong phạm vi quyền.
from ai_service import generate_answer  # Gửi câu hỏi và bằng chứng tới model Groq.
from access_control import create_session  # Dùng session, intent và quyền của chatbot.

pytestmark = pytest.mark.skipif(not os.getenv('GROQ_API_KEY'), reason='GROQ_API_KEY is not configured')


# Kiểm tra định tuyến, truy xuất bằng chứng và câu trả lời với API thật.
@pytest.mark.parametrize('question', ['SH 160i giá bao nhiêu?', 'Thủ tục trả góp?'])
def test_with_real_data(question):
    print("=" * 60)
    print(f"Câu hỏi : {question}")

    # Lấy loại xử lý và module hiển thị từ bộ định tuyến.
    route = route_question(question)
    question_type = route["type"]    # "SQL" hoặc "RAG"
    module        = route["module"]  # Tên module nghiệp vụ

    print(f"Loại    : {question_type}")
    print(f"Module  : {module}")

    # Dùng cùng session để audit quyền trước khi truy vấn SQL hoặc tài liệu.
    session_id = create_session(None)
    if question_type == "SQL":
        # Truy vấn dữ liệu có cấu trúc trong MySQL.
        context = answer_sql_question(question, session_id=session_id)
        print(f"Context :\n{context.strip()}")
    else:
        # Tìm tài liệu được phép đọc trước khi gọi model.
        context = search_documents(question, session_id=session_id)
        print(f"Context :\n{context.strip()}")

    # Gửi câu hỏi cùng bằng chứng đã truy xuất tới model.
    answer = generate_answer(question, context)

    print(f"Groq AI :\n{answer.strip()}")
    print("=" * 60)
    print()

    assert isinstance(answer, str) and answer.strip()


# Chạy các câu hỏi mẫu chỉ khi gọi file trực tiếp.
if __name__ == "__main__":

    print("\nB11 - Kiểm tra pipeline SQL + RAG với dữ liệu thật\n")

    # Danh sách gồm các chủ đề dữ liệu có cấu trúc và tài liệu.
    test_questions = [
        # --- SQL - CRM ---
        "Có bao nhiêu khách hàng?",
        "Khách hàng nào là VIP?",
        "Khách hàng nào đang ở trạng thái tiềm năng?",

        # --- SQL - Warehouse ---
        "Sản phẩm nào sắp hết hàng?",

        # --- SQL - Quote ---
        "Báo giá nào đã được duyệt?",
        "Doanh thu hiện tại là bao nhiêu?",

        # --- SQL - Opportunity ---
        "Cơ hội bán hàng nào có giá trị cao nhất?",

        # --- RAG - Tài liệu nội bộ ---
        "Chính sách bảo hành là gì?",
        "Quy định chăm sóc khách hàng như thế nào?",
        "Hướng dẫn sử dụng AI Chat?",
    ]

    # Chạy pipeline lần lượt cho từng câu hỏi mẫu.
    for q in test_questions:
        test_with_real_data(q)
