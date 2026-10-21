# File này chuẩn hóa câu hỏi và chọn luồng SQL, RAG hoặc thao tác nghiệp vụ.
import unicodedata  # Chuẩn hóa Unicode và bỏ dấu tiếng Việt khi phân loại từ khóa.
from question_language import wants_sql  # Nhận diện câu hỏi xe/số liệu cần truy vấn SQL.


# Bỏ dấu tiếng Việt để từ khóa không phụ thuộc người dùng gõ có dấu hay không.
def remove_vietnamese_accents(text):
    text = unicodedata.normalize("NFD", text.replace('đ', 'd').replace('Đ', 'D'))
    text = text.encode("ascii", "ignore").decode("utf-8")
    return text


# Trả cả câu thường có dấu và bản không dấu để các từ khóa dễ khớp hơn.
def normalize_question(question):
    question = question.lower().strip()
    question_no_accent = remove_vietnamese_accents(question)
    return question, question_no_accent


# Ưu tiên từ khóa chính sách/tài liệu trước từ khóa dữ liệu có cấu trúc.
def classify_question(question):
    question, question_no_accent = normalize_question(question)

    # Câu hỏi có các từ này được đưa sang tìm kiếm tài liệu.
    rag_keywords = [
        "chính sách", "chinh sach",
        "quy định", "quy dinh",
        "hướng dẫn", "huong dan",
        "tài liệu", "tai lieu",
        "rag",
        "api key",
        "bảo mật", "bao mat",
        "quy trình", "quy trinh",
        "mô tả hệ thống", "mo ta he thong",
        "cách hoạt động", "cach hoat dong",
        "bàn giao", "ban giao",
        "nội bộ", "noi bo",
        "bảo hành", "bao hanh",
        "hỗ trợ", "ho tro",
        "ai chat", "chatbot",
        "triển khai", "trien khai"
    ]

    # Câu hỏi về bản ghi nghiệp vụ được đưa sang truy vấn có cấu trúc.
    sql_keywords = [
        "khách hàng", "khach hang",
        "customer",
        "crm",
        "sản phẩm", "san pham",
        "tồn kho", "ton kho",
        "kho",
        "inventory",
        "báo giá", "bao gia",
        "quote",
        "cơ hội", "co hoi",
        "opportunity",
        "doanh thu",
        "số lượng", "so luong",
        "tổng", "tong",
        "bao nhiêu", "bao nhieu",
        "danh sách", "danh sach",
        "vip",
        "tiềm năng", "tiem nang",
        "đã duyệt", "da duyet",
        "sắp hết hàng", "sap het hang",
        "liệt kê", "liet ke",
        "tóm tắt", "tom tat"
    ]

    # Kiểm tra RAG trước để câu hỏi về quy định báo giá không bị hiểu thành tra giá.
    for keyword in rag_keywords:
        if keyword in question or keyword in question_no_accent:
            return "RAG"

    # Chỉ phân loại SQL sau khi đã loại trừ câu hỏi tài liệu/chính sách.
    for keyword in sql_keywords:
        if keyword in question or keyword in question_no_accent:
            return "SQL"

    # Không khớp chủ đề dữ liệu thì mặc định tra cứu tài liệu.
    return "RAG"


# Gán nhãn module theo nhóm từ khóa; các điều kiện được kiểm tra theo thứ tự ưu tiên.
def detect_module(question):
    question, question_no_accent = normalize_question(question)

    # Khách hàng được ưu tiên trước các nhóm nghiệp vụ còn lại.
    if (
        "khách hàng" in question
        or "khach hang" in question_no_accent
        or "crm" in question
        or "customer" in question
    ):
        return "AI CRM"

    if (
        "sản phẩm" in question
        or "san pham" in question_no_accent
        or "kho" in question
        or "tồn kho" in question
        or "ton kho" in question_no_accent
        or "inventory" in question
    ):
        return "AI Warehouse"

    if (
        "báo giá" in question
        or "bao gia" in question_no_accent
        or "quote" in question
    ):
        return "AI Quote"

    if (
        "cơ hội" in question
        or "co hoi" in question_no_accent
        or "opportunity" in question
    ):
        return "AI Opportunity"

    if (
        "dashboard" in question
        or "doanh thu" in question
        or "thống kê" in question
        or "thong ke" in question_no_accent
        or "tổng quan" in question
        or "tong quan" in question_no_accent
        or "tóm tắt" in question
        or "tom tat" in question_no_accent
    ):
        return "AI Dashboard"

    if (
        "chính sách" in question
        or "chinh sach" in question_no_accent
        or "quy định" in question
        or "quy dinh" in question_no_accent
        or "tài liệu" in question
        or "tai lieu" in question_no_accent
        or "rag" in question
    ):
        return "RAG Documents"

    # Câu hỏi chưa khớp module cụ thể vẫn hiển thị dưới nhãn AI Chat.
    return "AI Chat"


# Kết hợp intent, từ khóa và module để trả loại truy vấn cùng nhãn giao diện.
def route_question(question):
    # Dùng intent nghiệp vụ trước, sau đó mới fallback sang bộ phân loại từ khóa.
    from access_control import detect_intent  # Dùng session, intent và quyền của chatbot.
    intent = detect_intent(question)
    if intent in {'ask_stock', 'ask_order_status', 'ask_customer_info', 'ask_cost_margin'}:
        question_type = 'SQL'
    elif intent in {'ask_promotion', 'ask_sales_policy', 'ask_tech_procedure', 'ask_finance_procedure', 'ask_hr_policy'}:
        question_type = 'RAG'
    elif wants_sql(question) or any(word in question.casefold() for word in ('giá', 'gia', 'phiên bản', 'phân khúc', 'mẫu xe')):
        question_type = 'SQL'
    else:
        question_type = classify_question(question)

    module = detect_module(question)

    return {
        "question": question,
        "type": question_type,
        "module": module
    }


# Chạy các câu hỏi mẫu chỉ khi file được gọi trực tiếp từ dòng lệnh.
if __name__ == "__main__":
    test_questions = [
        "Có bao nhiêu khách hàng tiềm năng?",
        "Khách hàng nào là VIP?",
        "Sản phẩm nào sắp hết hàng?",
        "Báo giá nào đã được duyệt?",
        "Cơ hội bán hàng nào có giá trị cao nhất?",
        "Tổng doanh thu hiện tại là bao nhiêu?",
        "Chính sách chăm sóc khách hàng mới là gì?",
        "Quy định báo giá như thế nào?",
        "RAG trong hệ thống dùng để làm gì?",
        "API key cần được bảo mật như thế nào?"
    ]

    print("Kết quả kiểm tra phân loại câu hỏi:")
    print("-" * 60)

    # ---------------------------------------------------------
    # Vòng lặp FOR: Duyệt danh sách các câu hỏi test mẫu
    # ---------------------------------------------------------
    for question in test_questions:
        result = route_question(question)

        print("Câu hỏi:", result["question"])
        print("Loại xử lý:", result["type"])
        print("Module:", result["module"])
        print("-" * 60)
