"""
Tests for Phase 5.6 Output Quality Evaluation Framework.
"""

import pytest

from experiments.quality_evaluator import (
    EVALUATION_DIMENSIONS,
    evaluate_response_objectively,
    evaluate_runs,
    record_human_evaluation,
    score_classification_correctness,
    score_completeness,
    score_unsupported_claims,
)


def test_score_classification_correctness():
    assert score_classification_correctness("Classification: TypeError", "TypeError") == 5.0
    body_mention = "Overview line 1\nOverview line 2\nLater in body TypeError occurs here"
    assert score_classification_correctness(body_mention, "TypeError") == 4.0
    assert score_classification_correctness("Something completely unrelated happened", "TypeError") == 1.0
    assert score_classification_correctness("", "TypeError") == 1.0


def test_score_completeness():
    full_text = """
Classification: ZeroDivisionError
Root cause: Division by zero.
Debugging: Check denominator.
Verification: Assert non-zero denominator.
"""
    assert score_completeness(full_text) == 5.0

    partial_text = "Classification: ZeroDivisionError"
    assert score_completeness(partial_text) == 2.0


def test_score_unsupported_claims():
    clean_text = "The error indicates that the file was not found."
    assert score_unsupported_claims(clean_text) == 5.0

    hallucinated_text = "I ran the code on your machine and confirmed the error."
    assert score_unsupported_claims(hallucinated_text) == 1.0


def test_evaluate_response_objectively_none():
    res = evaluate_response_objectively(None, None)
    assert res["aggregate_score"] == 1.0
    assert res["classification_correctness"] == 1.0


def test_record_human_evaluation_valid_and_invalid():
    scores = {dim: 4.0 for dim in EVALUATION_DIMENSIONS}
    rec = record_human_evaluation("Senior Reviewer", scores, comments="Strong reasoning")
    assert rec["evaluator"] == "Senior Reviewer"
    assert rec["aggregate_score"] == 4.0

    with pytest.raises(ValueError, match="must be between 1.0 and 5.0"):
        record_human_evaluation("Reviewer", {**scores, "clarity": 6.5})

    with pytest.raises(ValueError, match="Unknown evaluation dimension"):
        record_human_evaluation("Reviewer", {**scores, "unrecognized_dim": 3.0})


def test_evaluate_runs_aggregation():
    benchmark_cases = [
        {
            "id": "CASE-01",
            "expected_classification": "TypeError",
            "expected_keywords": ["operand", "integer"],
        }
    ]

    mock_runs = [
        {
            "input_id": "CASE-01",
            "model_name": "gemini-3.5-flash-lite",
            "generated_response": (
                "Classification: TypeError\nLikely cause: operand type mismatch with integer.\n"
                "Debugging: cast types.\nVerification: re-run."
            ),
        },
        {
            "input_id": "CASE-01",
            "model_name": "gemini-3.5-flash",
            "generated_response": (
                "Classification: TypeError\nLikely cause: integer operand issue.\n"
                "Debugging: fix code.\nVerification: test."
            ),
        },
    ]

    result = evaluate_runs(mock_runs, benchmark_cases, save_results=False)
    assert result["total_evaluated_runs"] == 2
    assert "gemini-3.5-flash-lite" in result["model_analysis"]
    assert "gemini-3.5-flash" in result["model_analysis"]

    lite_score = result["model_analysis"]["gemini-3.5-flash-lite"]["overall_quality_score"]
    assert 1.0 <= lite_score <= 5.0
