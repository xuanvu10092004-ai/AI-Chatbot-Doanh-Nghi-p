from __future__ import annotations

import re
from dataclasses import dataclass
from sql_guard import validate_sql as guard

@dataclass(frozen=True)
class ValidatedQuery:
    sql: str
    limit: int
    timeout_ms: int

def validate_sql(sql: str, allowed_views: frozenset[str], timeout_ms: int = 5000) -> ValidatedQuery:
    # Only application templates use connector bind markers. Never interpolate values.
    markers = []
    def bind(match):
        name = f"__honda_bind_{len(markers)}"
        markers.append(name)
        return ":" + name
    candidate = re.sub(r"%s", bind, sql)
    if ";" in candidate.rstrip().rstrip(";"):
        raise ValueError("exactly_one_statement_required")
    safe = guard(candidate, set(allowed_views))
    for name in markers:
        safe = safe.replace(":" + name, "%s")
    limit = re.search(r"LIMIT (\d+)", safe)
    timeout_ms = max(1, min(int(timeout_ms), 5000))
    safe = re.sub(r"^SELECT\b", f"SELECT /*+ MAX_EXECUTION_TIME({timeout_ms}) */", safe, count=1)
    return ValidatedQuery(safe, int(limit.group(1)) if limit else 100, timeout_ms)
