from app.engine import (
    load_schema,
    generate_sql,
    validate_and_execute,
    display_results,
)


def main():
    schema = load_schema()

    original_question = input("Ask your question: ")
    question = original_question

    decision = generate_sql(question, schema)

    # Handle Gemini/API failure
    if decision is None:
        print(
            "\nUnable to generate SQL because the Gemini service "
            "is currently unavailable."
        )
        return

    # Clarification loop
    while decision.needs_clarification:
        print("\nClarification needed:")
        print(decision.clarification_question)

        answer = input("Your answer: ")

        question = f"""
Original question:
{original_question}

User's clarification:
{answer}
"""

        decision = generate_sql(question, schema)

        # Handle Gemini/API failure during clarification
        if decision is None:
            print(
                "\nUnable to generate SQL because the Gemini service "
                "is currently unavailable."
            )
            return

    # Display generated SQL
    print("\nGenerated SQL:")
    print(decision.sql)

    # Validate and execute
    result = validate_and_execute(decision.sql)

    if result is None:
        print("\nSQL validation: FAILED")
        print("Query was not executed.")
        return

    print("\nSQL validation: PASSED")
    display_results(result)


if __name__ == "__main__":
    main()