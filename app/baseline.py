from app.engine import (
    load_schema,
    generate_sql,
    execute_sql,
    display_results,
)
from app.sql_validator import validate_sql


def main():
    schema = load_schema()

    question = input("Ask your question: ")

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
{question}

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
    if validate_sql(decision.sql):
        print("\nSQL validation: PASSED")

        result = execute_sql(decision.sql)
        display_results(result)

    else:
        print("\nSQL validation: FAILED")
        print("Query was not executed.")


if __name__ == "__main__":
    main()