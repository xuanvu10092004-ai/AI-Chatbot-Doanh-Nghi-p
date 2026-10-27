# File này khởi tạo Flask, đăng ký route và chuyển request tới các service xác thực, dữ liệu và chatbot.
from __future__ import annotations

import os  # Đọc khóa session và trạng thái môi trường khi khởi tạo Flask.
import re  # Phát hiện thông tin mật khẩu trước khi lưu câu hỏi vào lịch sử chat.
from typing import Any  # Dùng cho kiểu dữ liệu trong các hàm backend.

from flask import Flask, jsonify, render_template, request, session, g, redirect  # Tạo ứng dụng, xử lý request và dựng response.

from access_control import create_session, record_message, resume_session, read_history  # Dùng session, intent và quyền của chatbot.
# Gọi model để diễn đạt câu trả lời từ bằng chứng SQL hoặc RAG.
from ai_service import generate_answer
# Lấy số liệu tổng quan, tồn thấp và khách tiềm năng cho các API cũ.
from database_service import (
    SchemaExtensionRequired,  # Báo module cũ cần schema extension chưa có.
    get_dashboard_stats,  # Đọc số đếm tổng quan cho dashboard.
    get_low_stock_products,  # Lấy phiên bản sắp hết hoặc đã hết hàng.
    get_potential_customers,  # Lấy khách tiềm năng, đang tư vấn hoặc đã mua.
)
from rag_service import search_documents  # Tạo truy vấn RAG và lọc nguồn theo quyền.
from routing import route_question  # Phân loại câu hỏi SQL/RAG và nhãn module.
from sql_service import answer_sql_question  # Thực thi câu hỏi SQL hoặc truy vấn đã kiểm tra.
from sql_service import SchemaExtensionRequired as SQLSchemaExtensionRequired  # Thực thi câu hỏi SQL hoặc truy vấn đã kiểm tra.
from mysql.connector import Error as DatabaseError  # Dùng driver MySQL và kiểu lỗi/kết nối database.
from question_language import resolve_followup  # Chuẩn hóa câu hỏi và nhận diện mẫu xe.
from answer_renderer import QueryEvidence  # Định dạng kết quả truy vấn thành nội dung hiển thị.
# Chuẩn hóa dấu gạch trước khi ghi lịch sử và trả JSON.
from text_formatting import normalize_dashes
from security import initialize_request,permissions,navigation,csrf_token,require_permission  # Dùng xác thực, permission hoặc audit của backend.
# Đăng ký route đăng nhập và đổi mật khẩu.
from auth_routes import register_auth
# Đăng ký dashboard cùng API widget.
from dashboard_routes import register_dashboard
# Đăng ký API quản trị user, role, permission và audit.
from admin_routes import register_admin
# Đăng ký danh sách khách hàng và tồn kho.
from business_routes import register_business
# Đăng ký upload tài liệu và giới hạn kích thước request.
from document_routes import register_documents, document_request_limits
# Đăng ký biểu mẫu Excel và API nhập khách.
from customer_input_routes import register_customer_input
from customer_chat import handle_customer_chat  # Phân tích thông tin khách gửi qua chat.
# Đăng ký API danh sách đơn hàng và xuất chứng từ PDF.
from sales_routes import register_sales
# Đăng ký danh mục xe và lịch dịch vụ.
from operations_routes import register_operations
# Đăng ký trang/API nhận và đọc phiếu nhập kho.
from stock_routes import register_stock
# Đăng ký API lịch hẹn và thao tác chat.
from chat_action_routes import register_chat_actions
# Thực thi lệnh nghiệp vụ trong chat sau khi kiểm tra quyền.
from chat_tools import handle_tool_chat


app = Flask(__name__)
# Giữ thứ tự key JSON theo dữ liệu trả về của route.
app.json.sort_keys = False
# Session cần secret key cấu hình; ứng dụng dừng thay vì dùng khóa mặc định không an toàn.
secret_key = os.getenv("FLASK_SECRET_KEY")
if secret_key:
    app.secret_key = secret_key
