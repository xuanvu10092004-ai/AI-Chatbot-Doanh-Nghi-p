import pytest

from sql_safety import validate_sql


VIEWS = frozenset({"v_ai_products", "v_ai_inventory", "v_ai_customers", "v_ai_orders", "v_ai_product_costs"})


def test_validator_adds_limit_and_timeout():
    query = validate_sql("SELECT model_name FROM v_ai_products", VIEWS)
    assert "MAX_EXECUTION_TIME(5000)" in query.sql
    assert query.sql.endswith("LIMIT 100")


def test_validator_caps_limit():
    query = validate_sql("SELECT model_name FROM v_ai_products LIMIT 1000", VIEWS)
    assert query.limit == 100
    assert query.sql.endswith("LIMIT 100")


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE v_ai_products",
        "SELECT 1; DROP TABLE v_ai_products",
        "SELECT * FROM users",
        "SELECT * FROM v_ai_products -- comment",
        "SELECT SLEEP(10) FROM v_ai_products",
        "SELECT * INTO OUTFILE 'dump.txt' FROM v_ai_products",
    ],
)
def test_validator_rejects_unsafe_sql(sql):
    with pytest.raises(ValueError):
        validate_sql(sql, VIEWS)
