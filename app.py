from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, render_template, request, session

from access_control import create_session, record_message, resolve_user_id
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


app = Flask(__name__)
secret_key = os.getenv("FLASK_SECRET_KEY")
if secret_key:
    app.secret_key = secret_key


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    try:
        return jsonify(get_dashboard_stats())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/low-stock", methods=["GET"])
def low_stock():
    try:
        return jsonify(get_low_stock_products())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/potential-customers", methods=["GET"])
def potential_customers():
    try:
        return jsonify(get_potential_customers())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def _current_user_id() -> int | None:
    session_user_id = session.get("user_id") if secret_key else None
    return resolve_user_id(
        session_user_id,
        request.headers.get("X-Demo-User-Id"),
        os.getenv("APP_ENV", "prod"),
    )


def _legacy_not_implemented(module: str):
    return jsonify({
        "error": "schema-extension-required",
        "message": f"{module} chưa có trong schema Honda; chưa tự thiết kế bảng.",
    }), 501


@app.route("/api/opportunities", methods=["GET", "POST"])
def opportunities():
    return _legacy_not_implemented("Opportunity")


@app.route("/api/quotes", methods=["GET", "POST"])
def quotes():
    return _legacy_not_implemented("Quote")


@app.route("/api/bookings", methods=["GET", "POST"])
def bookings():
    return _legacy_not_implemented("Booking")


@app.route("/chat", methods=["POST"])
def chat():
    data: dict[str, Any] = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    if not question:
        return jsonify({"answer": "Vui lòng nhập câu hỏi.", "type": "None", "module": "None"}), 400

    user_id = _current_user_id()
    session_id = create_session(user_id, "web")
    record_message(session_id, "user", question)
    route = route_question(question)

    try:
        if route["type"] == "SQL":
            context = answer_sql_question(question, user_id, session_id)
        else:
            context = search_documents(question, user_id, session_id)
        denied = context == "Tôi không thể hỗ trợ yêu cầu này."
        answer = context if denied else generate_answer(question, context)
        record_message(session_id, "bot", answer)
        return jsonify({
            "answer": answer,
            "type": route["type"],
            "module": route["module"],
            "session_id": session_id,
        })
    except SchemaExtensionRequired as exc:
        message = str(exc)
        record_message(session_id, "bot", message)
        return jsonify({"error": "schema-extension-required", "message": message}), 501
    except Exception as exc:
        message = f"Lỗi backend: {exc}"
        record_message(session_id, "bot", message)
        return jsonify({"error": "backend-error", "message": message}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
