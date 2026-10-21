# Validator SQL đời cũ; kiểm tra SELECT, view được phép và giới hạn dòng.
import re  # Chặn comment và lệnh ghi file ngay trên văn bản SQL.
import sqlglot  # Phân tích câu lệnh và các node SQL theo MySQL.
from sqlglot import exp  # Kiểm tra loại statement và cú pháp trong AST.

MAX_ROWS = 100
FORBIDDEN_FUNCS = {"SLEEP", "BENCHMARK", "LOAD_FILE", "GET_LOCK", "RELEASE_LOCK", "UUID_SHORT"}


# Lỗi validator được caller dùng để từ chối truy vấn không an toàn.
class SqlRejected(Exception):
    """SQL bị từ chối. Thông điệp dùng cho log/audit, KHÔNG gửi nguyên văn cho người dùng."""


# Chỉ nhận một SELECT/UNION, whitelist bảng/view và giới hạn LIMIT ngoài cùng.
def validate_sql(sql: str, allowed_views: set[str]) -> str:
    if not sql or not sql.strip():
        raise SqlRejected("empty_sql")

    # Chặn comment và ghi file trước khi parse; AST tiếp tục kiểm tra cấu trúc lệnh.
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

    # Cho phép bảng CTE do câu này định nghĩa, còn mọi bảng thật phải thuộc whitelist.
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

    # Từ chối các hàm có thể gây chờ, khóa hoặc đọc file.
    for func in tree.find_all(exp.Func):
        fname = (func.sql_name() or "").upper()
        if fname in FORBIDDEN_FUNCS:
            raise SqlRejected(f"function_not_allowed: {fname}")
    for anon in tree.find_all(exp.Anonymous):
        if str(anon.this).upper() in FORBIDDEN_FUNCS:
            raise SqlRejected(f"function_not_allowed: {anon.this}")

    # Cấm biến phiên để truy vấn không thể thay scope do backend thiết lập.
    for node in tree.walk():
        if isinstance(node, (exp.SessionParameter, exp.Parameter)):
            raise SqlRejected("session_variable_not_allowed")

    # Giới hạn số dòng của truy vấn ngoài cùng để response không quá lớn.
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
