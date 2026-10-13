# ==========================================================
# Tên file: test_ai.py
# Mục đích của file: Script kiểm thử tích hợp (Integration Testing) toàn bộ hệ thống AI Chatbot (kết hợp cả SQL và RAG).
# File này dùng để làm gì:
#   - Đánh giá khả năng xử lý hoàn chỉnh của ứng dụng trên dữ liệu thật.
#   - Phân loại câu hỏi thông qua `routing.route_question`.
#   - Tự động điều hướng: Nếu SQL -> lấy dữ liệu CSDL từ `sql_service`; Nếu RAG -> tìm kiếm tài liệu từ `rag_service`.
#   - Truyền ngữ cảnh thật vào `ai_service.generate_answer` để kiểm tra kết quả sinh câu trả lời tự nhiên do Groq AI (Llama 3.3 70B) tạo ra.
# Khi nào file được gọi:
#   - Được thực thi trực tiếp từ dòng lệnh (`python test_ai.py`) để kiểm định toàn diện chất lượng phản hồi của hệ thống.
# Luồng hoạt động tổng quát:
#   Câu hỏi thử nghiệm
#           ↓
#   [routing.route_question -> Xác định "SQL" hoặc "RAG" & Module]
#           ↓
#   [Điều hướng linh hoạt: SQL -> sql_service | RAG -> rag_service]
#           ↓
#   [ai_service.generate_answer -> Groq LLM sinh phản hồi]
#           ↓
#   [In nhật ký kiểm thử chi tiết và trả về kết quả]
# ==========================================================

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY is not configured",
)

from routing import route_question          # Phân loại SQL hay RAG
from sql_service import answer_sql_question # Lấy dữ liệu thật từ database
from rag_service import search_documents    # Tìm tài liệu thật từ bảng documents
from ai_service import generate_answer      # Gọi Groq AI sinh câu trả lời


# ==========================================================
# Hàm test_with_real_data:
# - Hàm dùng để làm gì: Chạy toàn bộ pipeline xử lý tích hợp (Routing -> Data Retrieval -> LLM Generation) cho một câu hỏi test.
# - Tham số đầu vào:
#     + question (str): Câu hỏi muốn kiểm tra.
# - Giá trị trả về:
#     + str: Phản hồi văn bản bằng tiếng Việt do Groq AI tạo ra.
# - Hàm này được gọi ở đâu: Được gọi trong vòng lặp FOR ở khối `if __name__ == "__main__":`.
# - Vai trò trong hệ thống: Hàm thực thi kiểm thử tích hợp toàn trình (End-to-End Test Case Runner).
# ==========================================================
def test_with_real_data(question):
    """
    Chạy toàn bộ pipeline: câu hỏi → routing → lấy dữ liệu → AI trả lời.

    Args:
        question (str): Câu hỏi muốn kiểm tra

    Returns:
        str: Câu trả lời từ Groq AI
    """

    print("=" * 60)
    print(f"Câu hỏi : {question}")

    # ---------------------------------------------------------
    # Bước 1 trong hàm: Phân loại câu hỏi bằng routing.py
    # ---------------------------------------------------------
    route = route_question(question)
    question_type = route["type"]    # "SQL" hoặc "RAG"
    module        = route["module"]  # Tên module nghiệp vụ

    print(f"Loại    : {question_type}")
    print(f"Module  : {module}")

    # ---------------------------------------------------------
    # Bước 2 trong hàm: Điều hướng lấy dữ liệu context từ nguồn phù hợp
    # - Điều kiện IF / ELSE:
    #     + Khi TRUE (SQL): Lấy ngữ cảnh từ CSDL SQLite thông qua `answer_sql_question(question)`.
    #     + Khi FALSE (RAG): Tìm kiếm văn bản tài liệu liên quan từ `search_documents(question)`.
    # ---------------------------------------------------------
    if question_type == "SQL":
        # Truy vấn database thật → trả về chuỗi kết quả
        context = answer_sql_question(question)
        print(f"Context :\n{context.strip()}")
    else:
        # RAG → tìm tài liệu thật từ bảng documents
        context = search_documents(question)
        print(f"Context :\n{context.strip()}")

    # ---------------------------------------------------------
    # Bước 3 trong hàm: Gửi (question + context) sang Groq AI để sinh câu trả lời tự nhiên
    # ---------------------------------------------------------
    answer = generate_answer(question, context)

    print(f"Groq AI :\n{answer.strip()}")
    print("=" * 60)
    print()

    # ---------------------------------------------------------
    # Bước 4 trong hàm: Trả về câu trả lời
    # ---------------------------------------------------------
    return answer


# ==========================================================
# Khối lệnh kiểm tra điểm chạy trực tiếp (Main Execution Entry Point):
# - __name__ là gì: Biến hệ thống Python chứa tên của module.
# - __main__ là gì: Giá trị chuỗi mặc định khi file được chạy trực tiếp (`python test_ai.py`).
# - Vì sao phải dùng: Ngăn việc tự động khởi chạy bộ test khi module này được import ở nơi khác.
# - Khi import: __name__ != "__main__" -> Không chạy bộ test.
# - Khi chạy trực tiếp: __name__ == "__main__" -> Duyệt qua 10 câu hỏi test tổng hợp cả SQL và RAG.
# ==========================================================
if __name__ == "__main__":

    print("\nB11 - Kiểm tra pipeline SQL + RAG với dữ liệu thật\n")

    # Danh sách các câu hỏi kiểm tra bao gồm cả SQL và RAG
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

    # ---------------------------------------------------------
    # Vòng lặp FOR: Duyệt qua từng câu hỏi trong danh sách test_questions
    # - Vòng lặp duyệt cái gì: Duyệt từng chuỗi câu hỏi q trong `test_questions`.
    # - Mỗi lần lặp xử lý gì: Gọi hàm `test_with_real_data(q)`.
    # - Khi kết thúc vòng lặp thu được gì: Hoàn tất quá trình test tích hợp toàn diện.
    # ---------------------------------------------------------
    for q in test_questions:
        test_with_real_data(q)
