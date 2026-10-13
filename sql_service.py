from __future__ import annotations

from typing import Any

from access_control import authorize_intent, create_session, detect_intent, permitted_views
from query_plans import plan_query
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


def _execute_text_to_sql(sql: str, params: tuple[Any, ...] = (), *, allowed_views=None, scope_branch_ids=None) -> list[dict[str, Any]]:
    validated = validate_sql(sql, frozenset({'v_ai_products'} if allowed_views is None else allowed_views))
    if scope_branch_ids is not None and len(scope_branch_ids) != 1:
        raise ValueError("ambiguous_branch_scope")
    connection = get_connection("text_to_sql")
    db_cursor = None
    try:
        db_cursor = connection.cursor(dictionary=True)
        db_cursor.execute("SET @ai_branch = %s", (scope_branch_ids[0] if scope_branch_ids else None,))
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

    sql, params = plan_query(question, intent_code)
    rows = _execute_text_to_sql(sql, params, allowed_views=permitted_views(user_id),
                                scope_branch_ids=authorization['scope_branch_ids'])
    return _format_rows(rows)