else:
    raise RuntimeError('FLASK_SECRET_KEY is required')
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('APP_ENV')!='dev',MAX_CONTENT_LENGTH=65536)
# Chạy giới hạn upload và nạp danh tính/quyền trước mọi route.
app.before_request(document_request_limits)
app.before_request(initialize_request)
register_auth(app)
register_dashboard(app)
register_admin(app)
register_business(app)
register_documents(app)
register_customer_input(app)
register_sales(app)
register_operations(app)
register_stock(app)
register_chat_actions(app)

@app.after_request
def security_headers(response):
    # Ngăn nhúng trang, sniff kiểu nội dung và lưu cache response nhạy cảm.
    response.headers['Content-Security-Policy']="default-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    response.headers['X-Frame-Options']='DENY'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response

@app.context_processor
def shell_context():
    # Cấp CSRF token, user và menu đã lọc quyền cho mọi template.
    return dict(csrf_token=csrf_token,current_user=g.user,menu=navigation() if g.user or session.get('guest') else [],identity=' · '.join(r['name']+' - '+(r['branch_code'] or 'Toàn hệ thống') for r in g.roles) if g.user else 'Khách',can=lambda code:code in permissions())


@app.route("/")
def home():
    if not g.user or g.user['user_type']!='staff':return redirect('/chat')
    return redirect(g.roles[0]['landing_path'] if g.roles else '/chat')

@app.get('/chat')
@require_permission('kb:public:read')
def chat_page():
    return render_template('index.html',demo_mode=False)


@app.route("/api/dashboard", methods=["GET"])
@require_permission('dashboard:view')
def dashboard():
    from dashboard_service import WIDGETS,widget_data  # Lọc widget theo permission và truy vấn số liệu.
    return jsonify({code:widget_data(code) for code,(_,codes) in WIDGETS.items() if all(c in permissions() for c in codes)})


@app.route("/api/low-stock", methods=["GET"])
@require_permission('inventory:read')
def low_stock():
    from business_routes import records  # Tạo danh sách tồn kho đã áp scope backend.
    return jsonify(records('inventory',low_stock=True))


@app.route("/api/potential-customers", methods=["GET"])
@require_permission('customer:read')
def potential_customers():
    from business_routes import records  # Tạo danh sách khách hàng đã áp scope backend.
    return jsonify(records('customers'))


def _current_user_id() -> int | None:
    return g.user['id'] if g.user else None


def _legacy_not_implemented(module: str):
    return jsonify({
        "error": "schema-extension-required",
        "message": f"{module} chưa có trong schema Honda; chưa tự thiết kế bảng.",
    }), 501


@app.route("/api/opportunities", methods=["GET", "POST"])
@require_permission('order:read')
def opportunities():
    return _legacy_not_implemented("Opportunity")


@app.route("/api/quotes", methods=["GET", "POST"])
@require_permission('order:read')
def quotes():
    return _legacy_not_implemented("Quote")


