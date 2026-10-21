# File này lập kế hoạch, kiểm tra quyền và thực thi truy vấn cho chatbot.
from __future__ import annotations

from typing import Any  # Mô tả kiểu tham số và kết quả thực thi truy vấn.

from access_control import authorize_intent, create_session, detect_intent, permitted_views  # Dùng session, intent và quyền của chatbot.
from query_plans import plan_query, NeedsGeneratedQuery  # Tạo kế hoạch truy vấn tồn kho theo câu hỏi.
from llm_sql import generate_query, QueryClarification  # Sinh truy vấn SQL và bind literal thành tham số.
from sql_guard import SqlRejected  # Kiểm tra whitelist AST của truy vấn SQL.
from answer_renderer import QueryEvidence  # Định dạng kết quả truy vấn thành nội dung hiển thị.
from db import get_connection  # Mở cursor hoặc connection MySQL.
from sql_safety import validate_sql  # Kiểm tra validator và timeout truy vấn SQL.


AI_VIEWS = frozenset(
    {
        "v_ai_products",
        "v_ai_inventory",
        "v_ai_customers",
        "v_ai_orders",
        "v_ai_product_costs",
    }
)


# Báo route rằng schema chuẩn chưa có bảng cho module nghiệp vụ cũ.
class SchemaExtensionRequired(RuntimeError):
    """Raised when a legacy module has no table in the Honda schema."""


def _format_rows(rows: list[dict[str, Any]], generated: bool = False, summary: str | None = None) -> str:
    if not rows:
        return "Không tìm thấy dữ liệu phù hợp."
    lines = ([summary] if summary else []) + [f"Tìm thấy {len(rows)} bản ghi:"]
    for row in rows:
        values = " | ".join(f"{key}: {value}" for key, value in row.items())
        lines.append(values)
    return QueryEvidence("\n".join(lines), rows, generated, summary)


# Chạy truy vấn bằng connection read-only; scope chi nhánh được thêm bằng parameters ở bước này.
def _execute_text_to_sql(sql: str, params: tuple[Any, ...] = (), *, allowed_views=None, scope_branch_ids=None, own_user_id=None) -> list[dict[str, Any]]:
    # Kiểm tra truy vấn trước khi mở connection read-only và áp scope bằng session variables.
    validated = validate_sql(sql, frozenset({'v_ai_products'} if allowed_views is None else allowed_views))
    if scope_branch_ids is not None and len(scope_branch_ids) != 1:
        raise ValueError("ambiguous_branch_scope")
    connection = get_connection("text_to_sql")
    db_cursor = None
    try:
        db_cursor = connection.cursor(dictionary=True)
        db_cursor.execute("SET @ai_branch = %s", (scope_branch_ids[0] if scope_branch_ids else None,))
        db_cursor.execute('SET @ai_user = %s',(own_user_id,))
        # Chọn tên biến timeout phù hợp giữa MySQL và MariaDB.
        db_cursor.execute("SELECT VERSION() AS version")
        version = db_cursor.fetchone()['version']
        if 'MariaDB' in version:
            db_cursor.execute("SET SESSION max_statement_time = %s", (validated.timeout_ms / 1000,))
        else:
            db_cursor.execute("SET SESSION MAX_EXECUTION_TIME = %s", (validated.timeout_ms,))
        db_cursor.execute(validated.sql, params)
        return list(db_cursor.fetchall())
    finally:
        if db_cursor is not None:
            try:
                db_cursor.execute("SET @ai_branch = NULL")
                db_cursor.execute('SET @ai_user = NULL')
            finally:
                db_cursor.close()
        connection.close()


def _branch_clause(scope_branch_ids: list[int] | None) -> tuple[str, tuple[int, ...]]:
    # Biến scope rỗng thành điều kiện không trả dòng; không có scope thì không thêm lọc.
    if scope_branch_ids is None:
        return "", ()
    if not scope_branch_ids:
        return " AND 1 = 0", ()
    placeholders = ", ".join(["%s"] * len(scope_branch_ids))
    return f" AND branch_id IN ({placeholders})", tuple(scope_branch_ids)


