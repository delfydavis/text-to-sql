import json
import sys
from pathlib import Path

from app.engine import generate_sql, load_schema


BASE_DIR = Path(__file__).resolve().parent

QUESTIONS_FILE = BASE_DIR / "questions.json"
GROUND_TRUTH_FILE = BASE_DIR / "ground_truth.json"
RESULTS_FILE = BASE_DIR / "evaluation_results.json"


def load_evaluation_data():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
        questions = json.load(file)

    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as file:
        ground_truth = json.load(file)

    return questions, ground_truth


def load_existing_results():
    if not RESULTS_FILE.exists():
        return []

    with open(RESULTS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_results(results):
    results = sorted(results, key=lambda item: item["id"])

    with open(RESULTS_FILE, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)


def get_test_ids():
    """
    If test IDs are provided on the command line, run only those tests.
    Otherwise, run the complete evaluation set.
    """
    if len(sys.argv) > 1:
        return {int(test_id) for test_id in sys.argv[1:]}

    return None


def main():
    questions, ground_truth = load_evaluation_data()
    schema = load_schema()

    selected_ids = get_test_ids()

    if selected_ids is not None:
        questions = [
            item
            for item in questions
            if item["id"] in selected_ids
        ]

    ground_truth_by_id = {
        item["id"]: item
        for item in ground_truth
    }

    print(f"Questions loaded: {len(questions)}")
    print(f"Ground truth loaded: {len(ground_truth)}")

    if selected_ids is not None:
        print(f"Selected test IDs: {sorted(selected_ids)}")

    print("\nStarting evaluation...\n")

    existing_results = load_existing_results()

    results_by_id = {
        result["id"]: result
        for result in existing_results
    }

    current_results = []

    for item in questions:
        question_id = item["id"]
        question = item["question"]

        expected = ground_truth_by_id[question_id]

        print("=" * 70)
        print(f"Test {question_id}")
        print(f"Question: {question}")

        decision = generate_sql(question, schema)

        if decision is None:
            print("Status: API_ERROR")

            result = {
                "id": question_id,
                "question": question,
                "status": "api_error",
                "needs_clarification": None,
                "generated_sql": None,
                "clarification_question": None,
            }

            results_by_id[question_id] = result
            current_results.append(result)
            continue

        expected_clarification = expected.get(
            "clarification_required",
            False,
        )

        actual_clarification = decision.needs_clarification

        clarification_match = (
            expected_clarification == actual_clarification
        )

        status = "PASS" if clarification_match else "FAIL"

        print(f"Status: {status}")
        print(f"Expected clarification: {expected_clarification}")
        print(f"Actual clarification:   {actual_clarification}")

        if decision.needs_clarification:
            print(
                f"Clarification: "
                f"{decision.clarification_question}"
            )
        else:
            print(f"Generated SQL: {decision.sql}")

        result = {
            "id": question_id,
            "question": question,
            "status": status,
            "needs_clarification": actual_clarification,
            "generated_sql": decision.sql,
            "clarification_question": (
                decision.clarification_question
            ),
        }

        results_by_id[question_id] = result
        current_results.append(result)

    # Preserve historical results in the JSON artifact.
    results = list(results_by_id.values())
    save_results(results)

    # Report statistics for THIS RUN only.
    passed = sum(
        1
        for result in current_results
        if result["status"] == "PASS"
    )

    failed = sum(
        1
        for result in current_results
        if result["status"] == "FAIL"
    )

    api_errors = sum(
        1
        for result in current_results
        if result["status"] == "api_error"
    )

    evaluated = passed + failed

    print("\n" + "=" * 70)
    print("CURRENT RUN EVALUATION")
    print("=" * 70)

    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"API errors: {api_errors}")
    print(f"Evaluated: {evaluated}")

    if evaluated > 0:
        print(f"Accuracy: {passed / evaluated * 100:.1f}%")
    else:
        print("Accuracy: N/A - no tests were successfully evaluated")

    print(f"\nResults saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()