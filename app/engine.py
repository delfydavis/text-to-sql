import os
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from google import genai
from google.genai import errors
from google.genai import types
from pydantic import BaseModel

from .sql_validator import validate_sql


load_dotenv()


class SQLDecision(BaseModel):
    needs_clarification: bool
    clarification_question: str
    sql: str


client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}


def get_connection():
    return psycopg.connect(**DB_CONFIG)


def execute_sql(sql):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

                columns = [desc.name for desc in cur.description]
                rows = cur.fetchall()

                return columns, rows

    except psycopg.Error as e:
        print("\nDatabase error:")
        print("The query could not be executed.")
        print(f"Details: {e}")
        return None


def display_results(result):
    if result is None:
        return

    columns, rows = result

    if not rows:
        print("\nNo results found.")
        return

    print("\nResult:")
    print(" | ".join(columns))
    print("-" * 60)

    for row in rows:
        print(" | ".join(str(value) for value in row))


def load_schema():
    schema_path = Path(__file__).resolve().parent / "schema.sql"

    with open(schema_path, "r", encoding="utf-8") as file:
        return file.read()


def generate_sql(question, schema) -> SQLDecision | None:
    prompt = f"""
You are a Text-to-SQL and clarification engine.

Your job is to determine whether the user's question
contains enough information to generate a correct SQL query.

DATABASE SCHEMA:
{schema}

USER QUESTION:
{question}

Rules:
1. If the question is clear:
   - needs_clarification = false
   - clarification_question = ""
   - generate the SQL query.

2. If the question is ambiguous or missing important information:
   - needs_clarification = true
   - generate one clear clarification question.
   - sql must be "".

3. Do not guess missing information.

4. Only use tables and columns that exist in the database schema.

5. Ask for clarification only when the missing information
   could affect the correctness of the SQL query.

6. Generate the simplest and most efficient SQL that correctly answers
   the user's question.

7. Select only the columns needed to answer the question.

8. Avoid unnecessary tables, joins, subqueries, and calculations.

9. Do not use SELECT * unless the user explicitly asks for all columns.

10. Do not sacrifice correctness for performance.

11. Generate exactly one read-only SQL statement.

12. Do not generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE,
    CREATE, GRANT, or REVOKE statements.

13. Do not invent values, tables, columns, or business logic that
    are not supported by the schema or user-provided information.

BUSINESS RULES:

- Revenue and sales calculations must use only orders
  where status = 'completed'.

- When calculating revenue, use:
  quantity * unit_price.

- "Revenue" and "sales" refer to completed-order revenue
  unless the user explicitly specifies otherwise.
"""

    start_time = time.perf_counter()

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SQLDecision,
            ),
        )

    except errors.APIError as e:
        print("\nGemini API error:")
        print(f"Status code: {e.code}")
        print(f"Message: {e.message}")
        return None

    elapsed = time.perf_counter() - start_time
    print(f"Gemini response time: {elapsed:.2f} seconds")

    return SQLDecision.model_validate_json(response.text)


def validate_and_execute(sql):
    if not validate_sql(sql):
        return None

    return execute_sql(sql)