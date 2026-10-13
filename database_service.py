from __future__ import annotations

from typing import Any

from db import cursor


class SchemaExtensionRequired(RuntimeError):
    """Raised when an unsupported legacy module needs a future schema extension."""



def get_count(source: str) -> int:
    allowed_sources = {
        "customers": "v_ai_customers",
        "inventory": "v_ai_inventory",
        "products": "v_ai_products",
        "orders": "v_ai_orders",
        "documents": "kb_documents",
        "chat_messages": "chat_messages",
    }
    if source not in allowed_sources:
        raise ValueError("Nguồn đếm không hợp lệ")
    expression = "COUNT(DISTINCT product_id)" if source == "products" else "COUNT(*)"
    with cursor("app") as db_cursor:
        db_cursor.execute(f"SELECT {expression} AS total FROM {allowed_sources[source]}")
        return int(db_cursor.fetchone()["total"])


def get_dashboard_stats() -> dict[str, int]:
    return {
        "customers": get_count("customers"),
        "products": get_count("products"),
        "inventory": get_count("inventory"),
        "orders": get_count("orders"),
        "documents": get_count("documents"),
        "chat_messages": get_count("chat_messages"),
    }


def get_low_stock_products(limit: int = 5) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(int(limit), 100))
    with cursor("app") as db_cursor:
        db_cursor.execute(
            """
            SELECT branch_code, branch_name, model_name, variant_name, color,
                   quantity, list_price
            FROM v_ai_inventory
            WHERE quantity < %s
            ORDER BY quantity ASC, model_name, variant_name
            LIMIT %s
            """,
            (10, bounded_limit),
        )
        return list(db_cursor.fetchall())


def get_potential_customers(limit: int = 5) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(int(limit), 100))
    with cursor("app") as db_cursor:
        db_cursor.execute(
            """
            SELECT customer_id, full_name, phone, email, province, district,
                   customer_status
            FROM v_ai_customers
            WHERE customer_status IN (%s, %s, %s)
            ORDER BY full_name
            LIMIT %s
            """,
            ("Tiềm năng", "Đang tư vấn", "Đã mua", bounded_limit),
        )
        return list(db_cursor.fetchall())


def unsupported_legacy_module(module: str) -> None:
    raise SchemaExtensionRequired(
        f"{module} chưa được hỗ trợ: cần schema-extension, chưa được tự thiết kế bảng."
    )
