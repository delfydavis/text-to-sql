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


def normalize_value(value):
    return str(value)


def normalize_rows(rows):
    return [
        tuple(normalize_value(value) for value in row)
        for row in rows
    ]


def exact_result_match(generated_result, expected_result):
    if generated_result is None or expected_result is None:
        return False

    generated_columns, generated_rows = generated_result
    expected_columns, expected_rows = expected_result

    return (
        tuple(generated_columns) == tuple(expected_columns)
        and normalize_rows(generated_rows)
        == normalize_rows(expected_rows)
    )


def expected_answer_match(generated_result, expected_answer):
    """
    Check whether the generated result contains the business answer
    defined by the evaluation case.
    """
    if generated_result is None or expected_answer is None:
        return False

    generated_columns, generated_rows = generated_result

    expected_type = expected_answer.get("type")
    expected_column = expected_answer.get("column")

    if not expected_column:
        return False

    column_map = {
        column.lower(): index
        for index, column in enumerate(generated_columns)
    }

    if expected_column.lower() not in column_map:
        return False

    column_index = column_map[expected_column.lower()]

    generated_values = {
        normalize_value(row[column_index])
        for row in generated_rows
    }

    if expected_type == "single_value":
        expected_value = normalize_value(
            expected_answer["value"]
        )

        return generated_values == {expected_value}

    if expected_type == "value_set":
        expected_values = {
            normalize_value(value)
            for value in expected_answer["values"]
        }

        return generated_values == expected_values

    return False


def main():
    results = load_json(RESULTS_FILE)
    ground_truth = load_json(GROUND_TRUTH_FILE)

    ground_truth_by_id = {
        item["id"]: item
        for item in ground_truth
    }

    exact_passed = 0
    answer_passed = 0
    failed = 0
    skipped = 0

    print("\nStarting business answer evaluation...\n")

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

        if result["needs_clarification"]:
            print("Status: SKIPPED - clarification required")
            skipped += 1
            continue

        generated_sql = result["generated_sql"]

        expected = ground_truth_by_id[question_id]
        expected_sql = expected.get("expected_sql")
        expected_answer = expected.get("expected_answer")

        if not generated_sql:
            print("Status: FAIL - no SQL generated")
            failed += 1
            continue

        if not expected_sql:
            print("Status: FAIL - no expected SQL available")
            failed += 1
            continue

        if not validate_sql(generated_sql):
            print("Status: FAIL - generated SQL rejected by validator")
            failed += 1
            continue

        generated_result = execute_sql(generated_sql)
        expected_result = execute_sql(expected_sql)

        if generated_result is None:
            print("Status: FAIL - generated SQL failed during execution")
            failed += 1
            continue

        if expected_result is None:
            print(
                "Status: FAIL - ground-truth SQL failed during execution"
            )
            failed += 1
            continue

        if exact_result_match(
            generated_result,
            expected_result,
        ):
            print("Status: PASS - exact result match")
            exact_passed += 1
            answer_passed += 1

        elif expected_answer_match(
            generated_result,
            expected_answer,
        ):
            print("Status: PASS - business answer correct")
            answer_passed += 1

        else:
            print("Status: FAIL")
            failed += 1

            print("\nGenerated SQL:")
            print(generated_sql)

            print("\nExpected SQL:")
            print(expected_sql)

            print("\nGenerated result:")
            print(generated_result)

            print("\nExpected result:")
            print(expected_result)

    evaluated = answer_passed + failed

    print("\n" + "=" * 70)
    print("BUSINESS ANSWER EVALUATION")
    print("=" * 70)

    print(f"Exact result matches: {exact_passed}")
    print(f"Business-answer correct: {answer_passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print(f"Evaluated: {evaluated}")

    if evaluated > 0:
        accuracy = answer_passed / evaluated * 100
        print(f"Business-answer accuracy: {accuracy:.1f}%")
    else:
        print(
            "Business-answer accuracy: "
            "N/A - no tests were evaluated"
        )


if __name__ == "__main__":
    main()