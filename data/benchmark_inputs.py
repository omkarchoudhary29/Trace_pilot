"""
Standardized benchmark dataset for TracePilot Evaluation Engine and Model Comparison.

Covers:
- Python exceptions (runtime type errors, dependencies, index boundaries)
- JavaScript / TypeScript errors (property access, reference errors)
- Database errors (unique constraint violations, connection failures)
- API / HTTP errors (expired authentication tokens, rate limits)
- Application logs (thread failures, socket resets)

Each record defines deterministic ground truth: expected classification, category,
severity, known evidence present in the input, root-cause criteria, and verification guidelines.
"""

from __future__ import annotations

from typing import Any

BENCHMARK_INPUTS: list[dict[str, Any]] = [
    {
        "id": "CASE-PY-01",
        "title": "Python Type Mismatch",
        "category": "runtime",
        "severity": "medium",
        "programming_language": "Python",
        "error_text": """Traceback (most recent call last):
  File "calculator.py", line 18, in calculate_total
    return subtotal + tax_rate
TypeError: unsupported operand type(s) for +: 'int' and 'str'""",
        "expected_classification": "TypeError",
        "known_evidence": [
            "calculator.py",
            "18",
            "calculate_total",
            "subtotal",
            "tax_rate",
            "unsupported operand type(s) for +: 'int' and 'str'",
        ],
        "known_root_causes": [
            "Adding integer subtotal and string tax_rate without explicit type casting",
            "tax_rate is str while subtotal is int",
        ],
        "expected_debugging_direction": "Inspect operand types and cast tax_rate to float or int before summing",
        "verification_criteria": "calculate_total(100, '0.05') returns 100.05 or passes float/int parameters",
        "is_synthetic": False,
        "description": "Attempting to perform arithmetic addition between an int and a str.",
    },
    {
        "id": "CASE-PY-02",
        "title": "Missing Python Dependency",
        "category": "dependency",
        "severity": "high",
        "programming_language": "Python",
        "error_text": """Traceback (most recent call last):
  File "data_pipeline.py", line 4, in <module>
    import pandas as pd
ModuleNotFoundError: No module named 'pandas'""",
        "expected_classification": "ModuleNotFoundError",
        "known_evidence": [
            "data_pipeline.py",
            "4",
            "pandas",
            "No module named 'pandas'",
        ],
        "known_root_causes": [
            "pandas package is not installed in the active virtual environment",
            "Virtual environment is missing dependency pandas",
        ],
        "expected_debugging_direction": "Verify active Python environment and run pip install pandas",
        "verification_criteria": "python -c 'import pandas' exits with code 0",
        "is_synthetic": False,
        "description": "Importing a third-party library not installed in the active environment.",
    },
    {
        "id": "CASE-PY-03",
        "title": "Python List Index Out of Range",
        "category": "runtime",
        "severity": "medium",
        "programming_language": "Python",
        "error_text": """Traceback (most recent call last):
  File "user_parser.py", line 23, in parse_tokens
    role = tokens[2]
IndexError: list index out of range""",
        "expected_classification": "IndexError",
        "known_evidence": [
            "user_parser.py",
            "23",
            "parse_tokens",
            "tokens[2]",
            "IndexError: list index out of range",
        ],
        "known_root_causes": [
            "Accessing third element of tokens list when list contains fewer than 3 elements",
            "tokens length is less than or equal to 2",
        ],
        "expected_debugging_direction": "Check len(tokens) before accessing index 2 or add default role fallback",
        "verification_criteria": "parse_tokens(['admin', 'user']) handles missing role without crashing",
        "is_synthetic": True,
        "description": "Direct index lookup exceeding the boundaries of an input list.",
    },
    {
        "id": "CASE-JS-01",
        "title": "JavaScript Undefined Property Access",
        "category": "runtime",
        "severity": "high",
        "programming_language": "JavaScript",
        "error_text": """TypeError: Cannot read properties of undefined (reading 'map')
    at UserList (src/components/UserList.jsx:14:22)
    at renderWithHooks (node_modules/react-dom/cjs/react-dom.development.js:16305:18)
    at mountIndeterminateComponent (node_modules/react-dom/cjs/react-dom.development.js:20074:13)""",
        "expected_classification": "TypeError",
        "known_evidence": [
            "src/components/UserList.jsx",
            "14",
            "UserList",
            "map",
            "Cannot read properties of undefined (reading 'map')",
        ],
        "known_root_causes": [
            "Calling .map() on an array prop or state variable before data has resolved or initialized",
            "Target array is undefined during initial render",
        ],
        "expected_debugging_direction": "Provide default empty array fallback users=[] or use optional chaining users?.map()",
        "verification_criteria": "UserList renders cleanly when users is null/undefined without unhandled TypeError",
        "is_synthetic": False,
        "description": "Calling .map() on undefined state during component render.",
    },
    {
        "id": "CASE-JS-02",
        "title": "JavaScript Reference Error",
        "category": "runtime",
        "severity": "medium",
        "programming_language": "JavaScript",
        "error_text": """ReferenceError: jwtToken is not defined
    at generateSession (controllers/auth.js:42:15)
    at Layer.handle [as handle_request] (node_modules/express/lib/router/layer.js:95:5)""",
        "expected_classification": "ReferenceError",
        "known_evidence": [
            "controllers/auth.js",
            "42",
            "generateSession",
            "jwtToken",
            "ReferenceError: jwtToken is not defined",
        ],
        "known_root_causes": [
            "Variable jwtToken was referenced without declaration or is out of lexical scope",
            "Misspelled variable or missing import for jwtToken",
        ],
        "expected_debugging_direction": "Declare jwtToken with const/let or verify imported symbol names",
        "verification_criteria": "generateSession executes without throwing ReferenceError",
        "is_synthetic": True,
        "description": "Referencing an undeclared variable in an Express route handler.",
    },
    {
        "id": "CASE-DB-01",
        "title": "PostgreSQL Unique Constraint Violation",
        "category": "database",
        "severity": "medium",
        "programming_language": "SQL",
        "error_text": """psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "users_email_key"
DETAIL:  Key (email)=(johndoe@example.com) already exists.
CONTEXT:  SQL statement "INSERT INTO users (username, email) VALUES ($1, $2)" """,
        "expected_classification": "UniqueViolation",
        "known_evidence": [
            "users_email_key",
            "johndoe@example.com",
            "duplicate key value violates unique constraint",
            "INSERT INTO users",
        ],
        "known_root_causes": [
            "Attempting to insert an already registered email (johndoe@example.com) into unique column",
            "Violating unique constraint users_email_key",
        ],
        "expected_debugging_direction": "Check email existence before insertion or implement ON CONFLICT (email) DO UPDATE (upsert)",
        "verification_criteria": "Inserting duplicate email returns user-friendly error or performs idempotent upsert",
        "is_synthetic": False,
        "description": "Inserting duplicate key value into a uniquely indexed database column.",
    },
    {
        "id": "CASE-DB-02",
        "title": "PostgreSQL Connection Refused",
        "category": "database",
        "severity": "critical",
        "programming_language": "SQL",
        "error_text": """psycopg2.OperationalError: could not connect to server: Connection refused
\tIs the server running on host "localhost" (127.0.0.1) and accepting
\tTCP/IP connections on port 5432?""",
        "expected_classification": "OperationalError",
        "known_evidence": [
            "localhost",
            "5432",
            "Connection refused",
            "OperationalError",
        ],
        "known_root_causes": [
            "PostgreSQL daemon is not running on localhost or port 5432 is blocked",
            "Database service is down or connection host/port is misconfigured",
        ],
        "expected_debugging_direction": "Verify PostgreSQL service status with systemctl/service and confirm port 5432 is open",
        "verification_criteria": "pg_isready -h localhost -p 5432 reports accepting connections",
        "is_synthetic": True,
        "description": "Database server daemon is unreachable or rejecting TCP connections.",
    },
    {
        "id": "CASE-API-01",
        "title": "HTTP 401 Expired Bearer Token",
        "category": "authentication",
        "severity": "high",
        "programming_language": "HTTP",
        "error_text": """HTTP/1.1 401 Unauthorized
Date: Sat, 07 Nov 2026 12:00:00 GMT
Content-Type: application/json

{
  "error": "invalid_token",
  "error_description": "The access token provided has expired at 2026-11-07T11:45:00Z"
}""",
        "expected_classification": "HTTP 401 Unauthorized",
        "known_evidence": [
            "401",
            "Unauthorized",
            "invalid_token",
            "The access token provided has expired",
        ],
        "known_root_causes": [
            "Bearer access token expired at 2026-11-07T11:45:00Z",
            "Authentication token lifetime exceeded without refresh",
        ],
        "expected_debugging_direction": "Exchange OAuth2 refresh token for a new access token or prompt user to re-login",
        "verification_criteria": "Request made with refreshed access token returns HTTP 200 OK",
        "is_synthetic": False,
        "description": "Client made an API call using an expired OAuth2 bearer token.",
    },
    {
        "id": "CASE-API-02",
        "title": "HTTP 429 Rate Limit Exceeded",
        "category": "resource",
        "severity": "high",
        "programming_language": "HTTP",
        "error_text": """HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
Content-Type: application/json

{"error": "rate_limit_exceeded", "message": "Rate limit exceeded. Try again in 60 seconds."}""",
        "expected_classification": "HTTP 429 Too Many Requests",
        "known_evidence": [
            "429",
            "Too Many Requests",
            "Retry-After: 60",
            "rate_limit_exceeded",
        ],
        "known_root_causes": [
            "Client request volume exceeded rate limit quota (100 requests per window)",
            "Too many requests sent in short interval",
        ],
        "expected_debugging_direction": "Adhere to Retry-After: 60 header with exponential backoff and add client-side throttling",
        "verification_criteria": "Retrying request after 60 seconds succeeds with HTTP 200",
        "is_synthetic": True,
        "description": "Downstream API rejected request because client exceeded rate quota.",
    },
    {
        "id": "CASE-LOG-01",
        "title": "Worker Thread Socket Reset Log",
        "category": "runtime",
        "severity": "critical",
        "programming_language": "Log",
        "error_text": """2026-11-07 14:22:01.402 [Worker-3] ERROR com.app.sync.SyncWorker - Thread died unexpectedly: ConnectionResetError: [Errno 104] Connection reset by peer
\tat sync_worker.py:88 in process_batch
\tat sync_worker.py:112 in run""",
        "expected_classification": "ConnectionResetError",
        "known_evidence": [
            "Worker-3",
            "sync_worker.py",
            "88",
            "112",
            "ConnectionResetError",
            "Connection reset by peer",
        ],
        "known_root_causes": [
            "Remote server or peer TCP connection was abruptly reset during batch processing",
            "Unhandled ConnectionResetError terminated worker thread",
        ],
        "expected_debugging_direction": "Wrap process_batch in try/except ConnectionResetError with backoff retry",
        "verification_criteria": "Simulated connection drop triggers retry handler instead of crashing Worker-3 thread",
        "is_synthetic": True,
        "description": "Application log recording an unhandled socket reset killing a background worker thread.",
    },
]


def get_benchmark_by_id(case_id: str) -> dict[str, Any] | None:
    """Retrieve a specific benchmark entry by ID."""
    for item in BENCHMARK_INPUTS:
        if item["id"] == case_id:
            return item
    return None
