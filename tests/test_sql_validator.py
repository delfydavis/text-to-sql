from app.sql_validator import validate_sql


def test_select_is_allowed():
    assert validate_sql("SELECT * FROM customers;") is True


def test_delete_is_rejected():
    assert validate_sql("DELETE FROM customers;") is False


def test_update_is_rejected():
    assert validate_sql(
        "UPDATE customers SET name = 'test';"
    ) is False


def test_insert_is_rejected():
    assert validate_sql(
        "INSERT INTO customers (name) VALUES ('test');"
    ) is False


def test_drop_is_rejected():
    assert validate_sql("DROP TABLE customers;") is False


def test_alter_is_rejected():
    assert validate_sql(
        "ALTER TABLE customers ADD COLUMN test TEXT;"
    ) is False


def test_truncate_is_rejected():
    assert validate_sql(
        "TRUNCATE TABLE customers;"
    ) is False


def test_multiple_statements_are_rejected():
    assert validate_sql(
        "SELECT * FROM customers; SELECT * FROM orders;"
    ) is False