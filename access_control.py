# File này nhận diện intent, tạo phiên chat, ghi lịch sử và kiểm tra quyền trước khi truy xuất dữ liệu.
from __future__ import annotations

import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.
from typing import Any  # Mô tả kiểu dữ liệu cho lịch sử hội thoại và kết quả phân quyền.

from db import cursor  # Mở cursor MySQL để lưu session, message và quyết định quyền.


# Ánh xạ cụm từ người dùng thường nhập sang mã intent lưu trong chatbot_intents.
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


# Dựa vào từ khóa và ngữ cảnh để chọn nhánh xử lý cho detect_intent.
def detect_intent(question: str) -> str:
    # Import tại chỗ để module ngôn ngữ không tạo vòng import khi khởi động ứng dụng.
    from question_language import normalize, asks_available_stock  # Chuẩn hóa câu hỏi và nhận diện mẫu xe.
    normalized = normalize(question)
    for intent_code, keywords in INTENT_RULES:
        # Ưu tiên bộ nhận diện tồn kho để phân biệt câu hỏi còn hàng với giá xe.
        if intent_code == 'ask_stock' and asks_available_stock(question):
            return 'ask_stock'
        if any(normalize(keyword) in normalized for keyword in keywords):
            # Câu hỏi thông số thuộc bảng giá, không phải quy trình sửa chữa.
            if intent_code == 'ask_tech_procedure' and 'thong so' in normalized:
                return 'ask_price_list'
            return intent_code
    # Mặc định định tuyến câu hỏi chưa nhận diện được sang tra cứu bảng giá.
    return "ask_price_list"


# Tạo phiên hội thoại mới và trả ID để các message tiếp theo gắn vào phiên.
def create_session(user_id: int | None, channel: str = "web") -> int:
    with cursor("app", dictionary=False) as db_cursor:
        db_cursor.execute(
            "INSERT INTO chat_sessions (user_id, channel) VALUES (%s, %s)",
            (user_id, channel),
        )
        return int(db_cursor.lastrowid)


# Ghi một message vào chat_messages để lịch sử hội thoại và intent được lưu theo session.
def record_message(session_id: int, sender: str, content: str, intent_id: int | None = None) -> None:
    with cursor("app", dictionary=False) as db_cursor:
        db_cursor.execute(
            """
            INSERT INTO chat_messages (session_id, sender, content, detected_intent_id)
            VALUES (%s, %s, %s, %s)
            """,
            (session_id, sender, content, intent_id),
        )


# Đọc permission của intent trước khi cho phép chatbot chạy SQL hoặc lấy tài liệu.
def authorize_intent(session_id, user_id, intent_code):
    # Tải quyền hiệu lực theo user; guest nhận tập quyền rỗng.
    from security import get_effective_permissions  # Dùng xác thực, permission hoặc audit của backend.
    effective=get_effective_permissions(user_id)
    with cursor() as cur:
        # JOIN intent với permission để biết câu hỏi này cần quyền nào.
        cur.execute("SELECT ci.id AS intent_id,p.code FROM chatbot_intents ci JOIN permissions p ON p.id=ci.required_permission_id WHERE ci.code=%s",(intent_code,))
        intent=cur.fetchone()
        if not intent:raise ValueError("Unknown intent")
        grant=effective.get(intent['code'])
        # Guest chỉ được dùng quyền đọc công khai; quyền own không áp dụng cho intent ngoài danh sách hỗ trợ.
        allowed=bool(grant) and (user_id is not None or intent['code']=='kb:public:read')
        if grant and grant['scope']=='own' and intent_code not in {'ask_customer_info','ask_order_status','ask_price_list','ask_promotion','tool_appointment_create','tool_appointment_list','tool_appointment_update'}:allowed=False
        # Ghi quyết định allowed/denied và lý do để có thể audit lại request.
        cur.execute("INSERT INTO chatbot_audit_log(session_id,user_id,intent_id,decision,reason) VALUES(%s,%s,%s,%s,%s)",(session_id,user_id,intent['intent_id'],'allowed' if allowed else 'denied','Permission granted' if allowed else 'Permission or scope denied'))
        audit_id=cur.lastrowid
    return {'allowed':allowed,'intent_id':intent['intent_id'],'intent_code':intent_code,'audit_id':audit_id,
            'scope_branch_ids':[grant['branch']] if grant and grant['scope']=='branch' else None,
            'own_user_id':user_id if grant and grant['scope']=='own' else None,
            'denied_message':"Tôi không thể hỗ trợ yêu cầu này."}


# Cập nhật audit khi bước kiểm tra sau đó phát hiện request phải bị từ chối.
def mark_audit_denied(audit_id: int, reason: str) -> None:
    with cursor() as cur:
        cur.execute("UPDATE chatbot_audit_log SET decision = 'denied', reason = %s WHERE id = %s", (reason, audit_id))


# Chỉ trả về các view mà quyền hiện tại cho phép; guest chỉ nhận quyền public.
def permitted_views(user_id):
    # Lấy quyền hiệu lực trước khi đối chiếu với danh sách view được đăng ký.
    from security import get_effective_permissions  # Dùng xác thực, permission hoặc audit của backend.
    effective=get_effective_permissions(user_id)
    with cursor() as cur:
        # Registry ánh xạ mỗi view AI với permission cần có để truy cập.
        cur.execute('SELECT ar.view_name,p.code FROM ai_view_registry ar JOIN permissions p ON p.id=ar.required_permission_id')
        return frozenset(r['view_name'] for r in cur.fetchall() if r['code'] in effective and (user_id is not None or r['code']=='kb:public:read'))


# Kiểm tra session thuộc đúng user hiện tại trước khi đọc hoặc ghi tiếp hội thoại.
def resume_session(session_id: int, user_id: int | None) -> bool:
    with cursor() as cur:
        cur.execute("SELECT id FROM chat_sessions WHERE id = %s AND user_id <=> %s", (session_id, user_id))
        return cur.fetchone() is not None


# Đọc tối đa limit message mới nhất rồi đảo lại để context giữ đúng thứ tự hội thoại.
def read_history(session_id: int, limit: int = 10) -> list[dict]:
    with cursor() as cur:
        cur.execute("SELECT sender, content FROM chat_messages WHERE session_id = %s ORDER BY id DESC LIMIT %s", (session_id, limit))
        return list(reversed(cur.fetchall()))
