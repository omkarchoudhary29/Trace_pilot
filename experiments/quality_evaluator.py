"""
Phase 5.6: Output Quality Evaluation Framework.

Provides a systematic 1-5 evaluation rubric and scoring engine to assess
debugging response quality across 9 dimensions, combining objective checks
against benchmark ground truth with human evaluation support.
"""

import json
import re
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
QUALITY_RESULTS_FILE = OUTPUT_DIR / "quality_evaluation_results.json"

EVALUATION_DIMENSIONS = [
    "classification_correctness",
    "root_cause_accuracy",
    "evidence_based_reasoning",
    "debugging_recommendation_relevance",
    "technical_correctness",
    "completeness",
    "clarity",
    "unsupported_claims_absence",
    "safety_and_uncertainty",
]

EVALUATION_RUBRIC = {
    "classification_correctness": {
        "description": "Accuracy of the identified error or exception class.",
        "scale": {
            1: "Incorrect or missing classification.",
            3: "Partially correct or generic error family identified.",
            5: "Precise, exact exception classification matching ground truth.",
        },
    },
    "root_cause_accuracy": {
        "description": "Correct identification of the underlying reason for failure.",
        "scale": {
            1: "Completely erroneous root cause.",
            3: "Plausible general cause, but misses specific contextual triggers.",
            5: "Accurate, specific root cause directly explaining the observed failure.",
        },
    },
    "evidence_based_reasoning": {
        "description": "Direct grounding in filenames, lines, and tokens from input trace.",
        "scale": {
            1: "No reference to input evidence or references fabricated files/lines.",
            3: "Cites some input data but draws loose conclusions.",
            5: "Meticulously cites trace lines, variables, and error message text.",
        },
    },
    "debugging_recommendation_relevance": {
        "description": "Actionability and appropriateness of recommended steps.",
        "scale": {
            1: "Generic or destructive recommendations.",
            3: "Reasonable advice but requires developer to guess specifics.",
            5: "Direct, step-by-step actionable recommendations with safe commands/code.",
        },
    },
    "technical_correctness": {
        "description": "Soundness of underlying programming concepts.",
        "scale": {
            1: "Technically flawed explanation violating language semantics.",
            3: "Mostly accurate with minor imprecision.",
            5: "Flawless technical precision adhering to official runtime semantics.",
        },
    },
    "completeness": {
        "description": "Coverage of classification, root cause, recommendations, and verification.",
        "scale": {
            1: "Major required sections missing.",
            3: "Covers diagnosis and fix, but omits verification or evidence.",
            5: "Comprehensive coverage of all required sections.",
        },
    },
    "clarity": {
        "description": "Readability, structured formatting, and concise tone.",
        "scale": {
            1: "Disorganized, hard to parse, or excessively verbose.",
            3: "Readable with basic headings, moderate verbosity.",
            5: "Clear structure, bullet points, concise explanations.",
        },
    },
    "unsupported_claims_absence": {
        "description": "Absence of hallucinations (e.g. claiming to have executed the code).",
        "scale": {
            1: "Claims to have run code, accessed user server, or invents files.",
            3: "No false execution claims, but makes unstated assumptions.",
            5: "Strict adherence to available evidence with zero hallucinations.",
        },
    },
    "safety_and_uncertainty": {
        "description": "Communication of uncertainty and safe credential handling.",
        "scale": {
            1: "Asserts unverified guesses as absolute facts or recommends insecure actions.",
            3: "Mentions hypotheses but sometimes speaks with unjustified certainty.",
            5: "Clearly distinguishes observed facts from hypotheses; promotes safe practices.",
        },
    },
}

FORBIDDEN_EXECUTION_PHRASES = [
    r"i executed",
    r"i have executed",
    r"i ran the code",
    r"i accessed your",
    r"i logged into",
    r"i tested this on your server",
]


