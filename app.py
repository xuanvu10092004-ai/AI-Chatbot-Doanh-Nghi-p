# ==========================================================
# Tên file: app.py
# Mục đích của file: File chính (Entry Point) của ứng dụng Web Flask Server.
# File này dùng để làm gì:
#   - Khởi tạo ứng dụng Web Flask (`app = Flask(__name__)`).
#   - Định nghĩa các đường dẫn API Endpoint phục vụ Frontend (Giao diện HTML/JS):
#       + Route `/`                     : Trả về giao diện trang web chính (index.html).
#       + Route `GET /api/dashboard`    : Trả về số liệu thống kê tổng quan của các bảng.
#       + Route `GET /api/low-stock`    : Trả về danh sách sản phẩm sắp hết hàng (tồn kho < 10).
#       + Route `GET /api/potential-customers`: Trả về danh sách khách hàng tiềm năng/VIP/mới.
#       + Route `POST /chat`            : Tiếp nhận câu hỏi Chatbot, định tuyến SQL/RAG và sinh câu trả lời bằng Groq LLM.
#   - Khởi chạy Web Server cục bộ và tự động bật trình duyệt.
# Khi nào file được gọi:
#   - Được gọi đầu tiên khi khởi động ứng dụng Web backend bằng lệnh `python app.py`.
# Luồng hoạt động tổng quát Chatbot & REST API:
#   Người dùng nhập câu hỏi trên Giao diện Web
#           ↓
#   [Gửi HTTP POST JSON request tới Route /chat]
#           ↓
#   [Hàm chat() nhận request -> Gọi routing.route_question(question)]
#           ↓
#   [Kiểm tra result["type"] == "SQL" hay "RAG"]
#       ├─ SQL: Gọi sql_service.answer_sql_question(question) lấy dữ liệu CSDL
#       └─ RAG: Lấy dữ liệu tài liệu chính sách công ty
#           ↓
#   [Gọi ai_service.generate_answer(question, context) -> Groq LLM sinh câu trả lời]
#           ↓
#   [Trả về HTTP JSON response {"answer", "type", "module"}]
#           ↓
#   [JavaScript render hiển thị câu trả lời lên giao diện khung chat Web]
# ==========================================================

import threading
import webbrowser
import logging
from flask import Flask, render_template, request, jsonify
from ai_service import AIConfigurationError, AIServiceError

# Import hàm phân loại câu hỏi (SQL hay RAG) và xác định module
from routing import route_question

# Import các hàm truy vấn database cho Dashboard và các widget
from database_service import (
    get_dashboard_stats,       # Thống kê tổng quan (số dòng mỗi bảng)
    get_low_stock_products,    # Sản phẩm sắp hết hàng
    get_potential_customers    # Khách hàng tiềm năng / VIP
)

# Import hàm xử lý câu hỏi dạng SQL (truy vấn database)
from sql_service import answer_sql_question

# Import hàm gọi Groq AI để sinh câu trả lời tự nhiên
from ai_service import generate_answer

# Import hàm tìm tài liệu trong bảng documents (RAG)
from rag_service import search_documents

# ---------------------------------------------------------
# Khởi tạo đối tượng ứng dụng Web Flask
# ---------------------------------------------------------
app = Flask(__name__)
logger = logging.getLogger(__name__)


# ==========================================================
# Hàm home (Route "/"):
# - Hàm dùng để làm gì: Trả về trang HTML giao diện người dùng chính (Single Page Application - SPA).
# - Tham số đầu vào: Không có.
# - Giá trị trả về: Nguồn mã HTML của file `templates/index.html`.
# - Hàm này được gọi ở đâu: Được Flask gọi khi người dùng truy cập trang chủ.
# - Vai trò trong hệ thống: Route render giao diện người dùng (Frontend View Renderer).
# ==========================================================
@app.route("/")
def home():
    """
    Route: Trang chủ
    Trả về file index.html trong thư mục templates/
    """
    return render_template("index.html")


