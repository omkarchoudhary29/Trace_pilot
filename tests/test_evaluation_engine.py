"""
Tests for Phase 9: Debugging Evaluation Engine.

Covers:
- Benchmark dataset validation (unique IDs, required fields, enum adherence).
- Metric calculations (Accuracy, Precision, Recall, Macro-F1, Sample Sizes).
- Evidence grounding and hallucinated / invented location detection.
- Schema validity checking for DebuggingReport instances, dicts, and invalid structures.
- Single case evaluation against ground truth.
- Multi-case aggregate metric computation.
- Benchmark evaluation flow across models with token usage and cost estimation.
- Optional LLM-assisted evaluation (verified as segregated and advisory).
- Human evaluation recording and rubric enforcement.
- Markdown report generation.
"""

from app.schemas.debugging_report import (
    DebuggingReport,
    ErrorCategory,
    Severity,
)
from data.benchmark_inputs import BENCHMARK_INPUTS, get_benchmark_by_id
from experiments.evaluation_engine import (
    compute_aggregate_evaluation_metrics,
    evaluate_single_case,
    generate_evaluation_report,
    run_benchmark_evaluation,
    run_llm_assisted_eval,
)
from experiments.quality_evaluator import (
    calculate_precision_recall_f1,
    evaluate_evidence_grounding,
    evaluate_schema_validity,
    record_human_evaluation,
)

SAMPLE_VALID_REPORT_DICT = {
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
        "failed_operation": "addition",
        "plain_language_explanation": "Cannot add string to integer without casting.",
    },
    "evidence": {
        "error_message_excerpts": ["unsupported operand type(s) for +: 'int' and 'str'"],
        "traceback_or_log_excerpts": ["File calculator.py, line 18 in calculate_total"],
        "extracted_file_and_line": "calculator.py:18",
        "observed_facts": ["subtotal is int", "tax_rate is str"],
        "inferred_information": ["tax_rate was loaded as string"],
    },
    "root_cause_analysis": {
        "primary_hypothesis": {
            "hypothesis": "Adding integer subtotal and string tax_rate without explicit type casting",
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
            "why_recommended": "Converts string to numeric type",
            "relevant_evidence": "calculator.py:18",
            "expected_outcome": "Addition succeeds",
        }
    ],
    "suggested_fix": {
        "explanation": "Cast tax_rate before summing",
        "code_example": "return subtotal + float(tax_rate)",
        "where_to_apply": "calculator.py line 18",
        "assumptions_and_limitations": ["tax_rate is numeric"],
    },
    "verification": {
        "how_to_verify": "Run calculate_total with subtotal=100 and tax_rate='0.05'",
        "expected_behavior": "Returns 100.05",
        "suggested_test_cases": ["calculate_total(100, '0.05')"],
        "if_error_persists": "Check if string contains non-numeric chars",
    },
    "confidence_and_review": {
        "overall_confidence": "high",
        "human_review_required": False,
        "uncertainty_explanation": "Explicit and standard exception",
    },
}


# ==========================================
# 1. Benchmark Dataset Validation
# ==========================================


def test_benchmark_inputs_unique_ids_and_required_fields():
    """Verify all benchmark entries have unique IDs and complete required fields."""
    seen_ids = set()
    valid_categories = {c.value for c in ErrorCategory}
    valid_severities = {s.value for s in Severity}

    assert len(BENCHMARK_INPUTS) >= 5

    for case in BENCHMARK_INPUTS:
        case_id = case.get("id")
        assert case_id is not None
        assert case_id not in seen_ids, f"Duplicate ID found: {case_id}"
        seen_ids.add(case_id)

        # Check required fields
        assert "title" in case
        assert "error_text" in case and len(case["error_text"].strip()) > 0
        assert "expected_classification" in case
        assert "known_evidence" in case and isinstance(case["known_evidence"], list)
        assert "known_root_causes" in case and isinstance(case["known_root_causes"], list)
        assert "expected_debugging_direction" in case
        assert "verification_criteria" in case
        assert "is_synthetic" in case and isinstance(case["is_synthetic"], bool)

        # Check enums
        assert case["category"] in valid_categories, f"Invalid category {case['category']} in {case_id}"
        assert case["severity"] in valid_severities, f"Invalid severity {case['severity']} in {case_id}"


