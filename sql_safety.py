# Bổ sung timeout và giới hạn dòng cho SQL đã được validator whitelist chấp nhận.
from __future__ import annotations

import re  # Tạm bảo toàn marker bind và gắn hint timeout vào SELECT.
from dataclasses import dataclass  # Gom SQL đã kiểm tra cùng limit/timeout hiệu lực.
from sql_guard import validate_sql as guard  # Dùng chung bộ kiểm tra AST và whitelist view.

@dataclass(frozen=True)
# Kết quả kiểm tra SQL kèm giới hạn dòng và timeout đã được chốt.
class ValidatedQuery:
    sql: str
    limit: int
    timeout_ms: int

# Chuẩn hóa marker tham số, gọi validator và gắn timeout không vượt quá 5 giây.
def validate_sql(sql: str, allowed_views: frozenset[str], timeout_ms: int = 5000) -> ValidatedQuery:
    # Chuyển %s thành marker tạm để SQL parser không nhầm bind với cú pháp truy vấn.
    markers = []
    def bind(match):
        name = f"__honda_bind_{len(markers)}"
        markers.append(name)
        return ":" + name
    candidate = re.sub(r"%s", bind, sql)
    if ";" in candidate.rstrip().rstrip(";"):
        raise ValueError("exactly_one_statement_required")
    safe = guard(candidate, set(allowed_views))
    safe = re.sub(r':__honda_bind_\d+\b', '%s', safe)
    limit = re.search(r"LIMIT (\d+)", safe)
    timeout_ms = max(1, min(int(timeout_ms), 5000))
    safe = re.sub(r"^SELECT\b", f"SELECT /*+ MAX_EXECUTION_TIME({timeout_ms}) */", safe, count=1)
    return ValidatedQuery(safe, int(limit.group(1)) if limit else 100, timeout_ms)
