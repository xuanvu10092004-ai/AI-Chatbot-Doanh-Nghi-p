from query_planner import plan_query  # Tạo SQL template cho intent được nhận diện.
from sql_service import answer_sql_question  # Thực thi câu hỏi SQL hoặc truy vấn đã kiểm tra.


def test_cr01_out_of_stock_question_is_planned_as_inventory_query():
    question = "xe nao het hang o kho CR01"
    sql, params = plan_query(question, "ask_stock")

    assert "v_ai_inventory" in sql
    assert "branch_code = %s" in sql
    assert "quantity = 0" in sql
    assert params == ("CR01",)


def test_cr01_out_of_stock_question_returns_only_empty_cr01_rows():
    result = answer_sql_question("xe nao het hang o kho CR01", 1)

    assert result.rows
    assert {row["branch_code"] for row in result.rows} == {"CR01"}
    assert {row["quantity"] for row in result.rows} == {0}
