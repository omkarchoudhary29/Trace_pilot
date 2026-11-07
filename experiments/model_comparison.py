"""
Phase 5.4: Model Comparison Lab.

Compares gemini-3.5-flash-lite and gemini-3.5-flash head-to-head on identical
debugging benchmark inputs and system prompts without automatic fallback.
"""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from app.input.redactor import redact_secrets
from app.llm.api_handler import execute_single_model
from app.prompting.system_prompts import TRACEPILOT_SYSTEM_PROMPT
from app.prompting.user_messages import build_user_message
from data.benchmark_inputs import BENCHMARK_INPUTS

load_dotenv()

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
RESULTS_FILE = OUTPUT_DIR / "model_comparison_results.json"


def parse_debugging_sections(text: str | None) -> dict:
    """
    Extract structured debugging sections from LLM output.
    Uses tolerant regex patterns matching common headings.
    """
    if not text:
        return {
            "classification": None,
            "root_cause": None,
            "debugging_recommendations": None,
            "verification_steps": None,
        }

    sections = {
        "classification": None,
        "root_cause": None,
        "debugging_recommendations": None,
        "verification_steps": None,
    }

    class_match = re.search(
        r"(?:classification|error type)[:\s]+([^\n]+)",
        text,
        re.IGNORECASE,
    )
    if class_match:
        sections["classification"] = class_match.group(1).strip()

    cause_match = re.search(
        r"(?:root cause|likely cause|explanation)[:\s]+(.*?)(?=\n\s*(?:debugging|evidence|recommendation|verification|\d+\.|$))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if cause_match:
        sections["root_cause"] = cause_match.group(1).strip()[:400]

    rec_match = re.search(
        r"(?:debugging|recommendation|possible fix)[:\s]+(.*?)(?=\n\s*(?:verification|\d+\.|$))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if rec_match:
        sections["debugging_recommendations"] = rec_match.group(1).strip()[:400]

    verif_match = re.search(
        r"(?:verification)[:\s]+(.*?)(?=\n\s*(?:summary|note|\d+\.|$))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if verif_match:
        sections["verification_steps"] = verif_match.group(1).strip()[:400]

    return sections


def run_model_comparison(
    benchmark_cases: list[dict] | None = None,
    primary_model: str | None = None,
    fallback_model: str | None = None,
    temperature: float = 0.2,
    save_results: bool = True,
) -> dict:
    """
    Execute comparison workflow across both models independently.

    Returns a structured dictionary with individual run metrics and
    aggregated comparisons.
    """
    cases = benchmark_cases or BENCHMARK_INPUTS
    model_lite = primary_model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    model_flash = fallback_model or os.getenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    models = [model_lite, model_flash]
    experiment_id = f"EXP-5.4-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

    results = []

    for case in cases:
        input_id = case["id"]
        sanitized_input = redact_secrets(case["error_text"].strip())
        prompt = build_user_message(sanitized_input)

        for model_name in models:
            run_result = execute_single_model(
                model=model_name,
                prompt=prompt,
                system_instruction=TRACEPILOT_SYSTEM_PROMPT,
                temperature=temperature,
                raise_on_error=False,
            )

            sections = parse_debugging_sections(run_result.get("text"))

            entry = {
                "experiment_id": experiment_id,
                "input_id": input_id,
                "input_category": case.get("category", "General"),
                "input_title": case.get("title", input_id),
                "model_name": model_name,
                "success": run_result["success"],
                "execution_time_sec": run_result["execution_time"],
                "finish_reason": run_result["finish_reason"],
                "prompt_tokens": run_result["prompt_tokens"],
                "response_tokens": run_result["response_tokens"],
                "total_tokens": run_result["total_tokens"],
                "is_complete": run_result["is_complete"],
                "was_truncated": run_result["was_truncated"],
                "sections": sections,
                "generated_response": run_result["text"],
                "error": run_result["error"],
            }
            results.append(entry)

    summary = aggregate_comparison_metrics(results, models)

    payload = {
        "experiment_id": experiment_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "primary_model": model_lite,
        "fallback_model": model_flash,
        "temperature": temperature,
        "total_runs": len(results),
        "summary": summary,
        "runs": results,
    }

    if save_results:
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    return payload


def aggregate_comparison_metrics(runs: list[dict], models: list[str]) -> dict:
    """Compute mean latency, token counts, and success rates by model."""
    summary = {}

    for model in models:
        model_runs = [r for r in runs if r["model_name"] == model]
        successful = [r for r in model_runs if r["success"]]

        count = len(model_runs)
        success_count = len(successful)
        success_rate = (success_count / count * 100) if count else 0.0

        latencies = [r["execution_time_sec"] for r in successful if r["execution_time_sec"]]
        avg_latency = round(sum(latencies) / len(latencies), 4) if latencies else None

        prompt_tokens = [r["prompt_tokens"] for r in successful if r["prompt_tokens"] is not None]
        avg_prompt_tokens = round(sum(prompt_tokens) / len(prompt_tokens), 1) if prompt_tokens else 0

        response_tokens = [r["response_tokens"] for r in successful if r["response_tokens"] is not None]
        avg_response_tokens = round(sum(response_tokens) / len(response_tokens), 1) if response_tokens else 0

        total_tokens = [r["total_tokens"] for r in successful if r["total_tokens"] is not None]
        avg_total_tokens = round(sum(total_tokens) / len(total_tokens), 1) if total_tokens else 0

        summary[model] = {
            "total_requests": count,
            "successful_requests": success_count,
            "success_rate_pct": success_rate,
            "avg_latency_sec": avg_latency,
            "avg_prompt_tokens": avg_prompt_tokens,
            "avg_response_tokens": avg_response_tokens,
            "avg_total_tokens": avg_total_tokens,
            "total_tokens_consumed": sum(total_tokens) if total_tokens else 0,
        }

    return summary


if __name__ == "__main__":
    print("Running Phase 5.4 Model Comparison Lab...")
    output = run_model_comparison()
    print("Completed. Summary:")
    print(json.dumps(output["summary"], indent=2))
