# File này đọc metadata từ information_schema để tạo context cho prompt SQL.
from __future__ import annotations

from typing import Any  # Mô tả connection và các hàng metadata trả về từ information_schema.


AI_VIEW_PATTERN = "v_ai_%"
SCHEMA_SYNONYMS = {
    "xe ga": "tay_ga",
    "xe số": "xe_so",
    "xe côn": "con_tay",
    "đại lý": "branches",
    "cửa hàng": "branches",
    "chi nhánh": "branches",
    "NT01": "branches.code = 'NT01'",
    "NT02": "branches.code = 'NT02'",
    "CR01": "branches.code = 'CR01'",
    "tiền tệ": "VNĐ",
    "giá": "cột *_price, đơn vị VNĐ",
}


def _fetch_rows(connection: Any, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    # Đóng cursor kể cả khi truy vấn metadata phát sinh lỗi.
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return list(cursor.fetchall())
    finally:
        cursor.close()


def _format_synonyms() -> str:
    lines = ["Từ điển đồng nghĩa và quy ước:"]
    for term, meaning in SCHEMA_SYNONYMS.items():
        lines.append(f"- {term} = {meaning}")
    return "\n".join(lines)


def build_schema_context(connection: Any, database: str, allowed_views: frozenset[str] | None = None) -> str:
    # Chỉ đọc metadata của view v_ai_* và giao tiếp tục với tập quyền được truyền vào.
    views = _fetch_rows(
        connection,
        """
        SELECT TABLE_NAME, TABLE_COMMENT
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME LIKE %s
        ORDER BY TABLE_NAME
        """,
        (database, AI_VIEW_PATTERN),
    )
    if allowed_views is not None:
        views = [row for row in views if row['TABLE_NAME'] in allowed_views]
    if not views:
        raise RuntimeError("Không tìm thấy view v_ai_* trong schema hiện tại")

    view_names = [row["TABLE_NAME"] for row in views]
    placeholders = ", ".join(["%s"] * len(view_names))
    columns = _fetch_rows(
        connection,
        f"""
        SELECT TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE,
               IS_NULLABLE, COLUMN_COMMENT
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({placeholders})
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """,
        (database, *view_names),
    )

    comments = {row["TABLE_NAME"]: row.get("TABLE_COMMENT") or "" for row in views}
    # Ưu tiên mô tả tiếng Việt đã biên tập trong từ điển, sau đó mới dùng COMMENT của MySQL.
    try:
        dictionary = _fetch_rows(connection, 'SELECT view_name, column_name, description_vi FROM ai_data_dictionary', ())
    except Exception:
        dictionary = []
    descriptions = {(row['view_name'], row['column_name']): row['description_vi'] for row in dictionary}
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in view_names}
    for column in columns:
        grouped[column["TABLE_NAME"]].append(column)

    lines = [
        "Schema context dành cho text-to-SQL.",
        "Chỉ được truy vấn các view v_ai_* bên dưới; không truy cập bảng gốc.",
        "Các giá trị giá/list_price/cost_price/gross_margin là số nguyên đơn vị VNĐ.",
    ]
    for view_name in view_names:
        table_comment = comments[view_name]
        description = f" ({table_comment})" if table_comment else ""
        lines.append(f"\nVIEW {view_name}{description}:")
        for column in grouped[view_name]:
            nullable = "NULL" if column["IS_NULLABLE"] == "YES" else "NOT NULL"
            column_comment = descriptions.get((view_name, column['COLUMN_NAME']), column.get("COLUMN_COMMENT") or "")
            comment = f" - {column_comment}" if column_comment else ""
            lines.append(
                f"- {column['COLUMN_NAME']}: {column['COLUMN_TYPE']}, {nullable}{comment}"
            )

    lines.append("")
    lines.append(_format_synonyms())
    return "\n".join(lines)


def allowed_ai_views(connection: Any, database: str) -> frozenset[str]:
    # Tạo whitelist tự động từ view AI thật sự tồn tại trong schema.
    rows = _fetch_rows(
        connection,
        """
        SELECT TABLE_NAME
        FROM information_schema.VIEWS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME LIKE %s
        """,
        (database, AI_VIEW_PATTERN),
    )
    return frozenset(row["TABLE_NAME"] for row in rows)
