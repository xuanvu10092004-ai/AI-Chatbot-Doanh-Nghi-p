# Kiểm tra AST để chỉ cho phép một truy vấn SELECT tới view nằm trong whitelist.
import re  # Chặn comment, outfile và cú pháp nguy hiểm trước khi parse AST.
import sqlglot  # Parse câu SQL theo cú pháp MySQL.
from sqlglot import exp  # So loại node câu lệnh, bảng, hàm và LIMIT trong AST.
from sqlglot.optimizer.scope import traverse_scope  # Kiểm tra bảng trong cả CTE và subquery.

MAX_ROWS = 100
FORBIDDEN_FUNCS = {"SLEEP", "BENCHMARK", "LOAD_FILE", "GET_LOCK", "RELEASE_LOCK", "UUID_SHORT"}


# SQL bị từ chối; mã lỗi nội bộ không được phản hồi nguyên văn cho người dùng.
class SqlRejected(ValueError):
    """SQL bị từ chối. Thông điệp dùng cho log/audit, KHÔNG gửi nguyên văn cho người dùng."""


# Parse, áp whitelist view, cấm hàm nguy hiểm và ép LIMIT tối đa MAX_ROWS.
def validate_sql(sql: str, allowed_views: set[str]) -> str:
    if not sql or not sql.strip():
        raise SqlRejected("empty_sql")

    # Chặn comment và ghi file ngay trên chuỗi, trước khi phân tích AST.
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

    # Chặn cả node ghi/DDL ẩn bên trong CTE hoặc truy vấn con.
    for node in tree.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
                             exp.Alter, exp.Command, exp.Into, exp.Set)):
            raise SqlRejected(f"forbidden_node: {type(node).__name__}")

    # Duyệt từng scope để CTE không che được bảng thật nằm trong truy vấn con.
    allowed = {v.lower() for v in allowed_views}
    real_tables = []
    for scope in traverse_scope(tree):
        for _, source in scope.selected_sources.values():
            if isinstance(source, exp.Table):
                real_tables.append(source)
                if source.db or source.catalog or source.name.lower() not in allowed:
                    raise SqlRejected("table_not_allowed")
    if not real_tables:
        raise SqlRejected("view_required")
    if tree.find(exp.Lock) or tree.find(exp.Hint):
        raise SqlRejected("lock_or_hint_not_allowed")

    # Chỉ cho phép hàm nằm trong whitelist hẹp; chặn sleep và hàm truy cập file/khóa.
    for func in tree.find_all(exp.Func):
        fname = (func.sql_name() or "").upper()
        if fname in FORBIDDEN_FUNCS:
            raise SqlRejected(f"function_not_allowed: {fname}")
    for anon in tree.find_all(exp.Anonymous):
        if str(anon.this).upper() not in {"ROUND", "DATE_FORMAT"}:
            raise SqlRejected(f"function_not_allowed: {anon.this}")

    # Cấm biến phiên để truy vấn không thể thay scope do backend thiết lập.
    for node in tree.walk():
        if isinstance(node, (exp.SessionParameter, exp.Parameter)):
            raise SqlRejected("session_variable_not_allowed")

    # Giới hạn số dòng trả về ở SELECT ngoài cùng, không sửa LIMIT trong truy vấn con.
    limit = tree.args.get("limit")
    if limit is None:
        tree = tree.limit(MAX_ROWS)
    else:
        try:
            n = int(limit.expression.name)
        except (ValueError, AttributeError):
            raise SqlRejected("limit_must_be_integer")
        if n < 0:
            raise SqlRejected("limit_must_be_nonnegative")
        if n > MAX_ROWS:
            tree = tree.limit(MAX_ROWS)

    return tree.sql(dialect="mysql")
