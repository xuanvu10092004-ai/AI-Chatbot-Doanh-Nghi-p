# ==========================================================
# Tên file: rag_service.py
# Mục đích của file: Dịch vụ RAG (Retrieval-Augmented Generation) tra cứu văn bản tài liệu nội bộ.
# File này dùng để làm gì:
#   - Tiếp nhận các câu hỏi hướng tới tra cứu quy định, chính sách, hướng dẫn công ty.
#   - Tách từ khóa quan trọng và lọc bỏ các từ dừng (stopwords) tiếng Việt và tiếng Anh (`extract_keywords`).
#   - Tra cứu cơ sở dữ liệu SQLite trong bảng `documents` sử dụng phép so sánh chuỗi `LIKE` trên tiêu đề (`title`) và nội dung (`content`).
#   - Hỗ trợ fallback tra cứu theo loại văn bản (`document_type`: 'policy', 'guide') nếu chưa đủ kết quả.
#   - Ghép các đoạn tài liệu tìm thấy thành một chuỗi ngữ cảnh (context) hoàn chỉnh để gửi sang `ai_service.py` cho Groq AI tổng hợp câu trả lời.
# Khi nào file được gọi:
#   - Được gọi bởi app.py trong hàm `chat()` khi `routing.py` xác định câu hỏi thuộc luồng "RAG".
#   - Được gọi bởi `test_ai.py` để kiểm tra pipeline tra cứu tài liệu thực tế.
# Luồng hoạt động tổng quát:
#   Người dùng nhập câu hỏi
#           ↓
#   [Tách từ khóa & Lọc Stopwords (extract_keywords)]
#           ↓
#   [Tra cứu SQLite LIKE Search trên title + content bảng documents]
#           ↓
#   [Lấy danh sách các tài liệu (tối đa MAX_DOCS = 3)]
#           ↓
#   [Ghép các tài liệu thành chuỗi Context hoàn chỉnh]
#           ↓
#   [ai_service.generate_answer(question, context)]
#           ↓
#   [Groq LLM sinh câu trả lời tự nhiên -> Trả về giao diện]
# ==========================================================

import sqlite3
import re
from routing import normalize_question   # lowercase + bỏ dấu tiếng Việt
from database_path import DATABASE_PATH

# ---------------------------------------------------------
# Khai báo Hằng số CSDL và Giới hạn số tài liệu tối đa
# ---------------------------------------------------------
DB_NAME = str(DATABASE_PATH)
MAX_DOCS = 3


# ==========================================================
# Hàm get_connection:
# - Hàm dùng để làm gì: Tạo và trả về kết nối CSDL SQLite với row_factory = sqlite3.Row.
# - Tham số đầu vào: Không có.
# - Giá trị trả về: sqlite3.Connection object.
# - Hàm này được gọi ở đâu: `search_documents()`.
# - Vai trò trong hệ thống: Trình mở kết nối CSDL dùng riêng cho RAG.
# ==========================================================
def get_connection():
    """Tạo kết nối SQLite, row_factory để truy cập theo tên cột."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================================
# Hàm extract_keywords:
# - Hàm dùng để làm gì: Phân tích câu hỏi người dùng, loại bỏ các từ không mang nhiều ý nghĩa (stopwords) để thu được danh sách từ khóa tìm kiếm.
# - Tham số đầu vào:
#     + question (str): Câu hỏi gốc của người dùng.
# - Giá trị trả về:
#     + list[str]: Danh sách từ khóa có độ dài >= 3 ký tự (VD: ['bảo', 'hành', 'chính', 'sách']).
# - Hàm này được gọi ở đâu: Được gọi ở đầu hàm `search_documents()`.
# - Vai trò trong hệ thống: Hàm tiền xử lý trích xuất thực thể/từ khóa (Keyword Extraction).
# ==========================================================
def extract_keywords(question):
    """
    Trích xuất từ khóa từ câu hỏi để dùng cho LIKE search.

    Chiến lược:
      1. Tách câu hỏi thành các từ.
      2. Lọc bỏ stopword tiếng Việt (là, gì, như, thế nào...).
      3. Giữ lại từ có nghĩa (>= 3 ký tự).

    Args:
        question (str): Câu hỏi gốc

    Returns:
        list[str]: Danh sách từ khóa để tìm kiếm
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Chuẩn hóa câu hỏi dạng thường có dấu và không dấu
    # ---------------------------------------------------------
    q, q_na = normalize_question(question)

    # ---------------------------------------------------------
    # Bước 2 trong hàm: Khai báo tập hợp các từ dừng (stopwords)
    # - Mục đích: Loại bỏ các từ nối, đại từ, thán từ phổ biến không dùng làm từ khóa tra cứu văn bản.
    # ---------------------------------------------------------
    stopwords = {
        "là", "gì", "như", "thế", "nào", "có", "không", "và", "của",
        "cho", "với", "được", "trong", "khi", "này", "đó", "các",
        "những", "một", "hay", "hoặc", "tôi", "bạn", "hãy", "cần",
        "muốn", "biết", "xem", "cho", "tìm", "về", "theo", "đến",
        "đang", "đã", "ra", "sao",
        "the", "what", "how", "is", "are", "and", "or", "in", "of"
    }

    # ---------------------------------------------------------
    # Vòng lặp list comprehension: Duyệt từng từ trong chuỗi q.split()
    # - Lọc giữ lại từ w KHÔNG thuộc stopwords VÀ độ dài len(w) >= 3.
    # ---------------------------------------------------------
    words = [
        word for word in re.findall(r"\w+", q, flags=re.UNICODE)
        if word not in stopwords and len(word) >= 3
    ]

    # ---------------------------------------------------------
    # Điều kiện IF: Trả về danh sách `words` nếu có từ khóa, hoặc fallback lấy cả câu `[q]` nếu rỗng
    # ---------------------------------------------------------
    return words if words else [q]


