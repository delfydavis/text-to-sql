import sqlglot
from sqlglot import exp


def validate_sql(sql: str) -> bool:
    if not sql or not sql.strip():
        return False

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except sqlglot.errors.ParseError:
        return False

    # We allow exactly one SQL statement
    if len(statements) != 1:
        return False

    statement = statements[0]

    # Our application is read-only
    if not isinstance(statement, exp.Select):
        return False

    return True
if __name__ == "__main__":
    test_queries = [
    "SELECT * FROM customers;",
    "DELETE FROM customers;",
    "DROP TABLE customers;",
    "SELECT * FROM customers; SELECT * FROM orders;",
    "UPDATE customers SET name = 'test';",
    "INSERT INTO customers (name) VALUES ('test');",
    "ALTER TABLE customers ADD COLUMN test TEXT;",
]
    

    for query in test_queries:
        result = validate_sql(query)
        print(f"{query} -> {result}")