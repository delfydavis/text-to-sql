# Text-to-SQL Clarification Engine

### Natural language → clarification → validated SQL → database answer

> **The LLM can reason. The system retains control.**

A Text-to-SQL clarification engine built around a practical engineering problem:

**What should happen when a language model can generate SQL, but the user's question is ambiguous?**

Instead of guessing, the system can ask for clarification.

Instead of blindly trusting generated SQL, the application validates it before execution.

Instead of treating generated SQL as the answer, the system evaluates the resulting business answer against PostgreSQL.

---

## The Core Idea

Consider:

> **"Show me the best customers."**

"Best" could mean:

- highest revenue
- most orders
- highest average order value

Generating SQL immediately requires silently choosing a business interpretation.

**This system does not guess.**

```text
User question
      ↓
Understand intent
      ↓
Is clarification needed?
   ↙             ↘
 YES              NO
  ↓                ↓
Clarify        Generate SQL
  ↓                ↓
User answer    Structured decision
  └───────→────────┘
                   ↓
             Validate SQL
                   ↓
              PostgreSQL
                   ↓
             Business result
```

---

## Architecture

The system separates **probabilistic reasoning** from **deterministic execution**.

```text
                         ┌──────────────────────┐
                         │        USER          │
                         │ Natural language     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   REASONING LAYER    │
                         │       Gemini         │
                         │                      │
                         │ • Understand intent  │
                         │ • Detect ambiguity   │
                         │ • Ask clarification  │
                         │ • Generate SQL       │
                         └──────────┬───────────┘
                                    │
                              SQLDecision
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ APPLICATION CONTROL  │
                         │ & VALIDATION         │
                         │                      │
                         │ Pydantic contract    │
                         │ SQLGlot validation   │
                         └──────────┬───────────┘
                                    │
                           Valid SELECT only
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     PostgreSQL       │
                         │                      │
                         │ Authoritative        │
                         │ query execution      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   BUSINESS RESULT    │
                         └──────────────────────┘
```

### Trust Boundary

The LLM is treated as a reasoning component, not as an execution authority.

```text
LLM
 │
 │ proposes a structured decision
 ▼
SQLDecision
 │
 │ deterministic validation
 ▼
SQLGlot
 │
 │ approved SELECT
 ▼
PostgreSQL
 │
 │ actual execution
 ▼
Business result
```

The responsibilities are deliberately separated:

- **Gemini** — understands the natural-language request, detects meaningful ambiguity, asks for clarification, and proposes SQL.
- **Pydantic** — defines the structured contract between the model and the application.
- **SQLGlot** — parses the generated SQL into an AST and lets the application enforce its read-only policy.
- **PostgreSQL** — performs the authoritative database execution.
- **Python application layer** — orchestrates the complete workflow.

This creates a clear control boundary: **the model can propose what should happen, but the application decides what is allowed to execute.**

---

## Engineering Decisions

### 1. Clarify Instead of Guessing

Ambiguity that can change the meaning of a SQL query is treated as a correctness problem.

Rather than silently choosing an interpretation, the system asks the user for clarification.

**Decision:** When missing information can affect SQL correctness, ask instead of guessing.

### 2. Use a Structured Model Contract

The LLM response is represented through a Pydantic `SQLDecision` model:

| Field | Purpose |
|---|---|
| `needs_clarification` | Whether additional information is required |
| `clarification_question` | Question to ask the user |
| `sql` | Generated SQL when the request is sufficiently clear |

**Decision:** Use structured output instead of relying on free-form model responses.

### 3. Keep SQL Safety Deterministic

Generated SQL is treated as **untrusted input**.

The application requires:

- non-empty SQL
- exactly one statement
- valid PostgreSQL parsing
- a `SELECT` statement

Statements such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, and `TRUNCATE` are rejected.

**Decision:** Let the LLM propose SQL, but keep execution eligibility under deterministic application control.

### 4. Make Business Semantics Explicit

Revenue calculations in this project use:

- completed orders
- `quantity × unit_price`

These rules are explicitly provided to the reasoning layer.

**Decision:** Make important business semantics explicit rather than expecting the model to infer them.

### 5. Let PostgreSQL Remain Authoritative

A SQL statement can be syntactically valid and still fail against the actual database.

PostgreSQL therefore remains the authoritative execution layer.

**Decision:** Use SQL parsing for application-level validation and the database for actual execution correctness.

### 6. Evaluate Business Answers

Different SQL queries can be structurally different while producing the same correct answer.

The evaluation distinguishes between:

- exact result matches
- business-answer correctness

**Decision:** Evaluate whether the system produced the correct business answer, not only whether its SQL resembles a predefined query.

---

## Testing & Evaluation

The system is evaluated at two levels:

1. **Deterministic application behavior**
2. **LLM-generated SQL and business answers**

### Automated Tests

The project includes **12 automated tests** across unit and integration testing.