def test_get_benchmark_by_id():
    """Verify lookup helper finds cases or returns None."""
    case = get_benchmark_by_id("CASE-PY-01")
    assert case is not None
    assert case["expected_classification"] == "TypeError"

    missing = get_benchmark_by_id("NONEXISTENT-CASE")
    assert missing is None


# ==========================================
# 2. Metric Calculations (Precision, Recall, F1)
# ==========================================


def test_calculate_precision_recall_f1_perfect_match():
    """Verify perfect predictions yield 1.0 accuracy, precision, recall, and F1."""
    y_true = ["runtime", "database", "authentication"]
    y_pred = ["runtime", "database", "authentication"]

    metrics = calculate_precision_recall_f1(y_true, y_pred)
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_precision"] == 1.0
    assert metrics["macro_recall"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["sample_size"] == 3


def test_calculate_precision_recall_f1_imperfect_match():
    """Verify precision, recall, and F1 calculation with classification errors."""
    y_true = ["runtime", "runtime", "database", "database"]
    y_pred = ["runtime", "database", "database", "database"]

    metrics = calculate_precision_recall_f1(y_true, y_pred)
    assert metrics["accuracy"] == 0.75
    assert metrics["sample_size"] == 4
    # runtime: tp=1, fp=0, fn=1 -> prec=1.0, rec=0.5, f1=0.6667
    assert metrics["per_class"]["runtime"]["precision"] == 1.0
    assert metrics["per_class"]["runtime"]["recall"] == 0.5


def test_calculate_precision_recall_f1_empty():
    """Verify empty input handling reports zero metrics without crash."""
    metrics = calculate_precision_recall_f1([], [])
    assert metrics["sample_size"] == 0
    assert metrics["accuracy"] == 0.0
    assert metrics["macro_f1"] == 0.0


# ==========================================
# 3. Evidence Grounding & Hallucinations
# ==========================================


def test_evaluate_evidence_grounding_valid_grounding():
    """Verify evidence grounding gives high score when cited file and line exist in input."""
    raw_error = 'File "calculator.py", line 18, in calculate_total'
    report = {"error_information": {"filename": "calculator.py", "line_number": 18}}
    known_evidence = ["calculator.py", "18"]

    result = evaluate_evidence_grounding(report, raw_error, known_evidence)
    assert result["grounding_score"] == 5.0
    assert result["file_grounded"] is True
    assert result["line_grounded"] is True
    assert len(result["invented_locations"]) == 0
    assert result["evidence_recall"] == 1.0


def test_evaluate_evidence_grounding_detects_invented_locations():
    """Verify invented filename or line number is flagged as hallucinated location."""
    raw_error = 'File "calculator.py", line 18, in calculate_total'
    report = {"error_information": {"filename": "invented_script.py", "line_number": 999}}

    result = evaluate_evidence_grounding(report, raw_error)
    assert result["file_grounded"] is False
    assert result["line_grounded"] is False
    assert "filename:invented_script.py" in result["invented_locations"]
    assert "line:999" in result["invented_locations"]
    assert result["grounding_score"] == 2.0  # Penalized


# ==========================================
# 4. Schema Validity Evaluation
# ==========================================


def test_evaluate_schema_validity():
    """Verify schema validity checks accept valid reports and reject invalid dicts."""
    valid_report = DebuggingReport.model_validate(SAMPLE_VALID_REPORT_DICT)
    assert evaluate_schema_validity(valid_report)["is_schema_valid"] is True
    assert evaluate_schema_validity(SAMPLE_VALID_REPORT_DICT)["is_schema_valid"] is True

    # Invalid dict missing required fields
    invalid_dict = {"error_information": {"broken": True}}
    eval_invalid = evaluate_schema_validity(invalid_dict)
    assert eval_invalid["is_schema_valid"] is False
    assert eval_invalid["error"] is not None


# ==========================================
# 5. Single Case Evaluation
# ==========================================


def test_evaluate_single_case_matching():
    """Verify evaluate_single_case matches ground truth and computes scores."""
    case = get_benchmark_by_id("CASE-PY-01")
    report = DebuggingReport.model_validate(SAMPLE_VALID_REPORT_DICT)

    result = evaluate_single_case(
        case=case,
        model_output=report,
        latency_seconds=1.23,
        usage={"prompt_tokens": 100, "response_tokens": 50},
    )

    assert result["case_id"] == "CASE-PY-01"
    assert result["is_schema_valid"] is True
    assert result["classification_matches"]["type_match"] is True
    assert result["classification_matches"]["category_match"] is True
    assert result["classification_matches"]["severity_match"] is True
    assert result["root_cause_grounded"] is True
    assert result["has_unsupported_claims"] is False
    assert result["latency_seconds"] == 1.23


# ==========================================
# 6. Aggregate Benchmark Evaluation & Reporting
# ==========================================


def test_run_benchmark_evaluation_and_report_generation():
    """Verify run_benchmark_evaluation processes multiple cases and generates Markdown report."""
    case_py = get_benchmark_by_id("CASE-PY-01")
    report = DebuggingReport.model_validate(SAMPLE_VALID_REPORT_DICT)

    runs = {
        "gemini-3.5-flash-lite": [
            {
                "case_id": "CASE-PY-01",
                "report": report,
                "latency_seconds": 0.85,
                "usage": {"prompt_tokens": 120, "response_tokens": 80},
            }
        ],
        "gemini-3.5-flash": [
            {
                "case_id": "CASE-PY-01",
                "report": report,
                "latency_seconds": 1.45,
                "usage": {"prompt_tokens": 120, "response_tokens": 90},
            }
        ],
    }

    eval_result = run_benchmark_evaluation(
        benchmark_cases=[case_py],
        runs_by_model=runs,
        save_results=True,
    )

    assert eval_result["benchmark_size"] == 1
    assert "gemini-3.5-flash-lite" in eval_result["model_results"]
    assert "gemini-3.5-flash" in eval_result["model_results"]

    lite_metrics = eval_result["model_results"]["gemini-3.5-flash-lite"]["metrics"]
    assert lite_metrics["schema_validation_rate"] == 1.0
    assert lite_metrics["type_accuracy"] == 1.0
    assert lite_metrics["latency_stats"]["mean_seconds"] == 0.85

    cost = eval_result["model_results"]["gemini-3.5-flash-lite"]["cost_estimate"]
    assert cost is not None
    assert cost["pricing_available"] is True

    # Generate Markdown Report
    human_evals = [
        record_human_evaluation(
            evaluator_name="Lead Reviewer",
            scores={dim: 4.5 for dim in ["classification_correctness", "root_cause_accuracy", "evidence_based_reasoning", "debugging_recommendation_relevance", "technical_correctness", "completeness", "clarity", "unsupported_claims_absence", "safety_and_uncertainty"]},
            comments="Clear, verified, actionable diagnosis.",
        )
    ]

    report_md = generate_evaluation_report(eval_result, human_evaluations=human_evals, save_file=True)
    assert "# TracePilot — Phase 9: Debugging Evaluation Engine Report" in report_md
    assert "gemini-3.5-flash-lite" in report_md
    assert "Lead Reviewer" in report_md


# ==========================================
# 7. LLM-Assisted Evaluation (Segregation Check)
# ==========================================


def test_run_llm_assisted_eval_segregation():
    """Verify LLM-assisted evaluation is clearly designated as advisory and not ground truth."""
    case = get_benchmark_by_id("CASE-PY-01")
    eval_res = run_llm_assisted_eval(
        report_text="Diagnostic output",
        ground_truth_case=case,
        judge_model="gemini-3.5-flash",
    )

    assert eval_res["evaluation_method"] == "llm_assisted"
    assert eval_res["judge_model"] == "gemini-3.5-flash"
    assert "scores" in eval_res
    assert "disclaimer" in eval_res
    assert "separate from objective ground-truth" in eval_res["disclaimer"]


def test_compute_aggregate_evaluation_metrics_empty():
    """Verify aggregate evaluation metrics handles empty case evaluations gracefully."""
    metrics = compute_aggregate_evaluation_metrics([])
    assert metrics["sample_size"] == 0
    assert metrics["schema_validation_rate"] == 0.0
    assert metrics["type_accuracy"] == 0.0
    assert metrics["category_metrics"] == {}

