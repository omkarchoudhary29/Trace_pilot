"""
Tests for FastAPI application server (Phase 10).

Covers:
- GET /api/health status check and model metadata (zero secret leak).
- GET /api/examples preset scenario listing.
- GET /api/evaluation stored benchmark results.
- POST /api/debug synchronous endpoint:
  - Valid structured request
  - Input validation (empty, whitespace, oversized)
  - API authentication error handling (401)
  - Rate limit / quota exhaustion handling (429)
  - Timeout error handling (504)
  - Service unavailable handling (503)
- POST /api/debug/stream Server-Sent Events (SSE) streaming endpoint.
- CORS header configuration.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.server import app
from app.llm.exceptions import (
    APIAuthenticationError,
    APIQuotaExceededError,
    APIServiceError,
    APITimeoutError,
)
from app.llm.streaming import RequestUsageMetrics, StreamEvent
from app.schemas.debugging_report import DebuggingReport

client = TestClient(app)

SAMPLE_REPORT_DICT = {
    "error_information": {
        "error_type": "TypeError",
        "error_message": "unsupported operand type(s) for +: 'int' and 'str'",
        "programming_language": "Python",
        "severity": "medium",
        "category": "runtime",
        "filename": "calculator.py",
        "line_number": 18,
        "function_name": "calculate_total",
    },
    "error_summary": {
        "short_description": "Type mismatch adding int and str.",
        "failed_operation": "Binary addition",
        "plain_language_explanation": "Cannot add string to integer directly.",
    },
    "evidence": {
        "error_message_excerpts": ["unsupported operand type(s) for +: 'int' and 'str'"],
        "traceback_or_log_excerpts": ["File calculator.py, line 18 in calculate_total"],
        "extracted_file_and_line": "calculator.py:18",
        "observed_facts": ["subtotal is int, tax_rate is str"],
        "inferred_information": ["tax_rate was passed as string"],
    },
    "root_cause_analysis": {
        "primary_hypothesis": {
            "hypothesis": "tax_rate is a string instead of numeric",
            "supporting_evidence": ["Line 18 execution"],
            "confidence": "high",
        },
        "alternative_hypotheses": [],
        "missing_information_to_confirm": [],
    },
    "debugging_steps": [
        {
            "step_number": 1,
            "action": "Cast tax_rate to float",
            "why_recommended": "Converts string to float before summation",
            "relevant_evidence": "calculator.py:18",
            "expected_outcome": "Sum succeeds",
        }
    ],
    "suggested_fix": {
        "explanation": "Cast tax_rate before summing",
        "code_example": "return subtotal + float(tax_rate)",
        "where_to_apply": "calculator.py line 18",
        "assumptions_and_limitations": ["tax_rate string is a valid float string"],
    },
    "verification": {
        "how_to_verify": "Call calculate_total(100, '0.05')",
        "expected_behavior": "Returns 100.05 without raising TypeError",
        "suggested_test_cases": ["calculate_total(100, '0.05')"],
        "if_error_persists": "Check if string has invalid characters",
    },
    "confidence_and_review": {
        "overall_confidence": "high",
        "human_review_required": False,
        "uncertainty_explanation": "Standard type error",
    },
}


# ==========================================
# 1. Health & Examples Endpoints
# ==========================================


def test_api_health_endpoint():
    """Verify health endpoint returns status, version, and model names without secrets."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "primary_model" in data
    assert "GEMINI_API_KEY" not in str(data)


def test_api_examples_endpoint():
    """Verify examples endpoint returns preset benchmark cases."""
    response = client.get("/api/examples")
    assert response.status_code == 200
    examples = response.json()
    assert len(examples) >= 5
    first = examples[0]
    assert "id" in first
    assert "title" in first
    assert "error_text" in first


def test_api_evaluation_endpoint():
    """Verify evaluation endpoint returns evaluation data or honest unavailable state."""
    response = client.get("/api/evaluation")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data


# ==========================================
# 2. Input Validation on /api/debug
# ==========================================


