import os
import random
from datetime import date, timedelta
import time
import psycopg
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

from sql_validator import validate_sql

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
def load_schema():
    with open("app/schema.sql", "r", encoding="utf-8") as file:
        return file.read()
def generate_sql(question, schema):
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
"""
    start_time = time.perf_counter()
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema= SQLDecision,
        ),
    )
    elapsed = time.perf_counter() - start_time
    print(f"Gemini response time: {elapsed:.2f} seconds")
    return SQLDecision.model_validate_json(response.text)

if __name__ == "__main__":
    schema = load_schema()

    question = input("Ask your question: ")

    decision = generate_sql(question, schema)

    while decision.needs_clarification:
        print("\nClarification needed:")
        print(decision.clarification_question)

        answer = input("Your answer: ")

        question = f"""
Original question:
{question}

User's clarification:
{answer}
"""

        decision = generate_sql(question, schema)

print("\nGenerated SQL:")
print(decision.sql)

if validate_sql(decision.sql):
    print("\nSQL validation: PASSED")
else:
    print("\nSQL validation: FAILED")