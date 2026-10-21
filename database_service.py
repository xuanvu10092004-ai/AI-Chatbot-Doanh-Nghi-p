# File này gom các truy vấn đọc phục vụ dashboard và màn hình tổng quan.
from __future__ import annotations

from typing import Any  # Khai báo kiểu dữ liệu cho tham số và kết quả.

from db import cursor  # Mở cursor hoặc connection MySQL.


# Báo cho route biết một màn hình cũ chưa có bảng phù hợp trong schema hiện tại.
class SchemaExtensionRequired(RuntimeError):
    """Raised when an unsupported legacy module needs a future schema extension."""



# Đếm dữ liệu từ nguồn whitelist; riêng sản phẩm đếm model khác nhau thay vì phiên bản.
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


# Gom các số đếm dùng cho dashboard vào một cấu trúc thống nhất.
def get_dashboard_stats() -> dict[str, int]:
    return {
        "customers": get_count("customers"),
        "products": get_count("products"),
        "inventory": get_count("inventory"),
        "orders": get_count("orders"),
        "documents": get_count("documents"),
        "chat_messages": get_count("chat_messages"),
    }


# Lấy phiên bản còn 1 đến ngưỡng tồn thấp và phiên bản hết hàng trong view tồn kho.
def get_low_stock_products(limit: int = 5) -> list[dict[str, Any]]:
    from inventory_policy import LOW_STOCK_THRESHOLD  # Dùng quy tắc xác định tình trạng tồn kho.
    bounded_limit = max(1, min(int(limit), 100))
    with cursor("app") as db_cursor:
        # Sắp hết hàng: quantity > 0 AND quantity < 10
        db_cursor.execute(
            """
            SELECT branch_code, branch_name, model_name, variant_name, color,
                   quantity, list_price, 'Sắp hết hàng' AS stock_status
            FROM v_ai_inventory
            WHERE quantity > 0 AND quantity < %s
            ORDER BY quantity ASC, model_name, variant_name
            LIMIT %s
            """,
            (LOW_STOCK_THRESHOLD, bounded_limit),
        )
        low_stock = list(db_cursor.fetchall())
        # Hết hàng: quantity = 0
        db_cursor.execute(
            """
            SELECT branch_code, branch_name, model_name, variant_name, color,
                   quantity, list_price, 'Hết hàng' AS stock_status
            FROM v_ai_inventory
            WHERE quantity = 0
            ORDER BY model_name, variant_name
            LIMIT %s
            """,
            (bounded_limit,),
        )
        out_of_stock = list(db_cursor.fetchall())
        return low_stock + out_of_stock


# Trả khách ở các trạng thái tiềm năng, đang tư vấn hoặc đã mua theo tên.
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
