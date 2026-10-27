# File này nhận diện intent, tạo phiên chat, ghi lịch sử và kiểm tra quyền trước khi truy xuất dữ liệu.
from __future__ import annotations

import os  # Đọc biến môi trường hoặc thông tin hệ điều hành được dùng trong file.
import re  # Nhận diện cách diễn đạt tự nhiên sau khi chuẩn hóa tiếng Việt.
from typing import Any  # Mô tả kiểu dữ liệu cho lịch sử hội thoại và kết quả phân quyền.

from db import cursor  # Mở cursor MySQL để lưu session, message và quyết định quyền.


# Ánh xạ cụm từ người dùng thường nhập sang mã intent lưu trong chatbot_intents.
INTENT_RULES = (
    ("ask_cost_margin", ("giá vốn", "gia von", "biên lợi nhuận", "bien loi nhuan", "giá nhập", "giá mua vào")),
    ("ask_stock", ("tồn kho", "ton kho", "còn hàng", "con hang", "kho hàng", "kho hang", "kiểm hàng", "kiem hang", "kiểm tra hàng", "kiem tra hang", "kiểm kê", "kiem ke", "danh sách tồn", "danh sach ton")),
    ("ask_order_status", ("đơn hàng", "don hang", "đơn của", "don cua")),
    ("ask_order_status", ("doanh thu", "thuần")),
    ("ask_stock", ("hết hàng", "het hang", "trong kho", "sắp hết", "tồn thấp")),
    ("ask_customer_info", ("khách hàng", "khach hang", "customer")),
    ("ask_sales_policy", ("chiết khấu", "chiet khau", "kịch bản tư vấn", "kich ban tu van")),
    ("ask_tech_procedure", ("kỹ thuật", "ky thuat", "pgm-fi", "bảo dưỡng", "bao duong")),
    ("ask_finance_procedure", ("hoàn tiền", "hoan tien", "tài chính", "tai chinh")),
    ("ask_hr_policy", ("nhân sự", "nhan su", "nghỉ phép", "nghi phep")),
    ("ask_promotion", ("khuyến mãi", "khuyen mai", "trả góp", "tra gop")),
    ("ask_price_list", ("giá", "gia", "mẫu xe", "mau xe", "phiên bản", "phien ban", "sản phẩm", "san pham")),
)

# Các mẫu ngữ nghĩa đơn giản giúp hiểu câu hỏi đời thường trước khi dùng bộ từ khóa cũ.
# Mẫu chỉ phân loại ý định; quyền và truy vấn SQL vẫn được kiểm tra ở các bước sau.
NATURAL_INTENT_RULES = (
    ('ask_cost_margin', (r'\b(?:gia von|gia nhap|gia mua vao|bien loi nhuan)\b',)),
    ('ask_stock', (
        r'\bkiem(?: tra| ke)?\b.*\b(?:hang|xe|kho|ton)\b',
        r'\b(?:kho|ton kho)\b.*\b(?:con|co|het|thieu|xe|hang|nao)\b',
        r'\b(?:xe|hang)\b.*\b(?:con hang|con xe|o dau|chi nhanh|dai ly|cua hang)\b',
        r'\bcon\b.*\b(?:o dau|chi nhanh|dai ly|cua hang)\b',
        r'\b(?:chi nhanh|dai ly|cua hang)\b.*\b(?:con|co|het)\b',
        r'\b(?:sap het|het hang|con hang|con xe)\b',
        r'\bcon\b.*\b(?:may|bao nhieu|chiec|xe|hang)\b',
        r'\b(?:kho|ton)\b.*\b(?:duoi|it|thap|muc)\b',
        r'\bton kho\b',
        r'\b(?:tim|xem|liet ke|cho toi)\b.*\b(?:con|het|ton)\b',
        r'\b(?:chi nhanh|dai ly|cua hang)\b.*\b(?:co|dang co|nhung xe)\b',
        r'\b(?:so luong bang 0|het ton|da het|con rat it)\b',
    )),
    ('ask_customer_info', (
        r'\b(?:khach|khach hang|nguoi mua|ho so khach)\b',
        r'\b(?:ai|nguoi nao)\b.*\b(?:da mua|dang tu van|cho tu van)\b',
    )),
    ('ask_order_status', (
        r'\b(?:don|don hang|phieu ban)\b.*\b(?:nao|nay|minh|toi|den dau|trang thai)\b',
        r'\b(?:don hang|doanh thu)\b',
        r'\b(?:tong|tat ca|bao nhieu)\b.*\b(?:don|don hang|giao dich)\b',
        r'\b(?:don|don hang)\b.*\b(?:bao nhieu|tong|tat ca)\b',
        r'\b(?:dem|so luong|xem so)\b.*\bdon\b',
        r'\b(?:doanh so|ban duoc|tong tien ban hang|ban hang)\b',
        r'\b(?:kiem tra|xem|theo doi)\b.*\b(?:tinh trang|trang thai)\b.*\bdon\b',
        r'\b(?:don|cac don)\b.*\b(?:cho|xu ly|xong)\b',
    )),
    ('ask_price_list', (
        r'\b(?:san pham|mau xe|phien ban|danh muc|bang gia|thong so)\b',
        r'\b(?:xem|tim|tra|tra cuu|cho toi|giup toi)\b.*\b(?:xe|mau|san pham|phien ban)\b',
        r'\b(?:xe|mau)\b.*\b(?:gia|ban|dang ban|thong so)\b',
    )),
)


def _detect_natural_intent(normalized: str) -> str | None:
    # Các cụm đặc biệt được ưu tiên để tránh nhầm ý định tự nhiên.
    if re.search(r"\b(?:gia von|gia nhap|nhap vao gia|nhap gia|chi phi von|xem cost|cost|xem von)\b", normalized):
        return "ask_cost_margin"
    if re.search(r"\b(?:doanh so|doanh thu|ban duoc|tong tien ban hang)\b", normalized):
        return "ask_order_status"
    if re.search(r"\b(?:kiem tra|xem|theo doi)\b.*\b(?:tinh trang|trang thai)\b.*\bdon\b", normalized):
        return "ask_order_status"
    if re.search(r"\b(?:ton tai|gan het)\b", normalized):
        return "ask_stock"
    if re.search(r"\b(?:nt01|nt02|cr01)\b.*\b(?:dang co|co hang|hang xe|nhung xe|o dau)\b", normalized):
        return "ask_stock"
    if re.search(r"\b(?:mau xe|xe ga|tay ga|xe so)\b.*\b(?:con|het|so luong)\b", normalized):
        return "ask_stock"
    if re.search(r"\b(?:khach hang|du lieu khach|nguoi da mua|nguoi mua|ho so khach)\b", normalized):
        return "ask_customer_info"
    if re.search(r"\b(?:xe con tay|xe ga|tay ga|xe so)\b.*\b(?:gia|bao nhieu)\b", normalized):
        return "ask_price_list"
    for intent_code, patterns in NATURAL_INTENT_RULES:
        if any(re.search(pattern, normalized) for pattern in patterns):
            return intent_code
    return None

# Dựa vào từ khóa và ngữ cảnh để chọn nhánh xử lý cho detect_intent.
def detect_intent(question: str) -> str:
    # Import tại chỗ để module ngôn ngữ không tạo vòng import khi khởi động ứng dụng.
    from question_language import normalize, asks_available_stock  # Chuẩn hóa câu hỏi và nhận diện mẫu xe.
    normalized = normalize(question)
    natural_intent = _detect_natural_intent(normalized)
    if natural_intent:
        return natural_intent
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
