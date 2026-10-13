from __future__ import annotations

import re
from dataclasses import dataclass
from typing import FrozenSet


FORBIDDEN = re.compile(
    r"\b(?:DROP|ALTER|TRUNCATE|INSERT|UPDATE|DELETE|REPLACE|CREATE|GRANT|REVOKE|CALL|SET|SHOW|DESCRIBE|EXPLAIN|INTO\s+OUTFILE|SLEEP)\b",
    re.IGNORECASE,
)
COMMENTS = re.compile(r"(--|#|/\*)")
RELATIONS = re.compile(
    r"\b(?:FROM|JOIN)\s+(`?[A-Za-z_][A-Za-z0-9_$]*`?(?:\s*\.\s*`?[A-Za-z_][A-Za-z0-9_$]*`?)?)",
    re.IGNORECASE,
)
LIMIT = re.compile(r"\bLIMIT\s+(?:(\d+)\s*,\s*)?(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class ValidatedQuery:
    sql: str
    limit: int
    timeout_ms: int


def _strip_identifier(value: str) -> str:
    return value.replace("`", "").replace(" ", "").lower()


def _check_relations(sql: str, allowed_views: FrozenSet[str]) -> None:
    relations = RELATIONS.findall(sql)
    if not relations:
        raise ValueError("SQL phải truy cập ít nhất một view v_ai_*")
    whitelist = {view.lower() for view in allowed_views}
    for relation in relations:
        normalized = _strip_identifier(relation)
        if "." in normalized:
            normalized = normalized.rsplit(".", 1)[-1]
        if normalized not in whitelist:
            raise ValueError(f"View không được phép: {relation}")


def _bounded_limit(sql: str) -> tuple[str, int]:
    matches = list(LIMIT.finditer(sql))
    if not matches:
        return f"{sql} LIMIT 100", 100
    if len(matches) != 1:
        raise ValueError("SQL chỉ được có một LIMIT")
    match = matches[0]
    offset = int(match.group(1) or 0)
    requested = int(match.group(2))
    bounded = min(requested, 100)
    replacement = f"LIMIT {offset}, {bounded}" if match.group(1) else f"LIMIT {bounded}"
    return sql[:match.start()] + replacement + sql[match.end():], bounded


def validate_sql(sql: str, allowed_views: FrozenSet[str], timeout_ms: int = 5000) -> ValidatedQuery:
    candidate = sql.strip()
    if not candidate:
        raise ValueError("SQL rỗng")
    if candidate.endswith(";"):
        candidate = candidate[:-1].rstrip()
    if ";" in candidate:
        raise ValueError("Không cho phép nhiều câu lệnh SQL")
    if COMMENTS.search(candidate):
        raise ValueError("Không cho phép comment trong SQL")
    if not re.match(r"^SELECT\b", candidate, re.IGNORECASE):
        raise ValueError("Chỉ cho phép câu lệnh SELECT")
    if FORBIDDEN.search(candidate):
        raise ValueError("SQL chứa từ khóa hoặc thao tác bị cấm")
    _check_relations(candidate, allowed_views)
    bounded_sql, limit = _bounded_limit(candidate)
    safe_sql = re.sub(
        r"^SELECT\b",
        f"SELECT /*+ MAX_EXECUTION_TIME({int(timeout_ms)}) */",
        bounded_sql,
        count=1,
        flags=re.IGNORECASE,
    )
    return ValidatedQuery(sql=safe_sql, limit=limit, timeout_ms=timeout_ms)
