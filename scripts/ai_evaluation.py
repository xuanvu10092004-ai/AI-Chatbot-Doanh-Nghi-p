"""Validate and benchmark the human-question evaluation set.

This tool evaluates the deterministic safety boundary before any model tuning:
intent, route, entities, permission expectation, and (when possible) the
deterministic SQL plan.  It never executes generated SQL and never mutates the
database.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from access_control import detect_intent
from query_planner import NeedsGeneratedQuery, plan_query
from routing import route_question


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "ai_questions" / "seed.jsonl"
DEFAULT_REPORT = ROOT / "docs" / "ai_evaluation_baseline.md"
ALLOWED_ROUTES = {"SQL", "RAG", "CLARIFY", "DENY", "OUT_OF_SCOPE"}


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        case.setdefault("id", f"line-{line_no}")
        cases.append(case)
    return cases


def validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    required = {"id", "question", "department", "intent", "expected_route",
                "expected_action", "required_permission", "expected_scope",
                "expected_entities", "expected_behavior", "difficulty", "split"}
    ids: set[str] = set()
    for index, case in enumerate(cases, 1):
        missing = required - case.keys()
        if missing:
            errors.append(f"{case.get('id', index)}: thiếu trường {sorted(missing)}")
        case_id = str(case.get("id", ""))
        if case_id in ids:
            errors.append(f"{case_id}: id trùng")
        ids.add(case_id)
        if case.get("expected_route") not in ALLOWED_ROUTES:
            errors.append(f"{case_id}: expected_route không hợp lệ")
        if not isinstance(case.get("expected_entities", {}), dict):
            errors.append(f"{case_id}: expected_entities phải là object")
        if case.get("split", case.get("dataset_split")) not in {"development", "validation", "test", "evaluation", "safety"}:
            errors.append(f"{case_id}: split phải là development/evaluation/safety")
    return errors


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    question = case["question"]
    actual_intent = detect_intent(question)
    expected_route = case["expected_route"]
    actual_route = "SQL" if actual_intent.startswith("ask_") else route_question(question).get("type", "OUT_OF_SCOPE")
    expected_intent = case["intent"]
    intent_ok = actual_intent == expected_intent
    route_ok = actual_route == expected_route
    plan_ok = None
    plan_error = ""
    if actual_route == "SQL":
        try:
            sql, _ = plan_query(question, actual_intent)
            plan_ok = bool(re.match(r"^SELECT\b", sql, re.I)) and "FROM v_ai_" in sql
        except NeedsGeneratedQuery:
            plan_ok = expected_behavior_allows_llm(case)
            plan_error = "needs_generated_query"
        except Exception as exc:  # keep benchmark reporting useful
            plan_ok = False
            plan_error = type(exc).__name__
    return {
        "id": case["id"],
        "intent_ok": intent_ok,
        "route_ok": route_ok,
        "plan_ok": plan_ok,
        "actual_intent": actual_intent,
        "actual_route": actual_route,
        "failure_class": failure_class(case, intent_ok, route_ok, plan_ok),
        "plan_error": plan_error,
    }


def expected_behavior_allows_llm(case: dict[str, Any]) -> bool:
    return case.get("expected_behavior") in {"query_and_answer", "retrieve_and_answer", "clarify"}


def failure_class(case: dict[str, Any], intent_ok: bool, route_ok: bool, plan_ok: bool | None) -> str:
    if not intent_ok:
        return "intent"
    if not route_ok:
        return "route"
    if plan_ok is False:
        return "sql_plan"
    return "pass"


def markdown_report(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> str:
    counts = Counter(r["failure_class"] for r in results)
    total = len(results)
    def pct(key: str) -> str:
        return f"{counts[key] / total:.1%}" if total else "0.0%"
    lines = [
        "# AI Evaluation Baseline",
        "",
        "> Báo cáo được tạo bởi `python scripts/ai_evaluation.py benchmark`. Đây là baseline của route/quy tắc hiện tại, không phải kết quả fine-tuning.",
        "",
        f"- Tổng số câu: **{total}**",
        f"- Intent đúng: **{sum(r['intent_ok'] for r in results)}/{total}**",
        f"- Route đúng: **{sum(r['route_ok'] for r in results)}/{total}**",
        f"- SQL plan hợp lệ hoặc được đánh dấu cần LLM: **{sum(r['plan_ok'] is not False for r in results)}/{total}**",
        "",
        "| Nhóm lỗi | Số lượng | Tỷ lệ |",
        "|---|---:|---:|",
    ]
    for key in ("pass", "intent", "route", "sql_plan"):
        lines.append(f"| {key} | {counts[key]} | {pct(key)} |")
    lines += ["", "## Phân bố theo split", "", "| Split | Số câu |", "|---|---:|"]
    split_counts = Counter(c.get("split") for c in cases)
    lines.extend(f"| {split} | {count} |" for split, count in sorted(split_counts.items()))
    failures = [r for r in results if r["failure_class"] != "pass"]
    lines += ["", "## Câu cần xử lý", "", "| ID | Nhóm lỗi | Intent thực tế | Route thực tế |", "|---|---|---|---|"]
    for result in failures[:100]:
        lines.append(f"| {result['id']} | {result['failure_class']} | {result['actual_intent']} | {result['actual_route']} |")
    if not failures:
        lines.append("| Không có | - | - | - |")
    lines += ["", "## Cách diễn giải", "", "- `intent`: mở rộng bộ nhận diện hoặc sửa câu hỏi/nhãn.", "- `route`: kiểm tra phân loại SQL/RAG/clarify trước khi gọi model.", "- `sql_plan`: bổ sung query template hoặc đưa vào tập kiểm thử LLM.", "- Kết quả này không được dùng để khẳng định dữ liệu nghiệp vụ; kết quả SQL phải được kiểm tra trên snapshot/fixture tái lập.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "benchmark"))
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    cases = load_cases(args.dataset)
    errors = validate_cases(cases)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Dataset hợp lệ: {len(cases)} câu ({args.dataset})")
    if args.command == "benchmark":
        results = [evaluate_case(case) for case in cases]
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown_report(cases, results), encoding="utf-8")
        counts = Counter(r["failure_class"] for r in results)
        print(f"Baseline: {counts['pass']}/{len(results)} pass; báo cáo: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