# ==========================================================
# Hàm dashboard (Route "GET /api/dashboard"):
# - Hàm dùng để làm gì: Trả về dữ liệu JSON chứa số lượng bản ghi của 6 bảng CSDL.
# - Tham số đầu vào: Không có.
# - Giá trị trả về: JSON Response đại diện cho từ điển thống kê.
# - Hàm này được gọi ở đâu: JavaScript frontend gọi qua fetch('/api/dashboard').
# - Vai trò trong hệ thống: REST API Endpoint cung cấp số liệu tổng quan Dashboard.
# ==========================================================
@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    """
    Route: API lấy thống kê Dashboard
    GET /api/dashboard
    Trả về số lượng bản ghi của từng bảng trong database
    """
    stats = get_dashboard_stats()
    return jsonify(stats)


# ==========================================================
# Hàm low_stock (Route "GET /api/low-stock"):
# - Hàm dùng để làm gì: Cung cấp danh sách các sản phẩm kho có tồn kho < 10.
# - Tham số đầu vào: Không có.
# - Giá trị trả về: JSON Array danh sách các sản phẩm.
# - Hàm này được gọi ở đâu: JavaScript frontend gọi để hiển thị Widget Sản phẩm sắp hết hàng.
# ==========================================================
@app.route("/api/low-stock", methods=["GET"])
def low_stock():
    """
    Route: API lấy danh sách sản phẩm sắp hết hàng
    GET /api/low-stock
    Trả về các sản phẩm có quantity < 10
    """
    products = get_low_stock_products()
    return jsonify(products)


# ==========================================================
# Hàm potential_customers (Route "GET /api/potential-customers"):
# - Hàm dùng để làm gì: Cung cấp danh sách các khách hàng tiềm năng/VIP/mới.
# - Tham số đầu vào: Không có.
# - Giá trị trả về: JSON Array danh sách thông tin khách hàng.
# - Hàm này được gọi ở đâu: JavaScript frontend gọi để render Widget Khách hàng trọng tâm.
# ==========================================================
@app.route("/api/potential-customers", methods=["GET"])
def potential_customers():
    """
    Route: API lấy danh sách khách hàng tiềm năng
    GET /api/potential-customers
    Trả về khách hàng có status là 'potential', 'vip', hoặc 'new'
    """
    customers = get_potential_customers()
    return jsonify(customers)


