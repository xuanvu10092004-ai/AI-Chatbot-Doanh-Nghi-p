import pytest  # Khai báo fixture, tham số hóa test và kiểm tra kết quả.

from sql_safety import validate_sql  # Kiểm tra validator và timeout truy vấn SQL.


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


@pytest.mark.parametrize('sql', [
    'WITH models AS (SELECT * FROM v_ai_products) SELECT * FROM models',
    'SELECT model_name FROM v_ai_products UNION SELECT model_name FROM v_ai_inventory',
    'SELECT segment, COUNT(*) FROM v_ai_products GROUP BY segment',
])
def test_valid_ast_queries(sql):
    assert validate_sql(sql, VIEWS).limit == 100


@pytest.mark.parametrize('sql', [
    'SELECT * FROM v_ai_products, users',
    'WITH users AS (SELECT * FROM users) SELECT * FROM users',
    'SELECT * FROM information_schema.tables',
    'SELECT @ai_branch FROM v_ai_products',
    'SELECT GET_LOCK("x", 1) FROM v_ai_products',
    'SELECT * FROM v_ai_products FOR UPDATE',
    'SELECT * FROM v_ai_products WHERE EXISTS (SELECT * FROM users)',
    'SELECT * FROM v_ai_product_costs',
])
def test_ast_attacks_rejected(sql):
    with pytest.raises(ValueError):
        validate_sql(sql, frozenset({'v_ai_products', 'v_ai_inventory'}))
