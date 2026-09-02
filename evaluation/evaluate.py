import json
from pathlib import Path

from app.engine import load_schema, generate_sql


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


def save_results(results):
    with open(RESULTS_FILE, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)


if __name__ == "__main__":
    questions, ground_truth = load_evaluation_data()
    schema = load_schema()

    ground_truth_by_id = {
        item["id"]: item
        for item in ground_truth
    }

    print(f"Questions loaded: {len(questions)}")
    print(f"Ground truth loaded: {len(ground_truth)}")
    print("\nStarting evaluation...\n")

    results = []

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

            results.append({
                "id": question_id,
                "question": question,
                "status": "api_error",
                "needs_clarification": None,
                "generated_sql": None,
                "clarification_question": None
            })

            continue

        expected_clarification = expected.get(
            "clarification_required", False
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

        results.append({
            "id": question_id,
            "question": question,
            "status": status,
            "needs_clarification": actual_clarification,
            "generated_sql": decision.sql,
            "clarification_question": (
                decision.clarification_question
            )
        })

    save_results(results)

    passed = sum(
        1 for result in results
        if result["status"] == "PASS"
    )

    failed = sum(
        1 for result in results
        if result["status"] == "FAIL"
    )

    api_errors = sum(
        1 for result in results
        if result["status"] == "api_error"
    )

    evaluated = passed + failed

    print("\n" + "=" * 70)
    print("CLARIFICATION EVALUATION")
    print("=" * 70)

    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"API errors: {api_errors}")

    if evaluated > 0:
        print(
            f"Accuracy: "
            f"{passed / evaluated * 100:.1f}%"
        )
    else:
        print("Accuracy: N/A")

    print(f"\nResults saved to: {RESULTS_FILE}")