def test_api_debug_empty_input_rejected():
    """Verify empty error text is rejected with HTTP 400 or 422."""
    response = client.post("/api/debug", json={"error_text": ""})
    assert response.status_code in (400, 422)


def test_api_debug_oversized_input_rejected():
    """Verify error text exceeding max length is rejected with HTTP 400."""
    huge_text = "A" * 15000
    response = client.post("/api/debug", json={"error_text": huge_text})
    assert response.status_code in (400, 422)


# ==========================================
# 3. Synchronous Debug Endpoint Execution
# ==========================================


@patch("app.api.server.generate_response_with_metrics")
def test_api_debug_success_structured(mock_gen):
    """Verify successful structured debugging response."""
    report = DebuggingReport.model_validate(SAMPLE_REPORT_DICT)
    metrics = RequestUsageMetrics(
        request_id="req-test1234",
        model_used="gemini-3.5-flash-lite",
        start_time="2026-11-07T12:00:00Z",
        total_duration_seconds=1.23,
        prompt_tokens=100,
        response_tokens=50,
        total_tokens=150,
        finish_reason="STOP",
        is_complete=True,
    )

    mock_gen.return_value = (report.model_dump_json(), metrics)

    payload = {
        "error_text": 'File "calculator.py", line 18\nTypeError: unsupported operand',
        "structured": True,
    }
    response = client.post("/api/debug", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["report"]["error_information"]["error_type"] == "TypeError"
    assert data["metrics"]["total_tokens"] == 150


@patch("app.api.server.generate_response_with_metrics")
def test_api_debug_authentication_error(mock_gen):
    """Verify authentication failure maps to HTTP 401."""
    mock_gen.side_effect = APIAuthenticationError("Invalid API key")

    payload = {"error_text": "TypeError: something failed"}
    response = client.post("/api/debug", json=payload)
    assert response.status_code == 401
    assert "authentication failed" in response.json()["detail"].lower()


@patch("app.api.server.generate_response_with_metrics")
def test_api_debug_rate_limit_error(mock_gen):
    """Verify rate limit error maps to HTTP 429."""
    mock_gen.side_effect = APIQuotaExceededError("Quota exceeded")

    payload = {"error_text": "TypeError: something failed"}
    response = client.post("/api/debug", json=payload)
    assert response.status_code == 429
    assert "rate limit or quota" in response.json()["detail"].lower()


@patch("app.api.server.generate_response_with_metrics")
def test_api_debug_timeout_error(mock_gen):
    """Verify timeout error maps to HTTP 504."""
    mock_gen.side_effect = APITimeoutError("Deadline exceeded")

    payload = {"error_text": "TypeError: something failed"}
    response = client.post("/api/debug", json=payload)
    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()


@patch("app.api.server.generate_response_with_metrics")
def test_api_debug_service_error(mock_gen):
    """Verify server error maps to HTTP 503."""
    mock_gen.side_effect = APIServiceError("Service unavailable")

    payload = {"error_text": "TypeError: something failed"}
    response = client.post("/api/debug", json=payload)
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"].lower()


# ==========================================
# 4. Streaming Endpoint Execution (SSE)
# ==========================================


@patch("app.api.server.generate_response_stream")
def test_api_debug_stream_endpoint(mock_stream_gen):
    """Verify Server-Sent Events stream yields frames."""
    report = DebuggingReport.model_validate(SAMPLE_REPORT_DICT)
    events = [
        StreamEvent(event_type="start", data={"request_id": "req-stream"}),
        StreamEvent(event_type="text_chunk", data={"delta": "Hello"}),
        StreamEvent(event_type="completed", data={"raw_text": "Hello", "report": report}),
    ]
    mock_stream_gen.return_value = iter(events)

    payload = {"error_text": "TypeError: something broke"}
    response = client.post("/api/debug/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    content = response.text
    assert "event: start" in content
    assert "event: text_chunk" in content
    assert "event: completed" in content


# ==========================================
# 5. Security & CORS Headers
# ==========================================


def test_cors_options_preflight():
    """Verify CORS preflight headers on API routes."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/api/debug", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
