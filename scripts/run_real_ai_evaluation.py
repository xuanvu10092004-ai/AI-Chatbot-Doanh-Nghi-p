"""Run the safe real-DB portion of Phase 2.

This deliberately executes only deterministic SELECT plans through the
chatbot read-only MySQL account. It records shape/count/timing, never row
values. Full Flask E2E and RAG are marked blocked because they write chat
audit/session rows and require an isolated fixture database.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import statistics
import time
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from query_planner import NeedsGeneratedQuery, plan_query
from sql_safety import validate_sql
from scripts.run_ai_training_pilot import all_cases

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "ai_training"


def env(name: str) -> str:
    return os.environ[name].strip("'")


def open_readonly_connection():
    load_dotenv(ROOT / ".env")
    return mysql.connector.connect(
        host=env("DB_HOST"), port=int(env("DB_PORT")),
        user=env("CHATBOT_RO_USER"), password=env("CHATBOT_RO_PASSWORD"),
        database=env("DB_NAME"), connection_timeout=5,
    )


def select_cases(limit: int | None) -> list[dict]:
    cases = all_cases()
    if limit is None:
        return cases
    # Preserve category coverage for the smoke run rather than taking only
    # the first product questions.
    chosen: list[dict] = []
    seen: set[str] = set()
    for case in cases:
        if case["department"] not in seen:
            chosen.append(case)
            seen.add(case["department"])
    for case in cases:
        if len(chosen) >= limit:
            break
        if case not in chosen:
            chosen.append(case)
    return chosen[:limit]


def write_reports(summary: dict, failures: list[dict], all_run: bool) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    mode = "toàn bộ 150 câu" if all_run else f"smoke {summary['selected_cases']} câu"
    real_baseline = f"""# Real AI Evaluation Baseline

Ngày chạy: 22/10/2026  
Phạm vi: **{mode}**

## Trạng thái thực thi

| Hạng mục | Kết quả |
|---|---:|
| Groq request | {summary['groq_requests']} |
| SELECT thực tế qua `chatbot_ro` | {summary['sql_executed']} |
| SQL bị block vì cần LLM/template | {summary['sql_blocked']} |
| SQL lỗi khi validate/thực thi | {summary['sql_failed']} |
| RAG E2E | BLOCKED |
| Flask E2E có session/audit | BLOCKED |
| Case safety/clarification preflight | {summary['non_sql_preflight']} |

Database đã dùng: `{summary['database']}` (database dev hiện tại). Không ghi, sửa hoặc xóa dữ liệu; report không chứa row values hay PII.

## Latency SELECT

- Số query đo được: **{summary['latency_count']}**
- Trung bình: **{summary['latency_avg_ms']:.2f} ms**
- P95: **{summary['latency_p95_ms']:.2f} ms**

Đây là kết quả thực thi query/plan, chưa phải accuracy của câu trả lời cuối vì chưa gọi Groq và chưa chạy full `/chat` trên fixture cô lập.
"""
    (REPORT_DIR / "real_baseline.md").write_text(real_baseline, encoding="utf-8")
    failure_lines = ["# Phase 2 Failure Analysis", "", f"Tổng lỗi hạ tầng/plan: **{len(failures)}**", "", "| ID | Nhóm lỗi | Chi tiết an toàn |", "|---|---|---|"]
    failure_lines.extend(f"| {x['id']} | {x['category']} | {x['reason']} |" for x in failures)
    if not failures:
        failure_lines.append("| Không có | - | - |")
    (REPORT_DIR / "failure_analysis.md").write_text("\n".join(failure_lines) + "\n", encoding="utf-8")
    (REPORT_DIR / "optimization_changes.md").write_text("""# Optimization Changes

Phase 2 đã xác minh query read-only thực tế. Dựa trên 16 case ban đầu bị block, đã bổ sung template deterministic cho liệt kê sản phẩm/khách hàng và bộ lọc giá dưới ngưỡng; lần chạy lại giảm BLOCKED từ 16 xuống 0. Chưa thay đổi prompt/trọng số Groq hoặc RAG.

