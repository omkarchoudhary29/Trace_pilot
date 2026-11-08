"""
Tests for Phase 8: Streaming and Usage Engine.

Covers:
- Incremental streaming of text chunks in order.
- Handling empty and None chunks.
- StreamEvent event structure (start, text_chunk, completed, failed).
- Latency calculations (TTFC, streaming duration, fallback duration, total duration).
- Token usage extraction and Phase 5 cost analyzer integration (no fake costs).
- Recoverable stream failure triggers fallback model with full buffer discard (no mixing).
- Non-recoverable failure (auth / invalid request) aborts immediately without fallback.
- Both models failing raises TracePilotAPIError.
- Post-stream Pydantic validation into DebuggingReport (never mid-stream).
- run_tracepilot streaming mode integration with on_chunk callback.
- generate_response_with_metrics non-streaming telemetry.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors

from app.llm.api_handler import generate_response_with_metrics
from app.llm.exceptions import (
    APIAuthenticationError,
    APIResponseTruncatedError,
    StructuredReportError,
    TracePilotAPIError,
)
from app.llm.streaming import (
    RequestUsageMetrics,
    StreamEvent,
    generate_response_stream,
)
from app.main import run_tracepilot
from app.schemas.debugging_report import DebuggingReport


def _create_mock_chunk(text=None, finish_reason=None, usage=None):
    """Helper to build a simulated GenerateContentResponse chunk."""
    chunk = MagicMock()
    chunk.text = text

    if finish_reason is not None:
        cand = MagicMock()
        cand.finish_reason = finish_reason
        chunk.candidates = [cand]
    else:
        chunk.candidates = []

    if usage:
        um = MagicMock()
        um.prompt_token_count = usage.get("prompt_tokens")
        um.candidates_token_count = usage.get("response_tokens")
        um.total_token_count = usage.get("total_tokens")
        chunk.usage_metadata = um
    else:
        chunk.usage_metadata = None

    return chunk


VALID_REPORT_DICT = {
    "error_information": {
        "error_type": "ZeroDivisionError",
        "error_message": "division by zero",
        "programming_language": "Python",
        "severity": "high",
        "category": "runtime",
        "filename": "calc.py",
        "line_number": 12,
        "function_name": "divide",
    },
    "error_summary": {
        "short_description": "Division by zero occurred in calc.py.",
        "failed_operation": "Binary float division.",
        "plain_language_explanation": "The denominator passed to divide was zero.",
    },
    "evidence": {
        "error_message_excerpts": ["ZeroDivisionError: division by zero"],
        "traceback_or_log_excerpts": ["File calc.py, line 12 in divide"],
        "extracted_file_and_line": "calc.py:12",
        "observed_facts": ["line 12 executed divide"],
        "inferred_information": ["argument b was 0"],
    },
    "root_cause_analysis": {
        "primary_hypothesis": {
            "hypothesis": "Zero passed as denominator without check.",
            "supporting_evidence": ["Traceback points to divide function"],
            "confidence": "high",
        },
        "alternative_hypotheses": [
            {
                "hypothesis": "Invalid user input cast to zero.",
                "supporting_evidence": [],
                "confidence": "low",
            }
        ],
        "missing_information_to_confirm": ["Where b is defined and assigned."],
    },
    "debugging_steps": [
        {
            "step_number": 1,
            "action": "Check divisor value before division.",
            "why_recommended": "Prevents ZeroDivisionError.",
            "relevant_evidence": "Line 12 in calc.py",
            "expected_outcome": "Controlled error or fallback.",
        }
    ],
    "suggested_fix": {
        "explanation": "Add zero check before division.",
        "code_example": "if b == 0: raise ValueError('cannot be zero')",
        "where_to_apply": "calc.py line 12",
        "assumptions_and_limitations": ["b is a numeric parameter."],
    },
    "verification": {
        "how_to_verify": "Run unit test with zero divisor.",
        "expected_behavior": "Raises ValueError instead of crash.",
        "suggested_test_cases": ["divide(10, 0) -> ValueError"],
        "if_error_persists": "Check if b is computed dynamically.",
    },
    "confidence_and_review": {
        "overall_confidence": "high",
        "human_review_required": False,
        "uncertainty_explanation": "Direct and standard runtime exception.",
    },
}

SAMPLE_VALID_REPORT_JSON = json.dumps(VALID_REPORT_DICT)


# ==========================================
# 1. Successful Streaming & Chunk Processing
# ==========================================


def test_streaming_success_accumulates_and_yields_events(monkeypatch):
    """Verify chunks are yielded incrementally and preserved in order."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    chunks = [
        _create_mock_chunk(text="Hello "),
        _create_mock_chunk(text="World!"),
        _create_mock_chunk(
            text=None,
            finish_reason="STOP",
            usage={"prompt_tokens": 15, "response_tokens": 10, "total_tokens": 25},
        ),
    ]

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = iter(chunks)

    events = list(generate_response_stream("Test prompt", custom_client=mock_client))

    event_types = [e.event_type for e in events]
    assert event_types == ["start", "text_chunk", "text_chunk", "completed"]

    assert events[0].data["model"] == "gemini-3.5-flash-lite"
    assert events[1].data["delta"] == "Hello "
    assert events[1].data["chunk_index"] == 0
    assert events[2].data["delta"] == "World!"
    assert events[2].data["chunk_index"] == 1

    completed_data = events[3].data
    assert completed_data["raw_text"] == "Hello World!"
    assert completed_data["model"] == "gemini-3.5-flash-lite"

    metrics = completed_data["metrics"]
    assert metrics["prompt_tokens"] == 15
    assert metrics["response_tokens"] == 10
    assert metrics["total_tokens"] == 25
    assert metrics["finish_reason"] == "STOP"
    assert metrics["is_complete"] is True
    assert metrics["was_truncated"] is False
    assert metrics["total_duration_seconds"] >= 0.0
    assert metrics["cost_estimate"] is not None
    assert metrics["cost_estimate"]["pricing_available"] is True