# Xác định intent và quyền trước, sau đó mới chọn kế hoạch SQL hoặc yêu cầu LLM sinh truy vấn.
def answer_sql_question(
    question: str,
    user_id: int | None = None,
    session_id: int | None = None,
    include_inventory_details: bool = False,
) -> str:
    # Ghi nhận intent và quyết định quyền trước khi tạo hoặc thực thi SQL.
    if session_id is None:
        session_id = create_session(user_id)
    intent_code = detect_intent(question)
    authorization = authorize_intent(session_id, user_id, intent_code)
    if not authorization["allowed"]:
        return authorization["denied_message"]

    if any(word in question.casefold() for word in ("cơ hội", "co hoi", "báo giá", "bao gia", "booking")):
        raise SchemaExtensionRequired(
            "Opportunity, Quote và Booking cần schema-extension; chưa được tự thiết kế bảng."
        )

    # Giới hạn các view theo intent rồi giao với quyền view của user.
    intent_views = {
        'ask_price_list': {'v_ai_products'},
        'ask_stock': {'v_ai_products', 'v_ai_inventory'},
        'ask_customer_info': {'v_ai_products', 'v_ai_customers'},
        'ask_order_status': {'v_ai_products', 'v_ai_orders'},
        'ask_cost_margin': {'v_ai_products', 'v_ai_product_costs'},
    }
    allowed_views = permitted_views(user_id) & intent_views.get(intent_code, set())
    generated = False
    # Thử kế hoạch SQL có sẵn trước; chỉ gọi LLM khi cần nhóm/điều kiện phức tạp.
    try:
        try:
            sql, params = plan_query(question, intent_code)
        except NeedsGeneratedQuery:
            sql, params = generate_query(question, frozenset(allowed_views))
            generated = True
    except QueryClarification as exc:
        return 'Cần làm rõ: ' + str(exc)
    except (SqlRejected, ValueError):
        from access_control import mark_audit_denied  # Dùng session, intent và quyền của chatbot.
        mark_audit_denied(authorization['audit_id'], 'SQL bị chặn bởi whitelist hoặc validator')
        return authorization['denied_message']
    except Exception:
        return 'Chưa phân tích được câu hỏi lúc này. Bạn hãy thử lại hoặc nêu rõ mẫu xe và điều kiện.'
    rows = _execute_text_to_sql(sql, params, allowed_views=allowed_views,
                                scope_branch_ids=authorization['scope_branch_ids'],own_user_id=authorization['own_user_id'])
    if include_inventory_details and intent_code=='ask_stock' and len(rows)==1 and set(rows[0])=={'total_stock'}:
        total=rows[0]['total_stock'] or 0
        detail_sql,detail_params=plan_query(question+' chi tiết theo sản phẩm theo chi nhánh',intent_code)
        details=_execute_text_to_sql(detail_sql,detail_params,allowed_views=allowed_views,
                                    scope_branch_ids=authorization['scope_branch_ids'],own_user_id=authorization['own_user_id'])
        summary=f'Tổng tồn kho: {int(total):,} xe. Chi tiết theo từng phiên bản và chi nhánh trong phạm vi được cấp.'.replace(',','.')
        if len(details)==100:summary+=' Hiển thị tối đa 100 dòng; mở trang Tồn kho để xem tiếp.'
        return QueryEvidence(f'total_stock: {total}\n'+str(_format_rows(details)),details,generated,summary)
    from question_language import normalize, product_patterns, asks_available_stock  # Chuẩn hóa câu hỏi và nhận diện mẫu xe.
    patterns = product_patterns(question)
    if not rows and intent_code == 'ask_stock' and asks_available_stock(question):
        return 'Không tìm thấy dữ liệu tồn kho phù hợp trong phạm vi bạn được xem. Hãy kiểm tra lại mẫu xe hoặc chi nhánh cần tra cứu.'
    summary = None
    from inventory_policy import asks_low_stock  # Dùng quy tắc xác định tình trạng tồn kho.
    if intent_code == 'ask_stock' and asks_low_stock(question):
        summary = 'Sắp hết hàng là còn 1–4 xe theo phiên bản và chi nhánh; số lượng 0 là hết hàng.'
        if not rows:
            return 'Không tìm thấy phiên bản còn 1–4 xe trong phạm vi bạn được xem.'
    if rows:
        if intent_code == 'ask_stock' and asks_available_stock(question):
            summary = 'Các phiên bản còn xe tại những chi nhánh dưới đây, trong phạm vi bạn được xem.'
        if 'so sanh' in normalize(question) and len(patterns) >= 2:
            import re  # Tìm và chuẩn hóa mẫu văn bản bằng biểu thức chính quy.
            missing = [pattern.strip('%').replace('%', ' ') for pattern in patterns
                       if not any(re.search('.*'.join(re.escape(normalize(part)) for part in pattern.split('%')),
                                            normalize(str(row.get('model_name', '')))) for row in rows)]
            summary = 'So sánh thông số và giá niêm yết theo từng phiên bản có dữ liệu.'
            if missing:
                summary = ('Chưa tìm thấy dữ liệu cho ' + ', '.join(missing)
                                    + ' trong phạm vi tra cứu; chưa đủ dữ liệu để so sánh đầy đủ. '
                                    + 'Bảng dưới chỉ hiển thị các mẫu đã tìm thấy, không thay thế mẫu xe bạn hỏi.')
    return _format_rows(rows, generated, summary)
