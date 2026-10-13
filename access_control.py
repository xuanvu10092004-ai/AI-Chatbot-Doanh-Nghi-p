from __future__ import annotations

import os
from typing import Any

from db import cursor


INTENT_RULES = (
    ("ask_cost_margin", ("giá vốn", "gia von", "biên lợi nhuận", "bien loi nhuan", "giá nhập", "giá mua vào")),
    ("ask_stock", ("tồn kho", "ton kho", "còn hàng", "con hang", "kho hàng", "kho hang")),
    ("ask_order_status", ("đơn hàng", "don hang", "đơn của", "don cua")),
    ("ask_order_status", ("doanh thu", "thuần")),
    ("ask_stock", ("hết hàng", "het hang", "trong kho")),
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
        try:
            value = int(session_user_id)
            return value if value > 0 else None
        except (ValueError, TypeError):
            return None
    if (app_env or os.getenv("APP_ENV", "prod")).lower() == "dev" and demo_header:
        try:
            value = int(demo_header)
            return value if value > 0 else None
        except ValueError:
            return None
    return None


def detect_intent(question: str) -> str:
    from question_language import normalize
    normalized = normalize(question)
    for intent_code, keywords in INTENT_RULES:
        if any(normalize(keyword) in normalized for keyword in keywords):
            if intent_code == 'ask_tech_procedure' and 'thong so' in normalized:
                return 'ask_price_list'
            return intent_code
    return "ask_price_list"


def create_session(user_id: int | None, channel: str = "web") -> int:
    with cursor("app", dictionary=False) as db_cursor:
        db_cursor.execute(
            "INSERT INTO chat_sessions (user_id, channel) VALUES (%s, %s)",
            (user_id, channel),
        )
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
        db_cursor.execute("SELECT scope_branch_id FROM v_user_permissions WHERE user_id = %s AND permission_code = (SELECT code FROM permissions WHERE id = %s)", (user_id, intent["required_permission_id"]))
        scope_rows = [r['scope_branch_id'] for r in db_cursor.fetchall()]
        if None not in scope_rows and len(set(scope_rows)) > 1:
            allowed = False
        reason = "allowed" if allowed else "denied: thiếu quyền truy cập"
        db_cursor.execute(
            """
            INSERT INTO chatbot_audit_log (session_id, user_id, intent_id, decision, reason)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (session_id, user_id, intent["intent_id"], "allowed" if allowed else "denied", reason),
        )
        audit_id = int(db_cursor.lastrowid)

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
        "audit_id": audit_id,
        "allowed": allowed,
        "intent_id": int(intent["intent_id"]),
        "intent_code": intent_code,
        "scope_branch_ids": None if user_id is None or any(scope is None for scope in scopes) else sorted(set(scopes)),
        "denied_message": "Tôi không thể hỗ trợ yêu cầu này.",
    }


def mark_audit_denied(audit_id: int, reason: str) -> None:
    with cursor() as cur:
        cur.execute("UPDATE chatbot_audit_log SET decision = 'denied', reason = %s WHERE id = %s", (reason, audit_id))


def permitted_views(user_id: int | None) -> frozenset[str]:
    with cursor() as cur:
        cur.execute("""
            SELECT ar.view_name FROM ai_view_registry ar
            JOIN permissions p ON p.id = ar.required_permission_id
            WHERE EXISTS (SELECT 1 FROM v_user_permissions vp
                WHERE vp.user_id = %s AND vp.permission_code = p.code)
            OR (%s IS NULL AND EXISTS (SELECT 1 FROM role_permissions rp
                JOIN roles r ON r.id = rp.role_id
                WHERE r.name = 'guest' AND rp.permission_id = p.id))
        """, (user_id, user_id))
        return frozenset(r['view_name'] for r in cur.fetchall())


def resume_session(session_id: int, user_id: int | None) -> bool:
    with cursor() as cur:
        cur.execute("SELECT id FROM chat_sessions WHERE id = %s AND user_id <=> %s", (session_id, user_id))
        return cur.fetchone() is not None


def read_history(session_id: int, limit: int = 10) -> list[dict]:
    with cursor() as cur:
        cur.execute("SELECT sender, content FROM chat_messages WHERE session_id = %s ORDER BY id DESC LIMIT %s", (session_id, limit))
        return list(reversed(cur.fetchall()))