| Test area | What is verified |
|---|---|
| SQL validation | Valid `SELECT` statements are accepted |
| SQL safety | Unsafe statements are rejected |
| Statement control | Multiple SQL statements are rejected |
| Database execution | Valid SQL executes against PostgreSQL |
| Result handling | Returned columns and rows are handled correctly |
| Database errors | Invalid database queries fail safely |

Run the test suite:

```bash
python -m pytest
```

### LLM Evaluation

The LLM is evaluated separately using **10 representative natural-language questions** covering straightforward, analytical, ambiguous, and multi-table requests.

Each case has independently defined ground truth. Generated SQL is validated and executed against PostgreSQL before evaluating the resulting business answer.

```text
Natural-language question
          ↓
       Gemini
          ↓
    Generated decision
          ↓
     SQL validation
          ↓
    PostgreSQL execution
          ↓
   Business-answer comparison
```

The evaluation distinguishes between:

- **Exact result match** — the generated query produces the same result as the reference query.
- **Business-answer correctness** — structurally different SQL can still be correct when it produces the expected business answer.

API availability or quota failures are reported separately from SQL correctness failures.

---

## Engineering Lessons

The first evaluation exposed a gap between **syntactic SQL correctness** and **business correctness**.

Some generated queries were valid SQL but did not correctly represent the project's revenue semantics. The underlying issue was that important business rules—such as using completed orders and `quantity × unit_price` for revenue—were not explicit enough.

The system was refined by making those semantics explicit in the reasoning layer and re-evaluating the affected cases.

The evaluation itself also exposed another limitation: exact SQL comparison can reject a query even when it produces the correct business answer.

The evaluator was therefore refined to distinguish between:

- **exact result matching**
- **business-answer correctness**

The goal was not to optimize the score after seeing model outputs. The goal was to make both the **system and the evaluation better represent the problem being solved.**

### Engineering Loop

```text
Observed failure
      ↓
Identify the underlying cause
      ↓
Change the system
      ↓
Re-test
      ↓
Re-evaluate
```

---

## Design Philosophy

The system deliberately uses a small number of components with clear responsibilities.

No additional infrastructure is introduced unless it solves a demonstrated problem.

The objective is not to maximize architectural complexity. It is to establish clear boundaries between **reasoning, control, execution, and evaluation**.

---

## Technology

| Technology | Role |
|---|---|
| **Python** | Application orchestration and control flow |
| **Gemini** | Natural-language reasoning, clarification, and SQL generation |
| **Pydantic** | Structured model-response contract |
| **SQLGlot** | PostgreSQL SQL parsing and deterministic validation |
| **PostgreSQL** | Authoritative database execution |
| **pytest** | Automated testing |
| **python-dotenv** | Environment configuration |

Each component has a defined responsibility.

---

## Project Structure

```text
text-to-sql/
│
├── app/                    # Application logic
│   ├── baseline.py
│   ├── engine.py
│   ├── sql_validator.py
│   ├── schema.sql
│   └── __init__.py
│
├── evaluation/             # LLM evaluation
│   ├── questions.json
│   ├── ground_truth.json
│   ├── evaluation_results.json
│   ├── evaluate.py
│   └── score_results.py
│
├── tests/                  # Automated tests
│   ├── test_sql_validator.py
│   └── test_integration.py
│
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Example

### User

> Show me the best customers.

### System

> How should I define "best customers" — by total revenue, number of orders, or average order value?

### User

> By total revenue.

The system then generates SQL, validates it, and executes the approved query against PostgreSQL.

The important distinction is that **clarification happens before SQL generation when the missing information could change the meaning of the query.**

---

## Limitations

This is a focused prototype rather than a production-scale analytics platform.

Current limitations include:

- Gemini availability and quota can affect LLM evaluation.
- The SQL safety policy is intentionally limited to read-only `SELECT` execution.
- Business semantics are explicitly defined for the current database and use cases.
- LLM evaluation uses a representative set of 10 questions rather than a large benchmark.
- The current interface is a command-line application.

These constraints are deliberate. The project prioritizes **correctness, control, and clear engineering boundaries** over unnecessary infrastructure.

---

## Future Improvements

Potential production-oriented extensions include:

- stronger schema-aware validation
- authorization and row-level access controls
- query cost and resource limits
- larger evaluation datasets
- observability and tracing
- API and UI layers
- support for additional databases and business domains

These would be driven by actual requirements rather than added for architectural complexity.

---

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd text-to-sql
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```text
GEMINI_API_KEY=your_api_key

DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

**Never commit `.env` or API keys to Git.**

### 5. Run the application

```bash
python -m app.baseline
```

### 6. Run the tests

```bash
python -m pytest
```

---

## Engineering Takeaway

A reliable Text-to-SQL system is not simply:

```text
Natural language → SQL
```

It is a controlled decision pipeline:

```text
Understand
    ↓
Clarify when necessary
    ↓
Structure the decision
    ↓
Validate deterministically
    ↓
Execute against the real database
    ↓
Evaluate the business answer
```

The model provides probabilistic reasoning.

The application provides control.

The database provides authoritative execution.

The evaluation provides evidence.

> **The LLM can reason. The system retains control.**