# ==========================================================
# Hàm search_documents:
# - Hàm dùng để làm gì: Thực hiện tìm kiếm tài liệu trong bảng `documents` theo danh sách từ khóa và loại văn bản.
# - Tham số đầu vào:
#     + question (str): Câu hỏi của người dùng.
# - Giá trị trả về:
#     + str: Chuỗi văn bản ngữ cảnh (Context) chứa nội dung các tài liệu tìm thấy, sẵn sàng cho LLM.
# - Hàm này được gọi ở đâu: app.py, test_ai.py.
# - Vai trò trong hệ thống: Động cơ tìm kiếm kiến thức RAG (RAG Retrieval Engine).
# ==========================================================
def search_documents(question):
    """
    Tìm tài liệu liên quan trong bảng documents bằng SQLite LIKE search.

    Chiến lược tìm kiếm theo thứ tự ưu tiên:
      1. Tìm theo từng từ khóa trong title và content.
      2. Tìm theo document_type (policy/guide) nếu câu hỏi nhắc đến.
      3. Nếu không có kết quả: trả về thông báo không tìm thấy.

    Args:
        question (str): Câu hỏi từ người dùng

    Returns:
        str: Context ghép từ các tài liệu tìm được (để gửi vào Groq AI)
    """
    # ---------------------------------------------------------
    # Bước 1 trong hàm: Chuẩn hóa câu hỏi và trích xuất từ khóa
    # ---------------------------------------------------------
    q, q_na = normalize_question(question)
    keywords = extract_keywords(question)
    category_keywords = {
        "chính", "sách", "quy", "định", "hướng", "dẫn", "tài", "liệu",
        "nội", "bộ", "trình", "cách", "hoạt", "động",
    }
    specific_keywords = [
        keyword for keyword in keywords if keyword not in category_keywords
    ]
    if specific_keywords:
        keywords = specific_keywords

    conn = get_connection()
    cursor = conn.cursor()

    found_ids = set()   # Tập hợp lưu ID các tài liệu đã tìm thấy để tránh trùng lặp
    results   = []      # Danh sách chứa các từ điển bản ghi tài liệu

    # ---------------------------------------------------------
    # Bước 2 trong hàm: Tìm kiếm tài liệu theo từ khóa và chấm điểm (Scoring)
    # ---------------------------------------------------------
    # Tách số từ khóa khớp khỏi điểm xếp hạng để tránh một từ chung tạo bằng chứng giả.
    doc_scores = {}
    doc_keyword_matches = {}
    doc_data = {}

    for kw in keywords:
        cursor.execute("""
            SELECT id, title, content, document_type
            FROM documents
            WHERE (title LIKE ? OR content LIKE ?)
        """, (f"%{kw}%", f"%{kw}%"))

        for row in cursor.fetchall():
            doc_id = row["id"]
            if doc_id not in doc_scores:
                doc_scores[doc_id] = 0
                doc_keyword_matches[doc_id] = 0
                doc_data[doc_id] = dict(row)
            doc_keyword_matches[doc_id] += 1
            doc_scores[doc_id] += 3 if kw in row["title"].lower() else 1

    # Ưu tiên từ khóa xuất hiện trong tiêu đề; yêu cầu ít nhất hai từ khóa cụ thể nếu có.
    minimum_matches = min(2, len(specific_keywords)) if specific_keywords else 1
    sorted_docs = sorted(
        (
            (doc_id, score)
            for doc_id, score in doc_scores.items()
            if doc_keyword_matches[doc_id] >= minimum_matches
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    # Xóa bỏ các tài liệu trùng lặp (do Excel nạp nhiều lần tạo ra các đuôi #21, #41...)
    base_titles_seen = set()

    for doc_id, score in sorted_docs:
        doc = doc_data[doc_id]

        # Lấy tên gốc (ví dụ: "Chính sách khách hàng VIP #21" -> "Chính sách khách hàng VIP")
        base_title = re.sub(r'\s*#\d+$', '', doc['title']).strip()

        if base_title not in base_titles_seen:
            base_titles_seen.add(base_title)
            found_ids.add(doc_id)
            results.append(doc)

            if len(results) >= MAX_DOCS:
                break

    # ---------------------------------------------------------
    # Bước 3 trong hàm: Fallback tra cứu theo loại tài liệu (document_type) nếu số tài liệu < MAX_DOCS
    # ---------------------------------------------------------
    # Điều kiện IF 3: Nếu số tài liệu thu được chưa đủ 3
    if len(results) < MAX_DOCS and not specific_keywords:
        # Phát hiện loại tài liệu từ câu hỏi
        doc_type = None
        # ---------------------------------------------------------
        # Điều kiện IF 4: Kiểm tra từ khóa chính sách / bảo hành
        # ---------------------------------------------------------
        if any(w in q or w in q_na for w in ["chính sách", "chinh sach", "quy định", "quy dinh", "bảo hành", "bao hanh"]):
            doc_type = "policy"
        # ---------------------------------------------------------
        # Điều kiện ELIF 5: Kiểm tra từ khóa hướng dẫn / quy trình
        # ---------------------------------------------------------
        elif any(w in q or w in q_na for w in ["hướng dẫn", "huong dan", "quy trình", "quy trinh", "cách", "cach"]):
            doc_type = "guide"

        # ---------------------------------------------------------
        # Điều kiện IF 6: Nếu xác định được doc_type -> Thực thi SQL tìm theo document_type
        # ---------------------------------------------------------
        if doc_type:
            # Câu lệnh SQL: SELECT ... FROM documents WHERE document_type = ? AND id NOT IN (...) LIMIT ?
            cursor.execute("""
                SELECT id, title, content, document_type
                FROM documents
                WHERE document_type = ?
                  AND id NOT IN ({})
                LIMIT ?
            """.format(",".join("?" * len(found_ids)) if found_ids else "SELECT -1"),
                [doc_type] + list(found_ids) + [MAX_DOCS - len(results)]
            )
            # Vòng lặp FOR 3: Thêm kết quả từ doc_type vào danh sách results
            for row in cursor.fetchall():
                if row["id"] not in found_ids:
                    found_ids.add(row["id"])
                    results.append(dict(row))

    conn.close()

    # ---------------------------------------------------------
    # Bước 4 trong hàm: Xử lý trường hợp không tìm thấy tài liệu
    # ---------------------------------------------------------
    # Điều kiện IF 7: Nếu danh sách results rỗng hoàn toàn
    if not results:
        return "Không tìm thấy tài liệu liên quan trong hệ thống."

    # ---------------------------------------------------------
    # Bước 5 trong hàm: Ghép các tài liệu tìm được thành chuỗi ngữ cảnh Context cho LLM
    # ---------------------------------------------------------
    context_parts = [f"Tìm thấy {len(results)} tài liệu liên quan:\n"]

    # Vòng lặp FOR 4: Duyệt qua từng tài liệu để ghép chuỗi
    for i, doc in enumerate(results, 1):
        context_parts.append(
            f"--- Tài liệu {i}: {doc['title']} ---\n"
            f"{doc['content']}\n"
        )

    return "\n".join(context_parts)


# ==========================================================
# Khối lệnh kiểm tra điểm chạy trực tiếp (Main Execution Entry Point):
# - __name__ là gì: Biến lưu tên module hiện tại.
# - __main__ là gì: Tên gọi khi chạy trực tiếp file (`python rag_service.py`).
# - Vì sao phải dùng: Cho phép chạy kiểm thử độc lập hàm tra cứu `search_documents()` mà không kích hoạt khi import vào `app.py`.
# - Khi import: __name__ != "__main__" -> Không chạy danh sách câu hỏi test.
# - Khi chạy trực tiếp: __name__ == "__main__" -> Chạy kiểm tra RAG cho 5 câu hỏi mẫu và in kết quả ra terminal.
# ==========================================================
if __name__ == "__main__":
    test_questions = [
        "Chính sách bảo hành là gì?",
        "Quy định chăm sóc khách hàng như thế nào?",
        "Hướng dẫn sử dụng AI Chat?",
        "Quy trình báo giá như thế nào?",
        "Tồn kho thấp được xử lý ra sao?",
    ]

    # Vòng lặp FOR: Duyệt qua từng câu hỏi thử nghiệm RAG
    for q in test_questions:
        print("=" * 60)
        print(f"Câu hỏi : {q}")
        print(f"Context :\n{search_documents(q)}")
        print()
