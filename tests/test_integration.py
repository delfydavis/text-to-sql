import pytest

from app.engine import execute_sql
from app.sql_validator import validate_sql


def test_valid_select_executes():
    sql = "SELECT COUNT(*) FROM customers;"

    assert validate_sql(sql) is True

    result = execute_sql(sql)

    assert result is not None

    columns, rows = result

    assert columns == ["count"]
    assert len(rows) == 1


def test_valid_query_returns_expected_columns():
    sql = """
        SELECT id, name
        FROM customers
        ORDER BY id
        LIMIT 3;
    """

    assert validate_sql(sql) is True

    result = execute_sql(sql)

    assert result is not None

    columns, rows = result

    assert columns == ["id", "name"]
    assert len(rows) <= 3


def test_unsafe_query_is_not_executed():
    sql = "DELETE FROM customers;"

    assert validate_sql(sql) is False


def test_invalid_sql_is_handled():
    sql = "SELECT definitely_not_a_real_column FROM customers;"

    assert validate_sql(sql) is True

    result = execute_sql(sql)

    assert result is None