def score_classification_correctness(response_text: str, expected_classification: str | None) -> float:
    """Score classification accuracy against ground truth (1.0 - 5.0)."""
    if not response_text or not expected_classification:
        return 1.0

    target = expected_classification.lower().strip()
    text = response_text.lower()

    # Prominent match under classification header or first two lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    first_two_lines = " ".join(lines[:2]) if lines else ""

    if re.search(rf"(?:classification|error\s*type)[:\s]+[^\n]*{re.escape(target)}", text) or target in first_two_lines:
        return 5.0

    if target in text:
        return 4.0

    # Partial / keyword match
    words = [w for w in target.split() if len(w) > 3]
    if words and any(w in text for w in words):
        return 3.0

    return 1.0


def score_evidence_and_root_cause(
    response_text: str,
    expected_keywords: list[str] | None,
) -> tuple[float, float]:
    """Score evidence grounding and root cause accuracy via keyword coverage."""
    if not response_text or not expected_keywords:
        return 2.5, 2.5

    text = response_text.lower()
    matches = sum(1 for kw in expected_keywords if kw.lower() in text)
    ratio = matches / len(expected_keywords)

    if ratio >= 0.7:
        rc_score = 5.0
        ev_score = 4.8
    elif ratio >= 0.4:
        rc_score = 3.5
        ev_score = 3.5
    elif ratio > 0.0:
        rc_score = 2.5
        ev_score = 2.5
    else:
        rc_score = 1.0
        ev_score = 1.0

    return round(rc_score, 1), round(ev_score, 1)


def score_completeness(response_text: str) -> float:
    """Score section completeness across 4 major dimensions."""
    if not response_text:
        return 1.0

    sections = [
        r"(?:classification|error type)",
        r"(?:root cause|likely cause|explanation)",
        r"(?:debugging|recommendation|fix)",
        r"(?:verification|verify)",
    ]
    present = sum(1 for p in sections if re.search(p, response_text, re.IGNORECASE))

    scores = {4: 5.0, 3: 4.0, 2: 3.0, 1: 2.0, 0: 1.0}
    return scores.get(present, 1.0)


def score_unsupported_claims(response_text: str) -> float:
    """Check for hallucinations or false execution claims."""
    if not response_text:
        return 1.0

    for phrase in FORBIDDEN_EXECUTION_PHRASES:
        if re.search(phrase, response_text, re.IGNORECASE):
            return 1.0
    return 5.0


def score_safety_and_uncertainty(response_text: str) -> float:
    """Check if the response uses appropriate hedging or hypothesis language."""
    if not response_text:
        return 1.0

    hypothesis_markers = [
        "likely",
        "possible",
        "hypothes",
        "might",
        "could",
        "verify",
        "suggest",
    ]
    has_hedging = any(m in response_text.lower() for m in hypothesis_markers)
    return 4.5 if has_hedging else 3.0


def evaluate_response_objectively(response_text: str | None, benchmark_case: dict | None) -> dict:
    """
    Run automated heuristic scoring across standard dimensions.
    Returns individual scores on a 1-5 scale and an aggregate mean.
    """
    if not response_text:
        return {dim: 1.0 for dim in EVALUATION_DIMENSIONS} | {"aggregate_score": 1.0}

    exp_class = benchmark_case.get("expected_classification") if benchmark_case else None
    exp_kws = benchmark_case.get("expected_keywords") if benchmark_case else None

    class_score = score_classification_correctness(response_text, exp_class)
    rc_score, ev_score = score_evidence_and_root_cause(response_text, exp_kws)
    comp_score = score_completeness(response_text)
    claims_score = score_unsupported_claims(response_text)
    safety_score = score_safety_and_uncertainty(response_text)

    # Human-assessed dimensions default to baseline automated estimate
    tech_score = round((class_score + rc_score) / 2, 1)
    rec_score = comp_score
    clarity_score = 4.0 if len(response_text) > 200 else 2.5

    dimension_scores = {
        "classification_correctness": class_score,
        "root_cause_accuracy": rc_score,
        "evidence_based_reasoning": ev_score,
        "debugging_recommendation_relevance": rec_score,
        "technical_correctness": tech_score,
        "completeness": comp_score,
        "clarity": clarity_score,
        "unsupported_claims_absence": claims_score,
        "safety_and_uncertainty": safety_score,
    }

    avg_score = round(sum(dimension_scores.values()) / len(dimension_scores), 2)
    return {**dimension_scores, "aggregate_score": avg_score}


