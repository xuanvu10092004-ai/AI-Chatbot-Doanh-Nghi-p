from __future__ import annotations

from typing import Any

from access_control import authorize_intent, create_session, detect_intent
from db import get_connection
from sql_safety import validate_sql


AI_VIEWS = frozenset(
    {
        "v_ai_products",
        "v_ai_inventory",
        "v_ai_customers",
        "v_ai_orders",
        "v_ai_product_costs",
    }
)


class SchemaExtensionRequired(RuntimeError):
    """Raised when a legacy module has no table in the Honda schema."""


def _format_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Không tìm thấy dữ liệu phù hợp."
    lines = [f"Tìm thấy {len(rows)} bản ghi:"]
    for row in rows:
        values = " | ".join(f"{key}: {value}" for key, value in row.items())
        lines.append(values)
    return "\n".join(lines)


def _execute_text_to_sql(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    validated = validate_sql(sql, AI_VIEWS)
    connection = get_connection("text_to_sql")
    db_cursor = connection.cursor(dictionary=True)
    try:
        db_cursor.execute(validated.sql, params)
        return list(db_cursor.fetchall())
    finally:
        db_cursor.close()
        connection.close()


def _branch_clause(scope_branch_ids: list[int] | None) -> tuple[str, tuple[int, ...]]:
    if scope_branch_ids is None:
        return "", ()
    if not scope_branch_ids:
        return " AND 1 = 0", ()
    placeholders = ", ".join(["%s"] * len(scope_branch_ids))
    return f" AND branch_id IN ({placeholders})", tuple(scope_branch_ids)


def answer_sql_question(
    question: str,
    user_id: int | None = None,
    session_id: int | None = None,
) -> str:
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

    scopes = authorization["scope_branch_ids"]
    branch_sql, branch_params = _branch_clause(scopes)
    normalized = question.casefold()

    if intent_code == "ask_cost_margin":
        sql = """
            SELECT model_name, variant_name, color, list_price, cost_price, gross_margin
            FROM v_ai_product_costs
            WHERE model_name LIKE %s
            ORDER BY model_name, variant_name
            LIMIT 100
        """
        rows = _execute_text_to_sql(sql, ("%SH%" if "sh" in normalized else "%",))
        return _format_rows(rows)

    if intent_code == "ask_stock":
        sql = f"""
            SELECT branch_code, branch_name, model_name, variant_name, color,
                   quantity, list_price
            FROM v_ai_inventory
            WHERE 1 = 1{branch_sql}
            ORDER BY quantity DESC, model_name, variant_name
            LIMIT 100
        """
        return _format_rows(_execute_text_to_sql(sql, branch_params))

    if intent_code == "ask_customer_info":
        sql = """
            SELECT customer_id, full_name, phone, email, province, district, customer_status
            FROM v_ai_customers
            ORDER BY full_name
            LIMIT 100
        """
        return _format_rows(_execute_text_to_sql(sql))

    if intent_code == "ask_order_status":
        sql = f"""
            SELECT order_id, customer_name, model_name, variant_name, branch_code,
                   quantity, line_amount, status, created_at
            FROM v_ai_orders
            WHERE 1 = 1{branch_sql}
            ORDER BY created_at DESC
            LIMIT 100
        """
        return _format_rows(_execute_text_to_sql(sql, branch_params))

    sql = """
        SELECT model_name, variant_name, color, segment, engine_cc, list_price, total_stock
        FROM v_ai_products
        WHERE model_name LIKE %s
        ORDER BY model_name, list_price
        LIMIT 100
    """
    model_pattern = "%SH 160i%" if "sh 160i" in normalized else "%"
    return _format_rows(_execute_text_to_sql(sql, (model_pattern,)))
