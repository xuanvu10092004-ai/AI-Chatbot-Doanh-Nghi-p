from __future__ import annotations

import os
import re
from typing import Any

from flask import Flask, jsonify, render_template, request, session, g, redirect

from access_control import create_session, record_message, resume_session, read_history
from ai_service import generate_answer
from database_service import (
    SchemaExtensionRequired,
    get_dashboard_stats,
    get_low_stock_products,
    get_potential_customers,
)
from rag_service import search_documents
from routing import route_question
from sql_service import answer_sql_question
from sql_service import SchemaExtensionRequired as SQLSchemaExtensionRequired
from mysql.connector import Error as DatabaseError
from question_language import resolve_followup
from answer_renderer import QueryEvidence
from security import initialize_request,permissions,navigation,csrf_token,require_permission
from auth_routes import register_auth
from dashboard_routes import register_dashboard
from admin_routes import register_admin
from business_routes import register_business


app = Flask(__name__)
secret_key = os.getenv("FLASK_SECRET_KEY")
if secret_key:
    app.secret_key = secret_key
else:
    raise RuntimeError('FLASK_SECRET_KEY is required')
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('APP_ENV')!='dev',MAX_CONTENT_LENGTH=65536)
app.before_request(initialize_request)
register_auth(app)
register_dashboard(app)
register_admin(app)
register_business(app)

@app.after_request
def security_headers(response):
    response.headers['Content-Security-Policy']="default-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    response.headers['X-Frame-Options']='DENY'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response

@app.context_processor
def shell_context():
    return dict(csrf_token=csrf_token,current_user=g.user,menu=navigation() if g.user or session.get('guest') else [],identity=' · '.join(r['name']+' — '+(r['branch_code'] or 'Toàn hệ thống') for r in g.roles) if g.user else 'Khách',can=lambda code:code in permissions())


@app.route("/")
def home():
    return redirect(g.roles[0]['landing_path'] if g.roles else '/chat')

@app.get('/chat')
@require_permission('kb:public:read')
def chat_page():
    return render_template('index.html',demo_mode=False)


@app.route("/api/dashboard", methods=["GET"])
@require_permission('dashboard:view')
def dashboard():
    from dashboard_service import WIDGETS,widget_data
    return jsonify({code:widget_data(code) for code,(_,codes) in WIDGETS.items() if all(c in permissions() for c in codes)})


@app.route("/api/low-stock", methods=["GET"])
@require_permission('inventory:read')
def low_stock():
    from business_routes import records
    return jsonify(records('inventory',low_stock=True))


@app.route("/api/potential-customers", methods=["GET"])
@require_permission('customer:read')
def potential_customers():
    from business_routes import records
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


@app.route("/api/bookings", methods=["GET", "POST"])
@require_permission('kb:public:read')
def bookings():
    return _legacy_not_implemented("Booking")


@app.route("/chat", methods=["POST"],endpoint='chat_api')
@require_permission('kb:public:read')
def chat():
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
        record_message(session_id, "user", question)
        route = route_question(retrieval_question)
        if route["type"] == "SQL":
            context = answer_sql_question(retrieval_question, user_id, session_id)
        else:
            context = search_documents(question, user_id, session_id)
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
        record_message(session_id, "bot", answer)
        return jsonify({
            "answer": answer,
            "type": route["type"],
            "module": route["module"],
            "session_id": session_id,
            "engine": engine,
            "access_denied": denied,
            "rows": context.rows if isinstance(context,QueryEvidence) else [],
            "sources": [{'id':int(i),'title':title} for i,title in re.findall(r'\[Nguồn id=(\d+) \| tiêu đề=([^\]]+)\]',str(context))],
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
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
