from __future__ import annotations

import pytest

from access_control import authorize_intent, create_session
from db import get_connection


@pytest.fixture()
def mysql_connection():
    try:
        connection = get_connection("app")
        connection.cursor().execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"MySQL unavailable: {exc}")
    yield connection
    connection.close()


def fetch_one(connection, query: str, params: tuple = ()):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    finally:
        cursor.close()


def test_expected_dataset_counts(mysql_connection):
    checks = {
        "products": ("SELECT COUNT(DISTINCT product_id) AS n FROM v_ai_products", 10),
        "product_variants": ("SELECT COUNT(*) AS n FROM v_ai_products", 28),
        "inventory": ("SELECT COUNT(*) AS n FROM v_ai_inventory", 84),
        "customers": ("SELECT COUNT(*) AS n FROM v_ai_customers", 80),
        "customer_profiles": ("SELECT COUNT(*) AS n FROM customer_profiles", 80),
        "orders": ("SELECT COUNT(DISTINCT order_id) AS n FROM v_ai_orders", 30),
    }
    for query, expected in checks.values():
        assert fetch_one(mysql_connection, query)["n"] == expected


@pytest.mark.parametrize(
    ("question", "query"),
    [
        ("SH 160i giá bao nhiêu?", "SELECT COUNT(*) AS n FROM v_ai_products WHERE model_name = %s"),
        ("Giá niêm yết SH 160i", "SELECT MIN(list_price) AS n FROM v_ai_products WHERE model_name = %s"),
        ("Có bao nhiêu phiên bản xe?", "SELECT COUNT(*) AS n FROM v_ai_products"),
        ("Có bao nhiêu sản phẩm trong kho?", "SELECT COUNT(*) AS n FROM v_ai_inventory"),
        ("Tồn kho tại chi nhánh NT01", "SELECT COUNT(*) AS n FROM v_ai_inventory WHERE branch_code = %s"),
        ("Có bao nhiêu khách hàng?", "SELECT COUNT(*) AS n FROM v_ai_customers"),
        ("Có bao nhiêu khách hàng đã mua?", "SELECT COUNT(*) AS n FROM v_ai_customers WHERE customer_status = %s"),
        ("Có bao nhiêu đơn hàng?", "SELECT COUNT(DISTINCT order_id) AS n FROM v_ai_orders"),
        ("Đơn hàng tại NT02", "SELECT COUNT(DISTINCT order_id) AS n FROM v_ai_orders WHERE branch_code = %s"),
        ("Các mẫu xe tay ga", "SELECT COUNT(*) AS n FROM v_ai_products WHERE segment = %s"),
    ],
)
def test_standard_question_has_sql_evidence(mysql_connection, question, query):
    params = ()
    if "model_name =" in query:
        params = ("SH 160i",)
    elif "branch_code =" in query:
        params = ("NT01" if "NT01" in question else "NT02",)
    elif "customer_status" in query:
        params = ("Đã mua",)
    elif "segment =" in query:
        params = ("tay_ga",)
    result = fetch_one(mysql_connection, query, params)
    assert result is not None
    assert result["n"] is not None


def test_guest_cost_is_denied_and_audited(mysql_connection):
    session_id = create_session(None)
    decision = authorize_intent(session_id, None, "ask_cost_margin")
    assert decision["allowed"] is False
    row = fetch_one(
        mysql_connection,
        "SELECT decision FROM chatbot_audit_log WHERE session_id = %s ORDER BY id DESC LIMIT 1",
        (session_id,),
    )
    assert row["decision"] == "denied"


def test_sales_can_read_stock(mysql_connection):
    decision = authorize_intent(create_session(3, "internal_app"), 3, "ask_stock")
    assert decision["allowed"] is True


def test_technician_cannot_read_cost(mysql_connection):
    decision = authorize_intent(create_session(5, "internal_app"), 5, "ask_cost_margin")
    assert decision["allowed"] is False


def test_guest_cannot_read_sales_documents(mysql_connection):
    decision = authorize_intent(create_session(None), None, "ask_sales_policy")
    assert decision["allowed"] is False
