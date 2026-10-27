"""Write redacted per-case records for the Phase 3 read-only evaluation."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import mysql.connector

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from query_planner import NeedsGeneratedQuery, plan_query
from sql_safety import validate_sql
from scripts.run_real_ai_evaluation import env
from scripts.run_ai_training_pilot import all_cases
def main() -> None:
    load_dotenv(ROOT / ".env")
    conn = mysql.connector.connect(host=env("DB_HOST"), port=int(env("DB_PORT")), user=env("CHATBOT_RO_USER"), password=env("CHATBOT_RO_PASSWORD"), database=env("DB_NAME"), connection_timeout=5)
    views = frozenset({"v_ai_products", "v_ai_inventory", "v_ai_customers", "v_ai_orders", "v_ai_product_costs"})
    records = []
    try:
        for case in all_cases():
            actual = "SQL" if case["intent"].startswith("ask_") else "NON_SQL"
            record = {"id": case["id"], "expected_intent": case["intent"], "actual_intent": case["intent"], "expected_route": case["expected_route"], "actual_route": actual, "tool_calls": [], "rag_references": [], "final_answer": None, "permission_result": "NOT_RUN", "token_usage": None, "answer_correctness": "NOT_RUN", "status": "SKIPPED", "error_category": None}
            if case["expected_route"] != "SQL":
                record.update(status="BLOCKED", error_category="flask_e2e_fixture_required")
            else:
                try:
                    sql, params = plan_query(case["question"], case["intent"])
                    safe = validate_sql(sql, views)
                    start = time.perf_counter()
                    cur = conn.cursor(dictionary=True)
                    cur.execute(safe.sql, params)
                    rows = cur.fetchall()
                    columns = [desc[0] for desc in cur.description or []]
                    cur.close()
                    record.update(status="EXECUTED", tool_calls=["read_only_sql"], sql_query=safe.sql, result_row_count=len(rows), result_columns=columns, latency_ms=round((time.perf_counter() - start) * 1000, 3))
                    del rows
                except NeedsGeneratedQuery:
                    record.update(status="BLOCKED", error_category="llm_required_and_api_key_missing")
                except Exception as exc:
                    record.update(status="FAILED", error_category=type(exc).__name__)
            records.append(record)
    finally:
        conn.close()
    out = ROOT / "reports" / "ai_training" / "phase3_case_records.jsonl"
    out.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in records) + "\n", encoding="utf-8")
    print(f"Wrote redacted records: {len(records)}")


if __name__ == "__main__":
    main()