@app.route("/chat", methods=["POST"],endpoint='chat_api')
@require_permission('kb:public:read')
def chat():
    # Chỉ nhận JSON có câu hỏi văn bản, giới hạn độ dài trước khi truy xuất dữ liệu.
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('question'), str) or not data['question'].strip():
        return jsonify({"answer": "Vui lòng nhập câu hỏi.", "type": "None", "module": "None"}), 400
    question = data['question'].strip()
    if len(question) > 4000:
        return jsonify(answer="Câu hỏi quá dài."), 400
    session_id = None
    try:
        user_id = _current_user_id()
        existing_id = session.get('chat_session_id') if app.secret_key else None
        if existing_id is not None and resume_session(existing_id, user_id):
            session_id = existing_id
        else:
            session_id = create_session(user_id, "web")
            if app.secret_key:
                session['chat_session_id'] = session_id
        history = read_history(session_id)
        retrieval_question = resolve_followup(question, history)
        safe_question='[Thông tin mật khẩu đã được ẩn; dùng ô nhập bảo mật]' if re.search(r"\b(?:password|mật khẩu|mat khau)[\"']?\s*[:=]",question,re.I) else question
        record_message(session_id, "user", safe_question)
        tool_confirmation=(data.get('action_id'),data.get('action_version')) if 'action_id' in data else None
        tool_reply=handle_tool_chat(question,session_id,tool_confirmation,data.get('action_secret'))
        if tool_reply is not None:
            record_message(session_id,'bot',tool_reply['answer'])
            tool_reply['session_id']=session_id
            return jsonify(tool_reply)
        confirmation = (data.get('customer_batch_id'), data.get('customer_batch_version')) if 'customer_batch_id' in data else None
        customer_reply = handle_customer_chat(question, session_id, confirmation)
        if customer_reply is not None:
            record_message(session_id, 'bot', customer_reply['answer'])
            customer_reply['session_id'] = session_id
            return jsonify(customer_reply)
        # Phân nhánh truy vấn có cấu trúc hoặc tìm tài liệu theo quyền của user.
        route = route_question(retrieval_question)
        if route["type"] == "CLARIFY":
            answer = "Bạn muốn xem tất cả sản phẩm, tồn kho hay khách hàng? Hãy nói rõ nhóm dữ liệu cần tra cứu."
            record_message(session_id, "bot", answer)
            return jsonify(answer=answer, type=route["type"], module=route["module"], session_id=session_id, engine="clarification", access_denied=False, rows=[], summary=None, sources=[])
        if route["type"] == "SQL":
            context = answer_sql_question(retrieval_question, user_id, session_id, include_inventory_details=True)
        else:
            context = search_documents(question, user_id, session_id)
        # Không gửi kết quả từ chối hoặc thiếu bằng chứng tới model để tránh suy diễn.
        denied = context == "Tôi không thể hỗ trợ yêu cầu này."
        no_evidence = context.startswith(('Không tìm thấy', 'Chưa tìm thấy', 'Cần làm rõ:', 'Chưa phân tích được'))
        engine = 'database'
        if denied or no_evidence:
            answer = context
        elif isinstance(context, QueryEvidence) and os.getenv('GROQ_API_KEY'):
            answer = context.display
            engine = context.engine
        elif not os.getenv('GROQ_API_KEY') and os.getenv('APP_ENV') == 'dev':
            answer = context
        else:
            try:
                answer = generate_answer(question, context, history)
                engine = 'groq'
            except Exception:
                answer = "Dịch vụ AI chưa sẵn sàng. Vui lòng thử lại sau."
                record_message(session_id, 'bot', answer)
                return jsonify(answer=answer, error='ai-unavailable', session_id=session_id), 503
        answer = normalize_dashes(str(answer))
        record_message(session_id, "bot", answer)
        return jsonify({
            "answer": answer,
            "type": route["type"],
            "module": route["module"],
            "session_id": session_id,
            "engine": engine,
            "access_denied": denied,
            "rows": context.rows if isinstance(context,QueryEvidence) else [],
            "summary": context.summary if isinstance(context, QueryEvidence) else None,
            "sources": [{'id':int(i),'title':normalize_dashes(title)} for i,title in re.findall(r'\[Nguồn id=(\d+) \| tiêu đề=([^\]]+)\]',str(context))],
        })
    except (SchemaExtensionRequired, SQLSchemaExtensionRequired) as exc:
        message = str(exc)
        record_message(session_id, "bot", message)
        return jsonify({"error": "schema-extension-required", "message": message}), 501
    except (DatabaseError, RuntimeError):
        return jsonify(error='database-unavailable', answer="Chưa kết nối được cơ sở dữ liệu. Vui lòng thử lại sau."), 503
    except Exception:
        return jsonify(error='backend-error', answer="Chưa xử lý được yêu cầu. Vui lòng thử lại sau."), 500


if __name__ == "__main__":
    import threading  # Mở trình duyệt sau khoảng trễ khi chạy ứng dụng trực tiếp.
    import webbrowser  # Mở trang local mặc định cho nhà phát triển.

    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