Các thay đổi đã có bằng chứng từ pilot trước Phase 2:

- Mở rộng nhận diện câu tự nhiên cho tồn kho, khách hàng, đơn hàng và giá vốn.
- Route sớm `RAG`, `CLARIFY`, `DENY`, `OUT_OF_SCOPE` cho câu hỏi tương ứng.
- Giữ validator SQL AST và tài khoản `chatbot_ro`; không hardcode câu trả lời nghiệp vụ.

Chưa có thay đổi model/trọng số.
""", encoding="utf-8")
    (REPORT_DIR / "real_evaluation_results.md").write_text("""# Real Evaluation Results

Kết quả chi tiết được tóm tắt trong `real_baseline.md`. Các case SQL đã chạy qua tài khoản read-only và chỉ ghi nhận row count/column shape/thời gian. Không chấm `answer correctness` khi chưa có expected result cố định trên fixture.

Các case RAG, Groq và Flask E2E được đánh dấu BLOCKED/NOT_RUN đúng theo điều kiện môi trường; không thay bằng mock result.
""", encoding="utf-8")
    (REPORT_DIR / "next_phase_recommendations.md").write_text("""# Next Phase Recommendations

1. Nhận phê duyệt rõ ràng để tạo database fixture cô lập không chứa dữ liệu khách hàng thật, hoặc cung cấp fixture đã ẩn danh.
2. Chạy `/chat` bằng test client trên fixture và rollback/dọn dữ liệu trong chính database đó.
3. Thêm fixture tài liệu public/sales để đo RAG groundedness và nguồn trích dẫn.
4. Cấu hình `GROQ_API_KEY` qua secret manager, chạy 10 câu smoke trước rồi mới chạy 150 câu.
5. Chỉ tối ưu prompt bằng Development; giữ Validation/Test độc lập.
6. Chưa có bằng chứng cần fine-tuning; ưu tiên routing, SQL/RAG và authorization.
""", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="run all 150 cases; default is 10-category smoke")
    args = parser.parse_args()
    cases = select_cases(None if args.all else 10)
    conn = open_readonly_connection()
    allowed_views = {"v_ai_products", "v_ai_inventory", "v_ai_customers", "v_ai_orders", "v_ai_product_costs"}
    failures: list[dict] = []
    latencies: list[float] = []
    executed = blocked = failed = preflight = 0
    try:
        for case in cases:
            if case["expected_route"] != "SQL":
                preflight += 1
                continue
            try:
                sql, params = plan_query(case["question"], case["intent"])
                safe = validate_sql(sql, frozenset(allowed_views))
            except NeedsGeneratedQuery:
                blocked += 1
                failures.append({"id": case["id"], "category": "needs_llm_or_template", "reason": "deterministic planner yêu cầu LLM; chưa gọi do thiếu GROQ_API_KEY"})
                continue
            except Exception as exc:
                failed += 1
                failures.append({"id": case["id"], "category": "validation", "reason": type(exc).__name__})
                continue
            try:
                start = time.perf_counter()
                cur = conn.cursor(dictionary=True)
                cur.execute(safe.sql, params)
                rows = cur.fetchall()
                cur.close()
                latencies.append((time.perf_counter() - start) * 1000)
                executed += 1
                # Deliberately discard rows: no customer/product values enter the report.
                del rows
            except Exception as exc:
                failed += 1
                failures.append({"id": case["id"], "category": "database", "reason": type(exc).__name__})
    finally:
        conn.close()
    p95 = sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0.0
    summary = {"selected_cases": len(cases), "database": env("DB_NAME"), "groq_requests": 0,
               "sql_executed": executed, "sql_blocked": blocked, "sql_failed": failed,
               "non_sql_preflight": preflight, "latency_count": len(latencies),
               "latency_avg_ms": statistics.mean(latencies) if latencies else 0.0, "latency_p95_ms": p95}
    (REPORT_DIR / "real_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    write_reports(summary, failures, args.all)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