# ==========================================================
# Hàm chat (Route "POST /chat"):
# - Hàm dùng để làm gì: Xử lý toàn bộ quy trình nhận câu hỏi, phân loại SQL/RAG, chuẩn bị context và nhờ Groq LLM trả lời.
# - Luồng dữ liệu Flask API:
#     Request JSON -> Route POST /chat -> Hàm chat() -> Xử lý (routing + sql_service / rag_service) -> Database -> Groq LLM -> Response JSON
# - Tham số đầu vào:
#     + JSON body gửi từ client: {"question": "Nội dung câu hỏi"}
# - Giá trị trả về:
#     + JSON response: {"answer": "...", "type": "SQL"/"RAG", "module": "AI CRM"}
# - Hàm này được gọi ở đâu: Được JavaScript trên giao diện Web bấm gửi tin nhắn gọi tới.
# - Vai trò trong hệ thống: Trái tim tiếp nhận hội thoại Chatbot (Chat Controller Endpoint).
# ==========================================================
@app.route("/chat", methods=["POST"])
def chat():
    """
    Route: API xử lý câu hỏi từ chatbox
    POST /chat
    Nhận câu hỏi từ người dùng, phân loại (SQL/RAG),
    rồi trả về câu trả lời tương ứng.
    """
    # ---------------------------------------------------------
    # Khối try-except bắt lỗi ngoại lệ trong quá trình xử lý API
    # ---------------------------------------------------------
    try:
        # ---------------------------------------------------------
        # Bước 1 trong hàm: Trích xuất chuỗi câu hỏi từ request JSON
        # ---------------------------------------------------------
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({
                "answer": "Nội dung gửi lên phải là JSON hợp lệ.",
                "type": "ERROR",
                "module": "ERROR",
                "error": "invalid_json",
            }), 400

        question = data.get("question")
        if not isinstance(question, str):
            return jsonify({
                "answer": "Trường question phải là chuỗi văn bản.",
                "type": "ERROR",
                "module": "ERROR",
                "error": "invalid_question",
            }), 400

        # ---------------------------------------------------------
        # Điều kiện IF: Kiểm tra xem câu hỏi có bị rỗng hay chỉ toàn khoảng trắng hay không
        # - Khi TRUE: Trả về câu thông báo yêu cầu nhập câu hỏi ngay lập tức.
        # - Khi FALSE: Tiếp tục chuyển sang bước phân loại routing.
        # ---------------------------------------------------------
        if not question.strip():
            return jsonify({
                "answer": "Vui lòng nhập câu hỏi.",
                "type": "None",
                "module": "None",
                "error": "empty_question",
            }), 400

        # ---------------------------------------------------------
        # Bước 2 trong hàm: Gọi routing.py để phân loại loại xử lý (SQL/RAG) và xác định module
        # ---------------------------------------------------------
        result = route_question(question)

        # ---------------------------------------------------------
        # Bước 3 trong hàm: Lấy dữ liệu ngữ cảnh (Context) dựa vào kết quả phân loại
        # - Điều kiện IF / ELSE:
        #     + Khi result["type"] == "SQL": Gọi `answer_sql_question(question)` lấy dữ liệu CSDL SQLite thực tế.
        #     + Khi ELSE (RAG): Sử dụng chuỗi văn bản chính sách tài liệu nội bộ công ty.
        # ---------------------------------------------------------
        if result["type"] == "SQL":
            # SQL -> truy vấn database lấy dữ liệu thật làm context
            context = answer_sql_question(question)
        else:
            # RAG -> tìm tài liệu liên quan trong bảng documents bằng SQLite LIKE search
            context = search_documents(question)

        # ---------------------------------------------------------
        # Bước 4 trong hàm: Gửi (question + context) tới Groq AI LLM sinh câu trả lời tự nhiên
        # ---------------------------------------------------------
        answer = generate_answer(question, context)

        # ---------------------------------------------------------
        # Bước 5 trong hàm: Đóng gói và trả về JSON Response cho Frontend
        # ---------------------------------------------------------
        return jsonify({
            "answer": answer,
            "type": result["type"],
            "module": result["module"]
        })

    # ---------------------------------------------------------
    # Khối EXCEPT: Bắt tất cả ngoại lệ bất ngờ xảy ra ở backend
    # - Trả về mã lỗi JSON không làm crash trang web frontend.
    # ---------------------------------------------------------
    except AIConfigurationError as e:
        logger.warning("Chat request blocked: LLM configuration is missing.")
        return jsonify({
            "answer": str(e),
            "type": "ERROR",
            "module": "ERROR",
            "error": "llm_not_configured",
        }), 503
    except AIServiceError as e:
        logger.warning(
            "Chat provider failure: %s (HTTP %s)",
            e.error_code,
            e.provider_status or "unavailable",
        )
        return jsonify({
            "answer": str(e),
            "type": "ERROR",
            "module": "ERROR",
            "error": e.error_code,
        }), 502
    except Exception:
        logger.exception("Unexpected error while processing chat request.")
        return jsonify({
            "answer": "Đã xảy ra lỗi khi xử lý câu hỏi. Vui lòng thử lại.",
            "type": "ERROR",
            "module": "ERROR",
            "error": "internal_error",
        }), 500


# ==========================================================
# Khối lệnh kiểm tra điểm chạy trực tiếp (Main Execution Entry Point):
# - __name__ là gì: Biến lưu tên của module Python hiện tại.
# - __main__ là gì: Giá trị chuỗi mặc định khi khởi chạy trực tiếp file từ dòng lệnh (`python app.py`).
# - Vì sao phải dùng: Để khởi chạy Flask dev server và tự động mở trình duyệt web khi người dùng chạy `python app.py`.
# - Khi import sang file khác: __name__ != "__main__" -> Server Flask KHÔNG tự kích hoạt.
# - Khi chạy trực tiếp: __name__ == "__main__" -> Khởi tạo timer mở trình duyệt và chạy app.run(debug=True).
# ==========================================================
if __name__ == "__main__":
    url = "http://127.0.0.1:5000"
    # Dùng threading.Timer để chờ Flask khởi động xong (1.2s) rồi mới tự động mở trình duyệt web
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    # Chạy ứng dụng Flask ở port 5000 với tính năng debug và tắt reloader phụ
    app.run(debug=True, use_reloader=False)