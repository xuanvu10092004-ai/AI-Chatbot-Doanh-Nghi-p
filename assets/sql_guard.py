"""
sql_guard.py - Validator cho SQL do LLM sinh (text-to-SQL), dùng cho MySQL.

Cài: pip install sqlglot
Dùng:
    from sql_guard import validate_sql, SqlRejected
    safe_sql = validate_sql(llm_sql, allowed_views={"v_ai_products", "v_ai_inventory"})

Nguyên tắc: whitelist, không blacklist. Chỉ chấp nhận đúng 1 câu SELECT, chỉ đọc
các view trong allowed_views (tập này do backend tính theo quyền của user, KHÔNG
lấy từ LLM), không có hàm nguy hiểm, và luôn có LIMIT <= MAX_ROWS.
"""
import re
import sqlglot
from sqlglot import exp

MAX_ROWS = 100
FORBIDDEN_FUNCS = {"SLEEP", "BENCHMARK", "LOAD_FILE", "GET_LOCK", "RELEASE_LOCK", "UUID_SHORT"}


class SqlRejected(Exception):
    """SQL bị từ chối. Thông điệp dùng cho log/audit, KHÔNG gửi nguyên văn cho người dùng."""


def validate_sql(sql: str, allowed_views: set[str]) -> str:
    if not sql or not sql.strip():
        raise SqlRejected("empty_sql")

    # Chặn ký tự/chuỗi dễ dùng để lách ở tầng văn bản (kiểm tra thêm, không thay cho AST)
    if re.search(r"--|/\*|\*/|#|\binto\s+(outfile|dumpfile)\b", sql, re.IGNORECASE):
        raise SqlRejected("comment_or_outfile_not_allowed")

    try:
        statements = sqlglot.parse(sql, read="mysql")
    except sqlglot.errors.ParseError as e:
        raise SqlRejected(f"parse_error: {e}") from e

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise SqlRejected("exactly_one_statement_required")

    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        raise SqlRejected("only_select_allowed")

    # Không cho các nút ghi/DDL/lệnh khác lọt vào bên trong (CTE, subquery...)
    for node in tree.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
                             exp.Alter, exp.Command, exp.Into, exp.Set)):
            raise SqlRejected(f"forbidden_node: {type(node).__name__}")

    # Whitelist bảng/view (bỏ qua tên CTE do chính câu lệnh định nghĩa)
    cte_names = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    allowed = {v.lower() for v in allowed_views}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if table.db and table.db.lower() not in ("honda_chatbot",):
            raise SqlRejected(f"schema_not_allowed: {table.db}")
        if name in cte_names:
            continue
        if name not in allowed:
            raise SqlRejected(f"table_not_allowed: {name}")

    # Hàm nguy hiểm
    for func in tree.find_all(exp.Func):
        fname = (func.sql_name() or "").upper()
        if fname in FORBIDDEN_FUNCS:
            raise SqlRejected(f"function_not_allowed: {fname}")
    for anon in tree.find_all(exp.Anonymous):
        if str(anon.this).upper() in FORBIDDEN_FUNCS:
            raise SqlRejected(f"function_not_allowed: {anon.this}")

    # Biến phiên (@x, @@x) bị cấm để LLM không đổi được @ai_branch
    for node in tree.walk():
        if isinstance(node, (exp.SessionParameter, exp.Parameter)):
            raise SqlRejected("session_variable_not_allowed")

    # Ép LIMIT <= MAX_ROWS (chỉ áp cho câu SELECT ngoài cùng)
    limit = tree.args.get("limit")
    if limit is None:
        tree = tree.limit(MAX_ROWS)
    else:
        try:
            n = int(limit.expression.name)
        except (ValueError, AttributeError):
            raise SqlRejected("limit_must_be_integer")
        if n > MAX_ROWS:
            tree = tree.limit(MAX_ROWS)

    return tree.sql(dialect="mysql")
