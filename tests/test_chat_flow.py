import sqlite3
from pathlib import Path

import ai_service
import app
import database_service
import rag_service
import routing
import sql_service


ROOT = Path(__file__).resolve().parents[1]


def test_database_services_use_project_database_from_other_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert Path(database_service.DB_NAME) == ROOT / "database.db"
    assert Path(sql_service.DB_NAME) == ROOT / "database.db"
    assert Path(rag_service.DB_NAME) == ROOT / "database.db"
    assert database_service.get_dashboard_stats()["customers"] == 60
    assert "Tổng số khách hàng trong hệ thống: 60" in sql_service.answer_sql_question(
        "có bao nhiêu khách hàng?"
    )
    assert rag_service.search_documents("Chính sách bảo hành là gì?") == (
        "Không tìm thấy tài liệu liên quan trong hệ thống."
    )


def test_dashboard_and_inventory_endpoints_return_sqlite_data():
    client = app.app.test_client()

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.get_json()["customers"] == 60
    assert dashboard.get_json()["inventory"] == 50

    low_stock = client.get("/api/low-stock")
    assert low_stock.status_code == 200
    assert isinstance(low_stock.get_json(), list)
    assert all(item["quantity"] < 10 for item in low_stock.get_json())

    potential = client.get("/api/potential-customers")
    assert potential.status_code == 200
    assert all(item["status"] in {"potential", "vip", "new"} for item in potential.get_json())


def test_chat_rejects_malformed_or_empty_input():
    client = app.app.test_client()

    malformed = client.post(
        "/chat",
        data="{",
        content_type="application/json",
    )
    assert malformed.status_code == 400
    assert malformed.get_json()["error"] == "invalid_json"

    wrong_type = client.post("/chat", json={"question": 123})
    assert wrong_type.status_code == 400
    assert wrong_type.get_json()["error"] == "invalid_question"

    empty = client.post("/chat", json={"question": "   "})
    assert empty.status_code == 400
    assert empty.get_json()["error"] == "empty_question"


def test_chat_reports_missing_groq_configuration_without_calling_provider(monkeypatch):
    monkeypatch.setattr(ai_service, "API_KEY", None)
    monkeypatch.setattr(app, "generate_answer", ai_service.generate_answer)

    response = app.app.test_client().post(
        "/chat",
        json={"question": "có bao nhiêu khách hàng?"},
    )

    assert response.status_code == 503
    assert response.get_json()["error"] == "llm_not_configured"
    assert "GROQ_API_KEY" in response.get_json()["answer"]


def test_requested_sql_questions_are_grounded_in_database():
    connection = sqlite3.connect(ROOT / "database.db")
    try:
        customer_count = connection.execute(
            "SELECT COUNT(*) FROM customers"
        ).fetchone()[0]
        assert f"{customer_count} khách hàng" in sql_service.answer_sql_question(
            "có bao nhiêu khách hàng?"
        )

        low_stock_names = [
            row[0]
            for row in connection.execute(
                "SELECT product_name FROM inventory WHERE quantity < 10"
            )
        ]
        low_stock_context = sql_service.answer_sql_question(
            "kho nào sắp hết hàng?"
        )
        assert low_stock_names
        assert all(name in low_stock_context for name in low_stock_names)

        top_customers = [
            row[0]
            for row in connection.execute("""
                SELECT c.name
                FROM customers c
                JOIN quotes q ON q.customer_id = c.id
                WHERE q.status = 'approved'
                GROUP BY c.id
                ORDER BY SUM(q.total_amount) DESC
                LIMIT 10
            """)
        ]
        top_context = sql_service.answer_sql_question(
            "top 10 khách hàng có doanh thu cao nhất"
        )
        assert top_customers
        assert all(name in top_context for name in top_customers)

        product_count = connection.execute(
            "SELECT COUNT(*) FROM inventory"
        ).fetchone()[0]
        assert f"{product_count} sản phẩm" in sql_service.answer_sql_question(
            "có bao nhiêu sản phẩm trong kho?"
        )

        open_opportunities = [
            row[0]
            for row in connection.execute("""
                SELECT title
                FROM opportunities
                WHERE stage NOT IN ('won', 'lost')
                ORDER BY value DESC
                LIMIT 20
            """)
        ]
        opportunity_context = sql_service.answer_sql_question(
            "có cơ hội bán hàng nào đang chờ xử lý?"
        )
        assert open_opportunities
        assert f"({len(open_opportunities)} cơ hội)" in opportunity_context
        assert all(title in opportunity_context for title in open_opportunities)

        quote_codes = [
            row[0]
            for row in connection.execute("""
                SELECT quote_code
                FROM quotes
                ORDER BY total_amount DESC
                LIMIT 20
            """)
        ]
        quote_context = sql_service.answer_sql_question(
            "cho tôi xem các báo giá hiện có"
        )
        assert quote_codes
        assert all(code in quote_context for code in quote_codes)
    finally:
        connection.close()


def test_quote_waiting_query_does_not_match_the_word_for():
    pending_context = sql_service.answer_sql_question(
        "báo giá nào đang chờ duyệt?"
    )
    list_context = sql_service.answer_sql_question(
        "cho tôi xem các báo giá hiện có"
    )

    assert "Không tìm thấy báo giá" in pending_context
    assert "Danh sách báo giá" in list_context


def test_requested_rag_questions_retrieve_evidence_and_report_no_evidence():
    greeting_routes = [
        routing.route_question("chào"),
        routing.route_question("xin chào, bạn có thể giúp gì cho tôi?"),
    ]
    assert all(result["type"] == "RAG" for result in greeting_routes)

    unsupported_policy_context = rag_service.search_documents(
        "Chính sách bảo hành là gì?"
    )
    assert unsupported_policy_context == (
        "Không tìm thấy tài liệu liên quan trong hệ thống."
    )

    relevant_context = rag_service.search_documents(
        "Quy trình RAG hoạt động ra sao?"
    )
    assert "Luồng xử lý RAG" in relevant_context

    missing_context = rag_service.search_documents(
        "qzxv-no-evidence-987654"
    )
    assert missing_context == "Không tìm thấy tài liệu liên quan trong hệ thống."


def test_all_requested_prompts_are_routed_to_the_expected_retriever():
    prompts = [
        ("chào", "RAG"),
        ("xin chào, bạn có thể giúp gì cho tôi?", "RAG"),
        ("có bao nhiêu khách hàng?", "SQL"),
        ("kho nào sắp hết hàng?", "SQL"),
        ("top 10 khách hàng có doanh thu cao nhất", "SQL"),
        ("có bao nhiêu sản phẩm trong kho?", "SQL"),
        ("có cơ hội bán hàng nào đang chờ xử lý?", "SQL"),
        ("cho tôi xem các báo giá hiện có", "SQL"),
        ("Quy trình RAG hoạt động ra sao?", "RAG"),
        ("qzxv-no-evidence-987654", "RAG"),
    ]

    for question, expected_type in prompts:
        result = routing.route_question(question)
        assert result["type"] == expected_type
        if expected_type == "SQL":
            context = sql_service.answer_sql_question(question)
            assert context
            assert "chưa có truy vấn SQL phù hợp" not in context
        elif question == "Quy trình RAG hoạt động ra sao?":
            assert "Luồng xử lý RAG" in rag_service.search_documents(question)
        elif question.startswith("qzxv-"):
            assert rag_service.search_documents(question) == (
                "Không tìm thấy tài liệu liên quan trong hệ thống."
            )
