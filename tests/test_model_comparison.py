"""
Tests for Phase 5.4 Model Comparison Lab.
"""

from unittest.mock import patch

from experiments.model_comparison import (
    aggregate_comparison_metrics,
    parse_debugging_sections,
    run_model_comparison,
)


def test_parse_debugging_sections():
    sample_text = """
### 1. Error Classification
TypeError: unsupported operand type

### 2. Likely Root Cause
Attempting to add string and int.

### 3. Debugging Recommendations
Convert string to int using int(tax_rate).

### 4. Verification
Run calculation with valid integer values.
"""
    parsed = parse_debugging_sections(sample_text)
    assert parsed["classification"] is not None
    assert "TypeError" in parsed["classification"]
    assert parsed["root_cause"] is not None
    assert "Attempting to add" in parsed["root_cause"]
    assert parsed["debugging_recommendations"] is not None
    assert parsed["verification_steps"] is not None


def test_parse_debugging_sections_empty():
    parsed = parse_debugging_sections("")
    assert parsed["classification"] is None
    assert parsed["root_cause"] is None


def test_aggregate_comparison_metrics():
    sample_runs = [
        {
            "model_name": "gemini-3.5-flash-lite",
            "success": True,
            "execution_time_sec": 1.2,
            "prompt_tokens": 100,
            "response_tokens": 200,
            "total_tokens": 300,
        },
        {
            "model_name": "gemini-3.5-flash-lite",
            "success": True,
            "execution_time_sec": 0.8,
            "prompt_tokens": 100,
            "response_tokens": 150,
            "total_tokens": 250,
        },
        {
            "model_name": "gemini-3.5-flash",
            "success": False,
            "execution_time_sec": 2.5,
            "prompt_tokens": None,
            "response_tokens": None,
            "total_tokens": None,
        },
    ]

    summary = aggregate_comparison_metrics(
        sample_runs, ["gemini-3.5-flash-lite", "gemini-3.5-flash"]
    )

    lite = summary["gemini-3.5-flash-lite"]
    assert lite["total_requests"] == 2
    assert lite["successful_requests"] == 2
    assert lite["success_rate_pct"] == 100.0
    assert lite["avg_latency_sec"] == 1.0
    assert lite["avg_total_tokens"] == 275.0

    flash = summary["gemini-3.5-flash"]
    assert flash["total_requests"] == 1
    assert flash["successful_requests"] == 0
    assert flash["success_rate_pct"] == 0.0


@patch("experiments.model_comparison.execute_single_model")
def test_run_model_comparison_flow(mock_execute):
    mock_execute.return_value = {
        "model": "mock-model",
        "success": True,
        "text": "Classification: TypeError\nRoot cause: Invalid type",
        "execution_time": 0.45,
        "finish_reason": "STOP",
        "prompt_tokens": 50,
        "response_tokens": 80,
        "total_tokens": 130,
        "is_complete": True,
        "was_truncated": False,
        "metadata": {"finish_reason": "STOP"},
        "error": None,
    }

    test_case = [
        {
            "id": "TEST-01",
            "category": "Test",
            "title": "Mock Error",
            "error_text": "TypeError: mock error",
        }
    ]

    result = run_model_comparison(
        benchmark_cases=test_case,
        primary_model="gemini-3.5-flash-lite",
        fallback_model="gemini-3.5-flash",
        save_results=False,
    )

    assert result["total_runs"] == 2
    assert mock_execute.call_count == 2
    models_called = [call.kwargs["model"] for call in mock_execute.call_args_list]
    assert "gemini-3.5-flash-lite" in models_called
    assert "gemini-3.5-flash" in models_called

