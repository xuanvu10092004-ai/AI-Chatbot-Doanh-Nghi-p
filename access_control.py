from __future__ import annotations

import os
from typing import Any

from db import cursor


INTENT_RULES = (
    ("ask_cost_margin", ("giá vốn", "gia von", "biên lợi nhuận", "bien loi nhuan", "giá nhập", "giá mua vào")),
    ("ask_stock", ("tồn kho", "ton kho", "còn hàng", "con hang", "kho hàng", "kho hang")),
    ("ask_order_status", ("đơn hàng", "don hang", "đơn của", "don cua")),
    ("ask_order_status", ("doanh thu", "thuần")),
    ("ask_stock", ("hết hàng", "het hang", "trong kho", "sắp hết", "tồn thấp")),
    ("ask_customer_info", ("khách hàng", "khach hang", "customer")),
    ("ask_sales_policy", ("chiết khấu", "chiet khau", "kịch bản tư vấn", "kich ban tu van")),
    ("ask_tech_procedure", ("kỹ thuật", "ky thuat", "pgm-fi", "bảo dưỡng", "bao duong")),
    ("ask_finance_procedure", ("hoàn tiền", "hoan tien", "tài chính", "tai chinh")),
    ("ask_hr_policy", ("nhân sự", "nhan su", "nghỉ phép", "nghi phep")),
    ("ask_promotion", ("khuyến mãi", "khuyen mai", "trả góp", "tra gop")),
    ("ask_price_list", ("giá", "gia", "mẫu xe", "mau xe", "phiên bản", "phien ban")),
)


def detect_intent(question: str) -> str:
    from question_language import normalize, asks_available_stock
    normalized = normalize(question)
    for intent_code, keywords in INTENT_RULES:
        if intent_code == 'ask_stock' and asks_available_stock(question):
            return 'ask_stock'
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


def authorize_intent(session_id, user_id, intent_code):
    from security import get_effective_permissions
    effective=get_effective_permissions(user_id)
    with cursor() as cur:
        cur.execute("SELECT ci.id AS intent_id,p.code FROM chatbot_intents ci JOIN permissions p ON p.id=ci.required_permission_id WHERE ci.code=%s",(intent_code,))
        intent=cur.fetchone()
        if not intent:raise ValueError("Unknown intent")
        grant=effective.get(intent['code'])
        allowed=bool(grant) and (user_id is not None or intent['code']=='kb:public:read')
        if grant and grant['scope']=='own' and intent_code not in {'ask_customer_info','ask_order_status','ask_price_list','ask_promotion'}:allowed=False
        cur.execute("INSERT INTO chatbot_audit_log(session_id,user_id,intent_id,decision,reason) VALUES(%s,%s,%s,%s,%s)",(session_id,user_id,intent['intent_id'],'allowed' if allowed else 'denied','Permission granted' if allowed else 'Permission or scope denied'))
        audit_id=cur.lastrowid
    return {'allowed':allowed,'intent_id':intent['intent_id'],'intent_code':intent_code,'audit_id':audit_id,
            'scope_branch_ids':[grant['branch']] if grant and grant['scope']=='branch' else None,
            'own_user_id':user_id if grant and grant['scope']=='own' else None,
            'denied_message':"Tôi không thể hỗ trợ yêu cầu này."}


def mark_audit_denied(audit_id: int, reason: str) -> None:
    with cursor() as cur:
        cur.execute("UPDATE chatbot_audit_log SET decision = 'denied', reason = %s WHERE id = %s", (reason, audit_id))


def permitted_views(user_id):
    from security import get_effective_permissions
    effective=get_effective_permissions(user_id)
    with cursor() as cur:
        cur.execute('SELECT ar.view_name,p.code FROM ai_view_registry ar JOIN permissions p ON p.id=ar.required_permission_id')
        return frozenset(r['view_name'] for r in cur.fetchall() if r['code'] in effective and (user_id is not None or r['code']=='kb:public:read'))


def resume_session(session_id: int, user_id: int | None) -> bool:
    with cursor() as cur:
        cur.execute("SELECT id FROM chat_sessions WHERE id = %s AND user_id <=> %s", (session_id, user_id))
        return cur.fetchone() is not None


def read_history(session_id: int, limit: int = 10) -> list[dict]:
    with cursor() as cur:
        cur.execute("SELECT sender, content FROM chat_messages WHERE session_id = %s ORDER BY id DESC LIMIT %s", (session_id, limit))
        return list(reversed(cur.fetchall()))
