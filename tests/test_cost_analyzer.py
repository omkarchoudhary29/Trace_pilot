"""
Tests for Phase 5.7 Token Usage and Cost Analysis.
"""

from experiments.cost_analyzer import (
    PRICING_REGISTRY,
    analyze_token_usage_and_costs,
    calculate_request_cost,
    get_model_pricing,
)


def test_get_model_pricing():
    assert "gemini-3.5-flash-lite" in PRICING_REGISTRY
    assert "gemini-3.5-flash" in PRICING_REGISTRY
    lite_pricing = get_model_pricing("gemini-3.5-flash-lite")
    assert lite_pricing is not None
    assert lite_pricing["input_cost_per_million"] == 0.075
    assert lite_pricing["output_cost_per_million"] == 0.30
    assert lite_pricing["is_verified"] is True

    unknown_pricing = get_model_pricing("unknown-custom-model")
    assert unknown_pricing is None


def test_calculate_request_cost_verified():
    # 10,000 prompt tokens and 5,000 response tokens on flash-lite
    # Input cost: (10,000 / 1M) * 0.075 = $0.00075
    # Output cost: (5,000 / 1M) * 0.30 = $0.0015
    # Total: $0.00225
    cost = calculate_request_cost("gemini-3.5-flash-lite", 10_000, 5_000)
    assert cost["pricing_available"] is True
    assert cost["estimated_prompt_cost_usd"] == 0.00075
    assert cost["estimated_response_cost_usd"] == 0.0015
    assert cost["estimated_total_cost_usd"] == 0.00225


def test_calculate_request_cost_unverified_model():
    cost = calculate_request_cost("unregistered-model", 1000, 500)
    assert cost["pricing_available"] is False
    assert cost["estimated_total_cost_usd"] is None
    assert "Pricing unverified" in cost["disclaimer"]


def test_analyze_token_usage_and_costs():
    mock_runs = [
        {
            "model_name": "gemini-3.5-flash-lite",
            "success": True,
            "prompt_tokens": 500,
            "response_tokens": 500,
            "total_tokens": 1000,
            "execution_time_sec": 0.5,
        },
        {
            "model_name": "gemini-3.5-flash-lite",
            "success": True,
            "prompt_tokens": 1000,
            "response_tokens": 500,
            "total_tokens": 1500,
            "execution_time_sec": 0.7,
        },
        {
            "model_name": "gemini-3.5-flash",
            "success": True,
            "prompt_tokens": 500,
            "response_tokens": 1000,
            "total_tokens": 1500,
            "execution_time_sec": 1.2,
        },
    ]

    summary = analyze_token_usage_and_costs(mock_runs, save_results=False)
    assert summary["total_requests_analyzed"] == 3
    assert summary["total_prompt_tokens"] == 2000
    assert summary["total_response_tokens"] == 2000
    assert summary["total_tokens"] == 4000
    assert summary["avg_tokens_per_request"] == 1333.3

    breakdown = summary["model_breakdown"]
    assert "gemini-3.5-flash-lite" in breakdown
    assert "gemini-3.5-flash" in breakdown
    assert breakdown["gemini-3.5-flash-lite"]["total_requests"] == 2
    assert breakdown["gemini-3.5-flash-lite"]["total_tokens"] == 2500
    assert breakdown["gemini-3.5-flash"]["total_tokens"] == 1500
    assert summary["total_estimated_cost_usd"] is not None
