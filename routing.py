# ==========================================================
# Tên file: routing.py
# Mục đích của file: Bộ phân loại và định tuyến câu hỏi thông minh (Question Router & Classifier).
# File me dùng để làm gì:
#   - Chuẩn hóa chuỗi văn bản đầu vào: chuyển chữ thường, xóa khoảng trắng thừa và loại bỏ dấu tiếng Việt (`remove_vietnamese_accents`).
#   - Phân loại luồng xử lý câu hỏi (`classify_question`):
#       + `SQL`: Nếu câu hỏi hướng tới dữ liệu có cấu trúc trong CSDL (Khách hàng, Kho hàng, Báo giá, Cơ hội...).
#       + `RAG`: Nếu câu hỏi hướng tới tài liệu, quy trình, chính sách công ty hoặc câu hỏi tổng quát.
#   - Xác định Module nghiệp vụ (`detect_module`): AI CRM, AI Warehouse, AI Quote, AI Opportunity, AI Dashboard, RAG Documents, AI Chat.
#   - Cung cấp hàm định tuyến chính (`route_question`) kết hợp cả loại xử lý và module phụ trách.
# Khi nào file được gọi:
#   - Được app.py gọi ở đầu xử lý POST /chat request để quyết định gửi câu hỏi sang `sql_service.py` hay `rag_service.py`.
#   - Được import bởi `rag_service.py` và `sql_service.py` để dùng chung hàm chuẩn hóa `normalize_question`.
#   - Được `test_sql.py` và `test_ai.py` sử dụng trong quá trình chạy test pipeline.
# Luồng hoạt động tổng quát:
#   [Câu hỏi người dùng]
#           ↓
#   [normalize_question: lowercase + bỏ dấu]
#           ↓
#   [classify_question: Kiểm tra từ khóa RAG trước -> Kiểm tra từ khóa SQL sau]
#           ↓
#   [detect_module: Khớp từ khóa xác định module nghiệp vụ]
#           ↓
#   [Trả về dict {"question", "type": "SQL"/"RAG", "module": "AI CRM"...}]
# ==========================================================

import unicodedata


# ==========================================================
# Hàm remove_vietnamese_accents:
# - Hàm dùng để làm gì: Loại bỏ hoàn toàn dấu tiếng Việt out khỏi chuỗi văn bản (VD: 'khách hàng' -> 'khach hang').
# - Tham số đầu vào:
#     + text (str): Chuỗi tiếng Việt có dấu.
# - Giá trị trả về:
#     + str: Chuỗi tiếng Việt không dấu (chuẩn ASCII).
# - Hàm này được gọi ở đâu: Được gọi bên trong hàm `normalize_question()`.
# - Vai trò trong hệ thống: Hàm tiền xử lý văn bản (Text Preprocessing) hỗ trợ tìm kiếm không dấu.
# ==========================================================
def remove_vietnamese_accents(text):
    """
    Bỏ dấu tiếng Việt trong chuỗi để hỗ trợ nhận diện từ khóa
    khi người dùng gõ không dấu.

    Cách hoạt động:
        - NFD decompose ký tự có dấu thành ký tự gốc + dấu riêng
        - encode ascii ignore: loại bỏ phần dấu (không phải ASCII)
        - decode utf-8: chuyển bytes trở lại thành chuỗi

    Ví dụ:
        'khách hàng' -> 'khach hang'
        'sắp hết hàng' -> 'sap het hang'

    Args:
        text (str): Chuỗi tiếng Việt cần bỏ dấu

    Returns:
        str: Chuỗi đã bỏ dấu
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Thường hóa Unicode chuẩn NFD và loại bỏ ký tự dấu ASCII
    # - Bước này đang làm gì: Tách ký tự gốc và dấu riêng biệt bằng NFD, sau đó mã hóa ASCII bỏ qua các ký tự không chuẩn.
    # - Dữ liệu đi từ đâu đến đâu: Chuỗi Unicode tiếng Việt -> Chuỗi ASCII thuần không dấu.
    # ---------------------------------------------------------
    text = unicodedata.normalize("NFD", text.replace('đ', 'd').replace('Đ', 'D'))
    text = text.encode("ascii", "ignore").decode("utf-8")
    return text


# ==========================================================
# Hàm normalize_question:
# - Hàm dùng để làm gì: Tạo 2 phiên bản câu hỏi đã chuẩn hóa (chữ thường có dấu và chữ thường không dấu).
# - Tham số đầu vào:
#     + question (str): Câu hỏi gốc của người dùng.
# - Giá trị trả về:
#     + tuple(str, str): Trả về cặp (question_lowercase, question_no_accent).
# - Hàm này được gọi ở đâu:
#     + routing.py (trong classify_question, detect_module)
#     + rag_service.py (trong extract_keywords, search_documents)
#     + sql_service.py (trong answer_sql_question)
# - Vai trò trong hệ thống: Hàm chuẩn hóa câu hỏi dùng chung cho toàn bộ dự án.
# ==========================================================
def normalize_question(question):
    """
    Chuẩn hóa câu hỏi trước khi so sánh từ khóa.

    Trả về 2 phiên bản:
        - question: chữ thường, có dấu  (để khớp với người dùng gõ có dấu)
        - question_no_accent: chữ thường, không dấu (để khớp khi gõ không dấu)

    Args:
        question (str): Câu hỏi gốc từ người dùng

    Returns:
        tuple(str, str): (câu hỏi thường hóa có dấu, câu hỏi thường hóa không dấu)
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Chuyển về chữ thường, cắt bỏ khoảng trắng hai đầu và bỏ dấu
    # ---------------------------------------------------------
    question = question.lower().strip()
    question_no_accent = remove_vietnamese_accents(question)
    return question, question_no_accent