def test_streaming_handles_empty_and_none_chunks(monkeypatch):
    """Verify empty or None text chunks do not yield empty delta events."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    chunks = [
        _create_mock_chunk(text=""),
        _create_mock_chunk(text=None),
        _create_mock_chunk(text="ValidChunk"),
        _create_mock_chunk(text=None, finish_reason="STOP"),
    ]

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = iter(chunks)

    events = list(generate_response_stream("Test prompt", custom_client=mock_client))

    text_events = [e for e in events if e.event_type == "text_chunk"]
    assert len(text_events) == 1
    assert text_events[0].data["delta"] == "ValidChunk"
    assert events[-1].data["raw_text"] == "ValidChunk"


# ==========================================
# 2. Structured Output & Pydantic Validation
# ==========================================


def test_streaming_structured_output_validates_after_completion(monkeypatch):
    """Verify full JSON stream is validated with DebuggingReport upon completion."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    # Split JSON across 3 chunks
    part1 = SAMPLE_VALID_REPORT_JSON[:100]
    part2 = SAMPLE_VALID_REPORT_JSON[100:300]
    part3 = SAMPLE_VALID_REPORT_JSON[300:]

    chunks = [
        _create_mock_chunk(text=part1),
        _create_mock_chunk(text=part2),
        _create_mock_chunk(text=part3, finish_reason="STOP"),
    ]

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = iter(chunks)

    events = list(
        generate_response_stream(
            "Test prompt",
            response_schema=DebuggingReport,
            response_mime_type="application/json",
            custom_client=mock_client,
        )
    )

    completed_event = events[-1]
    assert completed_event.event_type == "completed"
    report = completed_event.data["report"]
    assert isinstance(report, DebuggingReport)
    assert report.error_information.error_type == "ZeroDivisionError"
    assert report.error_information.line_number == 12


def test_streaming_structured_output_invalid_json_raises(monkeypatch):
    """Verify invalid JSON raises StructuredReportError at end of stream."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    chunks = [
        _create_mock_chunk(text='{"error_information": { "broken": true }'),
        _create_mock_chunk(text=None, finish_reason="STOP"),
    ]

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = iter(chunks)

    with pytest.raises(StructuredReportError):
        list(
            generate_response_stream(
                "Test prompt",
                response_schema=DebuggingReport,
                custom_client=mock_client,
            )
        )


# ==========================================
# 3. Two-Model Fallback Policy
# ==========================================


def test_streaming_recoverable_failure_switches_to_fallback_with_buffer_reset(monkeypatch):
    """
    Verify recoverable primary stream failure discards partial primary chunks
    and starts fresh from fallback model without mixing output.
    """
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    def primary_generator():
        yield _create_mock_chunk(text="Partial primary chunk 1")
        yield _create_mock_chunk(text="Partial primary chunk 2")
        raise errors.ServerError(503, {"error": {"message": "Service unavailable"}})

    fallback_chunks = [
        _create_mock_chunk(text="Fresh fallback chunk 1"),
        _create_mock_chunk(text=" and chunk 2", finish_reason="STOP"),
    ]

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.side_effect = [
        primary_generator(),
        iter(fallback_chunks),
    ]

    events = list(generate_response_stream("Test prompt", custom_client=mock_client))

    # Fallback model must be called
    assert mock_client.models.generate_content_stream.call_count == 2
    second_call = mock_client.models.generate_content_stream.call_args_list[1]
    assert second_call.kwargs["model"] == "gemini-3.5-flash"

    completed = events[-1]
    assert completed.event_type == "completed"
    # Ensure partial primary text was discarded:
    assert completed.data["raw_text"] == "Fresh fallback chunk 1 and chunk 2"
    assert "Partial primary" not in completed.data["raw_text"]

    metrics = completed.data["metrics"]
    assert metrics["fallback_used"] is True
    assert metrics["model_used"] == "gemini-3.5-flash"
    assert metrics["fallback_duration_seconds"] is not None


def test_streaming_non_recoverable_failure_fails_fast_without_fallback(monkeypatch):
    """Verify authentication error aborts immediately and never calls fallback."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    def primary_generator():
        yield _create_mock_chunk(text="Unauthorized attempt")
        raise errors.ClientError(401, {"error": {"message": "Invalid API key"}})

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = primary_generator()

    with pytest.raises(APIAuthenticationError):
        list(generate_response_stream("Test prompt", custom_client=mock_client))

    # Exactly 1 model attempt (no fallback)
    assert mock_client.models.generate_content_stream.call_count == 1


