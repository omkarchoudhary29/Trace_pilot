"""
Tests for Phase 5.5 Parameter Combination Experiments.
"""

from unittest.mock import patch

from experiments.parameter_grid import (
    COMBINATION_CONFIGS,
    ISOLATED_CONFIGS,
    check_parameter_support,
    run_parameter_experiments,
)


def test_isolated_and_combination_config_definitions():
    assert "temperature" in ISOLATED_CONFIGS
    assert "top_p" in ISOLATED_CONFIGS
    assert "top_k" in ISOLATED_CONFIGS
    assert "max_tokens" in ISOLATED_CONFIGS

    for configs in ISOLATED_CONFIGS.values():
        assert len(configs) >= 3
        for c in configs:
            assert 0.0 <= c["temperature"] <= 2.0
            assert 0.0 < c["top_p"] <= 1.0
            assert c["max_output_tokens"] > 0

    assert len(COMBINATION_CONFIGS) >= 3
    for c in COMBINATION_CONFIGS:
        assert "name" in c
        assert 0.0 <= c["temperature"] <= 2.0


def test_check_parameter_support():
    config = {"temperature": 0.2, "top_p": 0.9, "top_k": 40, "max_output_tokens": 64}
    support = check_parameter_support("gemini-3.5-flash", config)

    assert support["supports_temperature"] is True
    assert support["supports_top_p"] is True
    assert support["supports_top_k"] is True
    assert len(support["notes"]) == 2  # Top-K note + low token budget note


@patch("experiments.parameter_grid.execute_single_model")
def test_run_parameter_experiments_mocked(mock_execute):
    mock_execute.return_value = {
        "model": "gemini-3.5-flash-lite",
        "success": True,
        "text": "Analysis with test parameter config",
        "execution_time": 0.25,
        "finish_reason": "STOP",
        "prompt_tokens": 40,
        "response_tokens": 60,
        "total_tokens": 100,
        "is_complete": True,
        "was_truncated": False,
        "metadata": {"finish_reason": "STOP"},
        "error": None,
    }

    test_case = {
        "id": "PARAM-TEST-01",
        "error_text": "ValueError: invalid parameter test",
    }

    result = run_parameter_experiments(
        benchmark_case=test_case,
        models=["gemini-3.5-flash-lite"],
        include_isolated=False,
        include_combinations=True,
        save_results=False,
    )

    assert result["total_runs"] == len(COMBINATION_CONFIGS)
    assert mock_execute.call_count == len(COMBINATION_CONFIGS)
    first_run = result["runs"][0]
    assert first_run["success"] is True
    assert first_run["model_name"] == "gemini-3.5-flash-lite"
    assert first_run["finish_reason"] == "STOP"
