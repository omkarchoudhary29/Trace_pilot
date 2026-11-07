"""
Standardized benchmark dataset for TracePilot Model Comparison and Evaluation Labs.
Contains diverse, realistic errors across multiple languages and runtime environments.
"""

BENCHMARK_INPUTS = [
    {
        "id": "INPUT-PY-01",
        "category": "Python Runtime",
        "title": "Python Type Mismatch",
        "error_text": """
Traceback (most recent call last):
  File "calculator.py", line 18, in calculate_total
    return subtotal + tax_rate
TypeError: unsupported operand type(s) for +: 'int' and 'str'
""",
        "expected_classification": "TypeError",
        "expected_keywords": ["unsupported operand", "int", "str", "subtotal", "tax_rate", "type conversion"],
        "description": "Attempting to add integer and string variables without explicit type casting.",
    },
    {
        "id": "INPUT-PY-02",
        "category": "Python Module",
        "title": "Missing Python Dependency",
        "error_text": """
Traceback (most recent call last):
  File "data_pipeline.py", line 4, in <module>
    import pandas as pd
ModuleNotFoundError: No module named 'pandas'
""",
        "expected_classification": "ModuleNotFoundError",
        "expected_keywords": ["pandas", "virtual environment", "pip install", "environment"],
        "description": "Importing a third-party library not installed in the active virtual environment.",
    },
    {
        "id": "INPUT-JS-01",
        "category": "JavaScript",
        "title": "Undefined Property Access",
        "error_text": """
TypeError: Cannot read properties of undefined (reading 'map')
    at UserList (src/components/UserList.jsx:14:22)
    at renderWithHooks (node_modules/react-dom/cjs/react-dom.development.js:16305:18)
    at mountIndeterminateComponent (node_modules/react-dom/cjs/react-dom.development.js:20074:13)
""",
        "expected_classification": "TypeError",
        "expected_keywords": ["undefined", "map", "array", "UserList", "optional chaining", "initial state"],
        "description": "Calling .map() on an array prop or state variable before data is loaded.",
    },
    {
        "id": "INPUT-DB-01",
        "category": "Database",
        "title": "PostgreSQL Unique Constraint Violation",
        "error_text": """
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "users_email_key"
DETAIL:  Key (email)=(johndoe@example.com) already exists.
CONTEXT:  SQL statement "INSERT INTO users (username, email) VALUES ($1, $2)"
""",
        "expected_classification": "UniqueViolation",
        "expected_keywords": ["duplicate key", "unique constraint", "users_email_key", "already exists", "upsert", "ON CONFLICT"],
        "description": "Attempting to insert an existing email into a uniquely indexed column.",
    },
    {
        "id": "INPUT-API-01",
        "category": "API / HTTP",
        "title": "Expired Authentication Token",
        "error_text": """
HTTP/1.1 401 Unauthorized
Date: Sat, 07 Nov 2026 12:00:00 GMT
Content-Type: application/json

{
  "error": "invalid_token",
  "error_description": "The access token provided has expired at 2026-11-07T11:45:00Z"
}
""",
        "expected_classification": "HTTP 401 Unauthorized",
        "expected_keywords": ["401", "token", "expired", "refresh token", "authentication", "re-authenticate"],
        "description": "API request with an expired OAuth2 bearer token.",
    },
]


def get_benchmark_by_id(input_id: str) -> dict | None:
    """Retrieve a specific benchmark entry by ID."""
    for item in BENCHMARK_INPUTS:
        if item["id"] == input_id:
            return item
    return None