def test_streaming_both_models_fail_raises_tracepilot_error(monkeypatch):
    """Verify that when both primary and fallback fail, a clear TracePilotAPIError is raised."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.side_effect = [
        errors.ServerError(500, {"error": {"message": "Primary 500"}}),
        errors.ServerError(503, {"error": {"message": "Fallback 503"}}),
    ]

    with pytest.raises(TracePilotAPIError, match="Both primary and fallback"):
        list(generate_response_stream("Test prompt", custom_client=mock_client))


def test_streaming_truncation_detection(monkeypatch):
    """Verify MAX_TOKENS finish reason raises APIResponseTruncatedError."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash-lite")  # Same model disables fallback

    chunks = [
        _create_mock_chunk(text="Long cut off output", finish_reason="MAX_TOKENS"),
    ]

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = iter(chunks)

    with pytest.raises(APIResponseTruncatedError):
        list(generate_response_stream("Test prompt", custom_client=mock_client))


# ==========================================
# 4. Latency & Cost Metrics Integration
# ==========================================


def test_streaming_missing_token_counts_handles_cleanly(monkeypatch):
    """Verify that when tokens are missing, no fake cost is fabricated."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    chunks = [
        _create_mock_chunk(text="Output without usage", finish_reason="STOP", usage=None),
    ]

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = iter(chunks)

    events = list(generate_response_stream("Test prompt", custom_client=mock_client))
    metrics = events[-1].data["metrics"]

    assert metrics["prompt_tokens"] is None
    assert metrics["response_tokens"] is None
    assert metrics["total_tokens"] is None
    assert metrics["cost_estimate"] is None  # Never fabricated


# ==========================================
# 5. Application Pipeline & Non-Streaming Integration
# ==========================================


@patch("app.main.generate_response_stream")
def test_run_tracepilot_stream_callback(mock_stream_gen):
    """Verify run_tracepilot streaming mode invokes callback and returns report."""
    fake_report = DebuggingReport.from_json(SAMPLE_VALID_REPORT_JSON)

    mock_stream_gen.return_value = iter(
        [
            StreamEvent(event_type="start", data={"request_id": "test-req"}),
            StreamEvent(event_type="text_chunk", data={"delta": "chunk1"}),
            StreamEvent(event_type="text_chunk", data={"delta": "chunk2"}),
            StreamEvent(
                event_type="completed",
                data={"raw_text": SAMPLE_VALID_REPORT_JSON, "report": fake_report},
            ),
        ]
    )

    accumulated = []
    result = run_tracepilot(
        "Traceback (most recent call last):\n  File 'a.py', line 1\nZeroDivisionError",
        structured=True,
        stream=True,
        on_chunk=accumulated.append,
    )

    assert accumulated == ["chunk1", "chunk2"]
    assert isinstance(result, DebuggingReport)
    assert result.error_information.error_type == "ZeroDivisionError"


@patch("app.llm.api_handler.create_gemini_client")
def test_generate_response_with_metrics_non_streaming(mock_create_client, monkeypatch):
    """Verify generate_response_with_metrics returns text and RequestUsageMetrics in non-streaming mode."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    mock_resp = MagicMock()
    mock_resp.text = "Non-streaming answer"
    cand = MagicMock()
    cand.finish_reason = "STOP"
    mock_resp.candidates = [cand]
    mock_resp.usage_metadata.prompt_token_count = 50
    mock_resp.usage_metadata.candidates_token_count = 25
    mock_resp.usage_metadata.total_token_count = 75

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp
    mock_create_client.return_value = mock_client

    text, metrics = generate_response_with_metrics("Test input")

    assert text == "Non-streaming answer"
    assert isinstance(metrics, RequestUsageMetrics)
    assert metrics.streaming is False
    assert metrics.model_used == "gemini-3.5-flash-lite"
    assert metrics.prompt_tokens == 50
    assert metrics.response_tokens == 25
    assert metrics.total_tokens == 75
    assert metrics.is_complete is True
    assert metrics.cost_estimate is not None
    assert metrics.cost_estimate["pricing_available"] is True
