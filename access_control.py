from __future__ import annotations

import os
from typing import Any

from db import cursor


INTENT_RULES = (
    ("ask_cost_margin", ("giá vốn", "gia von", "biên lợi nhuận", "bien loi nhuan")),
    ("ask_stock", ("tồn kho", "ton kho", "còn hàng", "con hang", "kho hàng", "kho hang")),
    ("ask_order_status", ("đơn hàng", "don hang", "đơn của", "don cua")),
    ("ask_customer_info", ("khách hàng", "khach hang", "customer")),
    ("ask_sales_policy", ("chiết khấu", "chiet khau", "kịch bản tư vấn", "kich ban tu van")),
    ("ask_tech_procedure", ("kỹ thuật", "ky thuat", "pgm-fi", "bảo dưỡng", "bao duong")),
    ("ask_finance_procedure", ("hoàn tiền", "hoan tien", "tài chính", "tai chinh")),
    ("ask_hr_policy", ("nhân sự", "nhan su", "nghỉ phép", "nghi phep")),
    ("ask_promotion", ("khuyến mãi", "khuyen mai", "trả góp", "tra gop")),
    ("ask_price_list", ("giá", "gia", "mẫu xe", "mau xe", "phiên bản", "phien ban")),
)


def resolve_user_id(session_user_id: int | None, demo_header: str | None, app_env: str | None = None) -> int | None:
    if session_user_id is not None:
        return int(session_user_id)
    if (app_env or os.getenv("APP_ENV", "prod")).lower() == "dev" and demo_header:
        try:
            return int(demo_header)
        except ValueError:
            return None
    return None


def detect_intent(question: str) -> str:
    normalized = question.casefold()
    for intent_code, keywords in INTENT_RULES:
        if any(keyword in normalized for keyword in keywords):
            return intent_code
    return "ask_price_list"


def create_session(user_id: int | None, channel: str = "web") -> int:
    with cursor("app", dictionary=False) as db_cursor:
        db_cursor.execute(
            "INSERT INTO chat_sessions (user_id, channel) VALUES (%s, %s)",
            (user_id, channel),
        )
        db_cursor.connection.commit()
        return int(db_cursor.lastrowid)


def record_message(session_id: int, sender: str, content: str, intent_id: int | None = None) -> None:
    with cursor("app", dictionary=False) as db_cursor:
        db_cursor.execute(
            """
            INSERT INTO chat_messages (session_id, sender, content, detected_intent_id)
            VALUES (%s, %s, %s, %s)
            """,
            (session_id, sender, content, intent_id),
        )
        db_cursor.connection.commit()


def authorize_intent(session_id: int, user_id: int | None, intent_code: str) -> dict[str, Any]:
    with cursor("app") as db_cursor:
        db_cursor.execute(
            """
            SELECT ci.id AS intent_id, ci.required_permission_id,
                   EXISTS (
                       SELECT 1
                       FROM v_user_permissions vup
                       WHERE vup.user_id = %s
                         AND vup.permission_code = p.code
                   ) AS user_allowed,
                   EXISTS (
                       SELECT 1
                       FROM role_permissions rp
                       JOIN roles r ON r.id = rp.role_id
                       WHERE r.name = 'guest'
                         AND rp.permission_id = ci.required_permission_id
                   ) AS guest_allowed
            FROM chatbot_intents ci
            JOIN permissions p ON p.id = ci.required_permission_id
            WHERE ci.code = %s
            """,
            (user_id, intent_code),
        )
        intent = db_cursor.fetchone()
        if intent is None:
            raise ValueError(f"Intent không tồn tại: {intent_code}")

        allowed = bool(intent["user_allowed"] if user_id is not None else intent["guest_allowed"])
        reason = "allowed" if allowed else "denied: thiếu quyền truy cập"
        db_cursor.execute(
            """
            INSERT INTO chatbot_audit_log (session_id, user_id, intent_id, decision, reason)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (session_id, user_id, intent["intent_id"], "allowed" if allowed else "denied", reason),
        )
        db_cursor.connection.commit()

        db_cursor.execute(
            """
            SELECT scope_branch_id
            FROM v_user_permissions
            WHERE user_id = %s
              AND permission_code = (
                  SELECT p.code
                  FROM chatbot_intents ci
                  JOIN permissions p ON p.id = ci.required_permission_id
                  WHERE ci.id = %s
              )
            """,
            (user_id, intent["intent_id"]),
        )
        scopes = [row["scope_branch_id"] for row in db_cursor.fetchall()]

    return {
        "allowed": allowed,
        "intent_id": int(intent["intent_id"]),
        "intent_code": intent_code,
        "scope_branch_ids": None if any(scope is None for scope in scopes) else scopes,
        "denied_message": "Tôi không thể hỗ trợ yêu cầu này.",
    }
