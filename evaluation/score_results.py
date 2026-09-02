import json
from pathlib import Path

from app.engine import execute_sql
from app.sql_validator import validate_sql


BASE_DIR = Path(__file__).resolve().parent

RESULTS_FILE = BASE_DIR / "evaluation_results.json"
GROUND_TRUTH_FILE = BASE_DIR / "ground_truth.json"


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize_result(result):
    if result is None:
        return None

    columns, rows = result

    normalized_rows = [
        tuple(str(value) for value in row)
        for row in rows
    ]

    return (
        tuple(columns),
        tuple(normalized_rows),
    )


def main():
    results = load_json(RESULTS_FILE)
    ground_truth = load_json(GROUND_TRUTH_FILE)

    ground_truth_by_id = {
        item["id"]: item
        for item in ground_truth
    }

    sql_passed = 0
    sql_failed = 0
    skipped = 0

    print("\nStarting SQL correctness evaluation...\n")

    for result in results:
        question_id = result["id"]
        question = result["question"]

        print("=" * 70)
        print(f"Test {question_id}")
        print(f"Question: {question}")

        if result["status"] == "api_error":
            print("Status: SKIPPED - Gemini API error")
            skipped += 1
            continue

        generated_sql = result["generated_sql"]
        expected_sql = ground_truth_by_id[question_id].get(
            "expected_sql"
        )

        # Clarification cases do not have SQL to execute.
        if result["needs_clarification"]:
            print("Status: SKIPPED - clarification required")
            skipped += 1
            continue

        if not generated_sql:
            print("Status: FAIL - no SQL generated")
            sql_failed += 1
            continue

        if not expected_sql:
            print("Status: FAIL - no expected SQL available")
            sql_failed += 1
            continue

        # Safety check on generated SQL
        if not validate_sql(generated_sql):
            print("Status: FAIL - generated SQL rejected by validator")
            sql_failed += 1
            continue

        generated_result = execute_sql(generated_sql)
        expected_result = execute_sql(expected_sql)

        generated_normalized = normalize_result(generated_result)
        expected_normalized = normalize_result(expected_result)

        if generated_normalized == expected_normalized:
            print("Status: PASS")
            sql_passed += 1
        else:
            print("Status: FAIL")
            sql_failed += 1

            print("\nGenerated SQL:")
            print(generated_sql)

            print("\nExpected SQL:")
            print(expected_sql)

            print("\nGenerated result:")
            print(generated_result)

            print("\nExpected result:")
            print(expected_result)

    evaluated = sql_passed + sql_failed

    print("\n" + "=" * 70)
    print("SQL CORRECTNESS EVALUATION")
    print("=" * 70)

    print(f"Passed: {sql_passed}")
    print(f"Failed: {sql_failed}")
    print(f"Skipped: {skipped}")

    if evaluated > 0:
        accuracy = sql_passed / evaluated * 100
        print(f"SQL accuracy: {accuracy:.1f}%")
    else:
        print("SQL accuracy: N/A")


if __name__ == "__main__":
    main()