def record_human_evaluation(
    evaluator_name: str,
    scores: dict[str, float],
    comments: str = "",
) -> dict:
    """
    Validate and record manual human evaluation scores.
    """
    for dim, score in scores.items():
        if dim not in EVALUATION_DIMENSIONS:
            raise ValueError(f"Unknown evaluation dimension: {dim}")
        if not 1.0 <= score <= 5.0:
            raise ValueError(f"Score for {dim} must be between 1.0 and 5.0 (got {score})")

    avg = round(sum(scores.values()) / len(scores), 2)
    return {
        "evaluator": evaluator_name,
        "scores": scores,
        "aggregate_score": avg,
        "comments": comments,
    }


def evaluate_runs(
    runs: list[dict],
    benchmark_cases: list[dict],
    save_results: bool = True,
) -> dict:
    """
    Evaluate a collection of experiment runs against benchmark cases.
    Aggregates results by model and identifies relative strengths/weaknesses.
    """
    case_map = {c["id"]: c for c in benchmark_cases}
    evaluated_runs = []

    models = sorted({r["model_name"] for r in runs})
    model_scores = {m: {dim: [] for dim in EVALUATION_DIMENSIONS} for m in models}

    for run in runs:
        input_id = run.get("input_id")
        case = case_map.get(input_id)
        scores = evaluate_response_objectively(run.get("generated_response"), case)

        model = run["model_name"]
        for dim in EVALUATION_DIMENSIONS:
            model_scores[model][dim].append(scores[dim])

        evaluated_runs.append({
            "input_id": input_id,
            "model_name": model,
            "scores": scores,
        })

    model_analysis = {}
    for model, dim_dict in model_scores.items():
        dim_averages = {
            dim: round(sum(vals) / len(vals), 2) if vals else 0.0
            for dim, vals in dim_dict.items()
        }
        overall_avg = (
            round(sum(dim_averages.values()) / len(dim_averages), 2)
            if dim_averages
            else 0.0
        )

        sorted_dims = sorted(dim_averages.items(), key=lambda x: x[1], reverse=True)
        strengths = [f"{dim} ({score})" for dim, score in sorted_dims[:2]]
        weaknesses = [f"{dim} ({score})" for dim, score in sorted_dims[-2:]]

        model_analysis[model] = {
            "overall_quality_score": overall_avg,
            "dimension_averages": dim_averages,
            "strengths": strengths,
            "weaknesses": weaknesses,
        }

    payload = {
        "total_evaluated_runs": len(evaluated_runs),
        "model_analysis": model_analysis,
        "evaluated_runs": evaluated_runs,
    }

    if save_results:
        with open(QUALITY_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    return payload


def calculate_precision_recall_f1(
    y_true: list[str | None],
    y_pred: list[str | None],
    labels: list[str] | None = None,
) -> dict:
    """
    Compute Accuracy, Precision, Recall, and Macro-F1 without external ML libraries.
    Treats missing and null predictions honestly; reports exact sample size.
    """
    if not y_true or not y_pred:
        return {
            "accuracy": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "sample_size": 0,
            "per_class": {},
        }

    sample_size = min(len(y_true), len(y_pred))
    pairs = list(zip(y_true[:sample_size], y_pred[:sample_size]))

    exact_matches = sum(
        1
        for yt, yp in pairs
        if yt is not None and yp is not None and str(yt).lower().strip() == str(yp).lower().strip()
    )
    accuracy = round(exact_matches / sample_size, 4) if sample_size > 0 else 0.0

    target_labels = labels or sorted({str(yt).lower().strip() for yt, _ in pairs if yt is not None})
    per_class = {}
    f1_list, prec_list, rec_list = [], [], []

    for label in target_labels:
        lbl = str(label).lower().strip()
        tp = sum(
            1
            for yt, yp in pairs
            if yt and yp and str(yt).lower().strip() == lbl and str(yp).lower().strip() == lbl
        )
        fp = sum(
            1
            for yt, yp in pairs
            if (not yt or str(yt).lower().strip() != lbl) and yp and str(yp).lower().strip() == lbl
        )
        fn = sum(
            1
            for yt, yp in pairs
            if yt and str(yt).lower().strip() == lbl and (not yp or str(yp).lower().strip() != lbl)
        )

        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = (
            round(2 * (precision * recall) / (precision + recall), 4)
            if (precision + recall) > 0
            else 0.0
        )

        per_class[lbl] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
        prec_list.append(precision)
        rec_list.append(recall)
        f1_list.append(f1)

    macro_prec = round(sum(prec_list) / len(prec_list), 4) if prec_list else 0.0
    macro_rec = round(sum(rec_list) / len(rec_list), 4) if rec_list else 0.0
    macro_f1 = round(sum(f1_list) / len(f1_list), 4) if f1_list else 0.0

    return {
        "accuracy": accuracy,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "macro_f1": macro_f1,
        "sample_size": sample_size,
        "per_class": per_class,
    }


def evaluate_evidence_grounding(
    report_or_dict,
    raw_input_text: str,
    known_evidence: list[str] | None = None,
) -> dict:
    """
    Verify whether cited files, line numbers, and error excerpts actually
    exist in the raw input. Detects and penalizes hallucinated / invented locations.
    """
    if not report_or_dict or not raw_input_text:
        return {
            "grounding_score": 1.0,
            "file_grounded": None,
            "line_grounded": None,
            "invented_locations": [],
            "evidence_recall": 0.0,
        }

    raw_lower = raw_input_text.lower()
    invented_locations = []
    file_grounded = None
    line_grounded = None

    if hasattr(report_or_dict, "error_information"):
        err_info = report_or_dict.error_information
        filename = getattr(err_info, "filename", None)
        line_num = getattr(err_info, "line_number", None)
    elif isinstance(report_or_dict, dict):
        err_info = report_or_dict.get("error_information", {})
        filename = err_info.get("filename")
        line_num = err_info.get("line_number")
    else:
        filename, line_num = None, None

    if filename:
        fn_clean = str(filename).strip()
        fn_base = Path(fn_clean).name.lower()
        if fn_clean.lower() in raw_lower or fn_base in raw_lower:
            file_grounded = True
        else:
            file_grounded = False
            invented_locations.append(f"filename:{filename}")

    if line_num is not None:
        if str(line_num) in raw_input_text:
            line_grounded = True
        else:
            line_grounded = False
            invented_locations.append(f"line:{line_num}")

    recall = 0.0
    if known_evidence:
        rep_text = str(report_or_dict).lower()
        matched = sum(1 for token in known_evidence if token.lower() in rep_text)
        recall = round(matched / len(known_evidence), 4)

    if invented_locations:
        score = 2.0
    elif file_grounded is True and (line_grounded is True or line_grounded is None):
        score = 5.0
    elif file_grounded is True or line_grounded is True:
        score = 4.0
    elif file_grounded is None and line_grounded is None:
        score = 3.5
    else:
        score = 2.5

    return {
        "grounding_score": score,
        "file_grounded": file_grounded,
        "line_grounded": line_grounded,
        "invented_locations": invented_locations,
        "evidence_recall": recall,
    }


def evaluate_schema_validity(report_obj) -> dict:
    """
    Check whether an output conforms to the Phase 6 DebuggingReport Pydantic schema.
    """
    from pydantic import ValidationError

    from app.llm.exceptions import StructuredReportError
    from app.schemas.debugging_report import DebuggingReport

    if isinstance(report_obj, DebuggingReport):
        return {"is_schema_valid": True, "error": None}

    if isinstance(report_obj, dict):
        try:
            DebuggingReport.model_validate(report_obj)
            return {"is_schema_valid": True, "error": None}
        except (ValidationError, ValueError, TypeError) as err:
            return {"is_schema_valid": False, "error": str(err)}

    if isinstance(report_obj, str):
        from app.schemas.debugging_report import parse_structured_debugging_report

        try:
            parse_structured_debugging_report(report_obj)
            return {"is_schema_valid": True, "error": None}
        except (StructuredReportError, ValidationError, ValueError, TypeError) as err:
            return {"is_schema_valid": False, "error": str(err)}

    return {"is_schema_valid": False, "error": "Unknown object type"}