# ==========================================================
# Hàm classify_question:
# - Hàm dùng để làm gì: Phân loại câu hỏi thành "RAG" hoặc "SQL" dựa trên thuật toán trùng khớp từ khóa (Keyword Matching).
# - Tham số đầu vào:
#     + question (str): Câu hỏi gốc người dùng nhập vào.
# - Giá trị trả về:
#     + str: "RAG" (tra cứu tài liệu) hoặc "SQL" (truy vấn cơ sở dữ liệu).
# - Hàm này được gọi ở đâu: Được gọi bên trong hàm `route_question()`.
# - Vai trò trong hệ thống: Bộ phân loại định tuyến luồng xử lý chính (Main Workflow Classifier).
# ==========================================================
def classify_question(question):
    """
    Phân loại câu hỏi thành SQL hoặc RAG dựa trên danh sách từ khóa.

    Nguyên tắc phân loại:
        - SQL : câu hỏi về dữ liệu có cấu trúc trong database
                (khách hàng, sản phẩm, tồn kho, báo giá, cơ hội...)
        - RAG : câu hỏi về tài liệu, chính sách, quy định, hướng dẫn nội bộ
                (cần tra cứu văn bản hoặc AI phân tích)

    Ưu tiên kiểm tra RAG TRƯỚC để tránh nhầm lẫn.
    Ví dụ: "Quy định báo giá là gì?" có chứa "báo giá" (SQL keyword)
    nhưng thực chất hỏi quy định → nên trả về RAG.

    Args:
        question (str): Câu hỏi gốc của người dùng

    Returns:
        str: "RAG" hoặc "SQL"
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Chuẩn hóa câu hỏi thành 2 dạng có dấu và không dấu
    # ---------------------------------------------------------
    question, question_no_accent = normalize_question(question)

    # Từ khóa chỉ ra câu hỏi về tài liệu / chính sách (xử lý bằng RAG)
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
        # Bổ sung B11 - RAG Pipeline
        "bảo hành", "bao hanh",
        "hỗ trợ", "ho tro",
        "ai chat", "chatbot",
        "triển khai", "trien khai"
    ]

    # Từ khóa chỉ ra câu hỏi về dữ liệu cấu trúc (xử lý bằng SQL)
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

    # ---------------------------------------------------------
    # Vòng lặp FOR 1: Kiểm tra từ khóa RAG (Được ƯU TIÊN kiểm tra TRƯỚC)
    # - Vòng lặp duyệt cái gì: Duyệt qua từng từ khóa trong danh sách `rag_keywords`.
    # - Mỗi lần lặp xử lý gì: So sánh từ khóa với câu hỏi có dấu và không dấu.
    # - Khi kết thúc vòng lặp thu được gì: Nếu tìm thấy từ khóa khớp -> Trả về ngay lập tức chuỗi "RAG".
    # ---------------------------------------------------------
    for keyword in rag_keywords:
        # ---------------------------------------------------------
        # Điều kiện IF: Kiểm tra từ khóa RAG xuất hiện trong câu hỏi
        # - Điều kiện kiểm tra gì: keyword in question (có dấu) HOẶC keyword in question_no_accent (không dấu).
        # - Khi TRUE sẽ làm gì: Trả về chuỗi "RAG".
        # - Khi FALSE sẽ làm gì: Bỏ qua và chuyển sang lặp từ khóa RAG tiếp theo.
        # ---------------------------------------------------------
        if keyword in question or keyword in question_no_accent:
            return "RAG"

    # ---------------------------------------------------------
    # Vòng lặp FOR 2: Kiểm tra từ khóa SQL (Kiểm tra SAU RAG)
    # - Vòng lặp duyệt cái gì: Duyệt qua từng từ khóa trong danh sách `sql_keywords`.
    # - Mỗi lần lặp xử lý gì: So sánh từ khóa với câu hỏi.
    # - Khi kết thúc vòng lặp thu được gì: Nếu tìm thấy từ khóa khớp -> Trả về ngay lập tức chuỗi "SQL".
    # ---------------------------------------------------------
    for keyword in sql_keywords:
        # ---------------------------------------------------------
        # Điều kiện IF: Kiểm tra từ khóa SQL có trong câu hỏi
        # - Điều kiện kiểm tra gì: keyword có trong question hoặc question_no_accent.
        # - Khi TRUE sẽ làm gì: Trả về chuỗi "SQL".
        # - Khi FALSE sẽ làm gì: Tiếp tục lặp từ khóa SQL tiếp theo.
        # ---------------------------------------------------------
        if keyword in question or keyword in question_no_accent:
            return "SQL"

    # ---------------------------------------------------------
    # Fallback mặc định nếu không khớp từ khóa nào -> Đưa về RAG để Groq AI trả lời tổng quát
    # ---------------------------------------------------------
    return "RAG"


# ==========================================================
# Hàm detect_module:
# - Hàm dùng để làm gì: Xác định câu hỏi thuộc phân hệ/module chức năng cụ thể nào.
# - Tham số đầu vào:
#     + question (str): Câu hỏi gốc của người dùng.
# - Giá trị trả về:
#     + str: Tên module nghiệp vụ ('AI CRM', 'AI Warehouse', 'AI Quote', 'AI Opportunity', 'AI Dashboard', 'RAG Documents', 'AI Chat').
# - Hàm này được gọi ở đâu: Được gọi bên trong hàm `route_question()`.
# - Vai trò trong hệ thống: Bộ phân loại module để hiển thị badge/icon trên giao diện frontend.
# ==========================================================
def detect_module(question):
    """
    Xác định câu hỏi thuộc module nghiệp vụ nào trong hệ thống.

    Các module được hỗ trợ:
        - AI CRM        : Quản lý khách hàng
        - AI Warehouse  : Quản lý tồn kho / sản phẩm
        - AI Quote      : Quản lý báo giá
        - AI Opportunity: Quản lý cơ hội bán hàng
        - AI Dashboard  : Thống kê tổng quan / doanh thu
        - RAG Documents : Tài liệu nội bộ / chính sách
        - AI Chat       : Mặc định khi không xác định được module

    Args:
        question (str): Câu hỏi gốc của người dùng

    Returns:
        str: Tên module phụ trách
    """

    question, question_no_accent = normalize_question(question)

    # ---------------------------------------------------------
    # Điều kiện IF 1: Phân loại Module AI CRM (Khách hàng)
    # - Khi TRUE: Trả về "AI CRM".
    # ---------------------------------------------------------
    if (
        "khách hàng" in question
        or "khach hang" in question_no_accent
        or "crm" in question
        or "customer" in question
    ):
        return "AI CRM"

    # ---------------------------------------------------------
    # Điều kiện IF 2: Phân loại Module AI Warehouse (Kho hàng & Sản phẩm)
    # - Khi TRUE: Trả về "AI Warehouse".
    # ---------------------------------------------------------
    if (
        "sản phẩm" in question
        or "san pham" in question_no_accent
        or "kho" in question
        or "tồn kho" in question
        or "ton kho" in question_no_accent
        or "inventory" in question
    ):
        return "AI Warehouse"

    # ---------------------------------------------------------
    # Điều kiện IF 3: Phân loại Module AI Quote (Báo giá)
    # - Khi TRUE: Trả về "AI Quote".
    # ---------------------------------------------------------
    if (
        "báo giá" in question
        or "bao gia" in question_no_accent
        or "quote" in question
    ):
        return "AI Quote"

    # ---------------------------------------------------------
    # Điều kiện IF 4: Phân loại Module AI Opportunity (Cơ hội bán hàng)
    # - Khi TRUE: Trả về "AI Opportunity".
    # ---------------------------------------------------------
    if (
        "cơ hội" in question
        or "co hoi" in question_no_accent
        or "opportunity" in question
    ):
        return "AI Opportunity"

    # ---------------------------------------------------------
    # Điều kiện IF 5: Phân loại Module AI Dashboard (Thống kê & Doanh thu)
    # - Khi TRUE: Trả về "AI Dashboard".
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # Điều kiện IF 6: Phân loại Module RAG Documents (Tài liệu nội bộ & Quy định)
    # - Khi TRUE: Trả về "RAG Documents".
    # ---------------------------------------------------------
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

    # Mặc định: trả về AI Chat khi không xác định được module cụ thể
    return "AI Chat"


# ==========================================================
# Hàm route_question:
# - Hàm dùng để làm gì: Hàm tích hợp chính, nhận câu hỏi và trả về đối tượng dict kết quả phân loại định tuyến.
# - Tham số đầu vào:
#     + question (str): Câu hỏi của người dùng gửi lên.
# - Giá trị trả về:
#     + dict: {"question": str, "type": "SQL"/"RAG", "module": str}
# - Hàm này được gọi ở đâu:
#     + app.py (route `/chat`)
#     + test_sql.py và test_ai.py
# - Vai trò trong hệ thống: Cổng vào định tuyến trung tâm (API Routing Entrypoint).
# ==========================================================
def route_question(question):
    """
    Hàm tổng hợp - điểm vào chính của module routing.

    Nhận câu hỏi từ người dùng và trả về dict chứa:
        - question : câu hỏi gốc
        - type     : loại xử lý ("SQL" hoặc "RAG")
        - module   : tên module phụ trách

    Được gọi bởi app.py khi nhận request từ giao diện chatbot.

    Args:
        question (str): Câu hỏi của người dùng

    Returns:
        dict: {
            "question": str,  # Câu hỏi gốc
            "type"    : str,  # "SQL" hoặc "RAG"
            "module"  : str   # Tên module nghiệp vụ
        }
    """

    # ---------------------------------------------------------
    # Bước 1 trong hàm: Gọi classify_question để xác định kiểu xử lý "SQL" hay "RAG"
    # ---------------------------------------------------------
    from access_control import detect_intent
    intent = detect_intent(question)
    if intent in {'ask_stock', 'ask_order_status', 'ask_customer_info', 'ask_cost_margin'}:
        question_type = 'SQL'
    elif intent in {'ask_promotion', 'ask_sales_policy', 'ask_tech_procedure', 'ask_finance_procedure', 'ask_hr_policy'}:
        question_type = 'RAG'
    elif any(word in question.casefold() for word in ('giá', 'gia', 'phiên bản', 'phân khúc', 'mẫu xe')):
        question_type = 'SQL'
    else:
        question_type = classify_question(question)

    # ---------------------------------------------------------
    # Bước 2 trong hàm: Gọi detect_module để xác định phân hệ nghiệp vụ
    # ---------------------------------------------------------
    module = detect_module(question)

    # ---------------------------------------------------------
    # Bước 3 trong hàm: Ghép kết quả trả về dưới dạng từ điển dict
    # ---------------------------------------------------------
    return {
        "question": question,
        "type": question_type,
        "module": module
    }


# ==========================================================
# Khối lệnh kiểm tra điểm chạy trực tiếp (Main Execution Entry Point):
# - __name__ là gì: Biến hệ thống Python chứa tên của module hiện tại.
# - __main__ là gì: Giá trị chuỗi mặc định của __name__ khi file được thực thi trực tiếp từ dòng lệnh.
# - Vì sao phải dùng khối lệnh này: Để kiểm tra thử nghiệm tính đúng đắn của logic phân loại mà không làm ảnh hưởng khi module này được import ở file khác.
# - Khi import (`from routing import route_question`): __name__ != "__main__" -> Khối test KHÔNG chạy.
# - Khi chạy trực tiếp (`python routing.py`): __name__ == "__main__" -> Chạy vòng lặp test 10 câu hỏi mẫu và in kết quả ra terminal.
# ==========================================================
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
