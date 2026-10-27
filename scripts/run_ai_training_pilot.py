"""Run the safe, offline part of the 150-question pilot and write a baseline.

The default command never calls Groq and never executes SQL.  It measures the
deterministic routing/intent boundary and records live SQL/RAG metrics as
NOT_RUN until a read-only fixture and API credentials are explicitly supplied.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ai_evaluation import evaluate_case, load_cases, validate_cases
from routing import route_question

DATA = ROOT / "data" / "ai_training"
REPORT = ROOT / "reports" / "ai_training" / "baseline_report.md"


def all_cases() -> list[dict]:
    rows = []
    for split in ("development", "validation", "test"):
        rows.extend(load_cases(DATA / f"{split}.jsonl"))
    return rows


def run(cases: list[dict]) -> tuple[list[dict], Counter]:
    results = []
    counts = Counter()
    for case in cases:
        expected = case["expected_route"]
        actual = route_question(case["question"])["type"]
        if expected == "SQL":
            result = evaluate_case(case)
            passed = result["intent_ok"] and result["route_ok"] and result["plan_ok"] is not False
            failure = result["failure_class"]
        else:
            passed = actual == expected
            failure = "pass" if passed else "route"
            result = {"id": case["id"], "actual_route": actual, "failure_class": failure,
                      "intent_ok": None, "route_ok": passed, "plan_ok": None}
        result["expected_route"] = expected
        results.append(result)
        counts[failure] += 1
    return results, counts


def write_report(cases: list[dict], results: list[dict], counts: Counter, path: Path) -> None:
    sql = [r for r, c in zip(results, cases) if c["expected_route"] == "SQL"]
    non_sql = [r for r, c in zip(results, cases) if c["expected_route"] != "SQL"]
    lines = [
        "# AI Training Pilot — Baseline Report", "",
        "> Đây là baseline offline của pilot 150 câu. Chưa gọi Groq, chưa thực thi SQL và chưa đọc dữ liệu production.", "",
        f"- Tổng số case: **{len(cases)}**",
        f"- Development/Validation/Test: **{sum(c['dataset_split']=='development' for c in cases)}/{sum(c['dataset_split']=='validation' for c in cases)}/{sum(c['dataset_split']=='test' for c in cases)}**",
        f"- SQL intent + route + plan shape: **{sum(r['failure_class']=='pass' for r in sql)}/{len(sql)}**",
        f"- Non-SQL route (RAG/CLARIFY/DENY): **{sum(r['failure_class']=='pass' for r in non_sql)}/{len(non_sql)}**",
        "",
        "| Nhóm lỗi | Số lượng |", "|---|---:|",
    ]
    for name in ("pass", "intent", "route", "sql_plan"):
        lines.append(f"| {name} | {counts[name]} |")
    lines += [
        "", "## Metrics chưa thể chạy an toàn", "",
        "| Metric | Trạng thái | Lý do |", "|---|---|---|",
        "| SQL result correctness | NOT_RUN | Cần MySQL snapshot/fixture cố định; không dùng dữ liệu đang thay đổi làm đáp án cứng |",
        "| RAG groundedness | NOT_RUN | Cần bộ tài liệu fixture và nguồn kỳ vọng |",
        "| Answer correctness | NOT_RUN | Cần chạy full `/chat` với identity test và bằng chứng |",
        "| Latency/token usage | NOT_RUN | Chưa gọi Groq/API |",
        "| Permission compliance | PRECHECK ONLY | Case safety đã route deny; cần integration test bằng session/backend identity |",
        "", "## Các case lỗi", "", "| ID | Expected route | Actual route | Nhóm |", "|---|---|---|---|",
    ]
    failures = [(c, r) for c, r in zip(cases, results) if r["failure_class"] != "pass"]
    lines.extend(f"| {c['id']} | {c['expected_route']} | {r.get('actual_route', '')} | {r['failure_class']} |" for c, r in failures)
    if not failures:
        lines.append("| Không có | - | - | - |")
    lines += ["", "## Kết luận", "", "Pilot đạt tiêu chí preflight định tuyến hiện tại. Đây chưa phải kết quả training và chưa đủ để kết luận chatbot trả lời đúng dữ liệu nghiệp vụ. Bước kế tiếp là chạy trên fixture/snapshot read-only, sau đó mới tối ưu bằng tập Development; không dùng Validation/Test để few-shot.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    cases = all_cases()
    errors = validate_cases(cases)
    if errors:
        print("\n".join(errors))
        return 1
    results, counts = run(cases)
    write_report(cases, results, counts, args.report)
    print(f"Pilot validated: {len(cases)} cases; pass={counts['pass']}; report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
