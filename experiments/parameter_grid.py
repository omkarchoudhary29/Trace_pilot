"""
Phase 5.5: Parameter Combination Experiments.

Analyzes how Temperature, Top-P, Top-K, and Max Output Tokens influence
debugging response quality, latency, token consumption, and truncation.
Includes both single-variable isolation and multi-variable grid configurations.
"""

import json
import os
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
RESULTS_FILE = OUTPUT_DIR / "parameter_grid_results.json"

# Parameter sets for isolated variable analysis
ISOLATED_CONFIGS = {
    "temperature": [
        {"name": "Temp 0.0 (Deterministic)", "temperature": 0.0, "top_p": 0.9, "top_k": None, "max_output_tokens": 1024},
        {"name": "Temp 0.2 (Baseline)", "temperature": 0.2, "top_p": 0.9, "top_k": None, "max_output_tokens": 1024},
        {"name": "Temp 0.7 (Creative)", "temperature": 0.7, "top_p": 0.9, "top_k": None, "max_output_tokens": 1024},
        {"name": "Temp 1.0 (High Variance)", "temperature": 1.0, "top_p": 0.9, "top_k": None, "max_output_tokens": 1024},
    ],
    "top_p": [
        {"name": "Top-P 0.3 (Strict Nucleus)", "temperature": 0.2, "top_p": 0.3, "top_k": None, "max_output_tokens": 1024},
        {"name": "Top-P 0.7 (Moderate Nucleus)", "temperature": 0.2, "top_p": 0.7, "top_k": None, "max_output_tokens": 1024},
        {"name": "Top-P 0.9 (Standard)", "temperature": 0.2, "top_p": 0.9, "top_k": None, "max_output_tokens": 1024},
        {"name": "Top-P 1.0 (Full Vocabulary)", "temperature": 0.2, "top_p": 1.0, "top_k": None, "max_output_tokens": 1024},
    ],
    "top_k": [
        {"name": "Top-K 1 (Greedy Choice)", "temperature": 0.2, "top_p": 0.9, "top_k": 1, "max_output_tokens": 1024},
        {"name": "Top-K 10 (Restricted)", "temperature": 0.2, "top_p": 0.9, "top_k": 10, "max_output_tokens": 1024},
        {"name": "Top-K 40 (Standard)", "temperature": 0.2, "top_p": 0.9, "top_k": 40, "max_output_tokens": 1024},
    ],
    "max_tokens": [
        {"name": "Tokens 64 (Severe Truncation)", "temperature": 0.2, "top_p": 0.9, "top_k": None, "max_output_tokens": 64},
        {"name": "Tokens 256 (Compact)", "temperature": 0.2, "top_p": 0.9, "top_k": None, "max_output_tokens": 256},
        {"name": "Tokens 1024 (Standard)", "temperature": 0.2, "top_p": 0.9, "top_k": None, "max_output_tokens": 1024},
        {"name": "Tokens 2048 (Full Detail)", "temperature": 0.2, "top_p": 0.9, "top_k": None, "max_output_tokens": 2048},
    ],
}

# Multi-parameter combinations
COMBINATION_CONFIGS = [
    {
        "name": "Strict-Deterministic",
        "description": "Zero temperature with greedy top-k and narrow nucleus",
        "temperature": 0.0,
        "top_p": 0.3,
        "top_k": 1,
        "max_output_tokens": 1024,
    },
    {
        "name": "Balanced-Production",
        "description": "Recommended settings for reliable technical debugging",
        "temperature": 0.2,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 2048,
    },
    {
        "name": "Exploratory-HighVariance",
        "description": "High temperature and broad sampling for brainstorming",
        "temperature": 0.8,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,
    },
    {
        "name": "Constrained-Tokens",
        "description": "Standard temperature but deliberately constrained output buffer",
        "temperature": 0.2,
        "top_p": 0.9,
        "top_k": None,
        "max_output_tokens": 128,
    },
]


def check_parameter_support(model_name: str, config: dict) -> dict:
    """
    Examine model and parameter settings to document compatibility notes.
    """
    notes = []
    if config.get("top_k") is not None:
        notes.append("Top-K is submitted via GenerateContentConfig; behavior depends on model architecture.")
    if config.get("max_output_tokens", 0) < 128:
        notes.append("Low token budget carries high probability of MAX_TOKENS truncation.")

    return {
        "model": model_name,
        "supports_temperature": True,
        "supports_top_p": True,
        "supports_top_k": True,
        "supports_max_output_tokens": True,
        "notes": notes,
    }


def run_parameter_experiments(
    benchmark_case: dict | None = None,
    models: list[str] | None = None,
    include_isolated: bool = True,
    include_combinations: bool = True,
    save_results: bool = True,
) -> dict:
    """
    Execute parameter experiments against configured models.
    """
    case = benchmark_case or BENCHMARK_INPUTS[0]
    sanitized_input = redact_secrets(case["error_text"].strip())
    prompt = build_user_message(sanitized_input)

    primary = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    fallback = os.getenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")
    target_models = models or [primary, fallback]

    experiment_id = f"EXP-5.5-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    experiment_runs = []

    configs_to_run = []
    if include_isolated:
        for group, conf_list in ISOLATED_CONFIGS.items():
            for c in conf_list:
                configs_to_run.append({**c, "group": f"isolated_{group}"})
    if include_combinations:
        for c in COMBINATION_CONFIGS:
            configs_to_run.append({**c, "group": "combination"})

    for conf in configs_to_run:
        for model_name in target_models:
            support_info = check_parameter_support(model_name, conf)

            run_result = execute_single_model(
                model=model_name,
                prompt=prompt,
                system_instruction=TRACEPILOT_SYSTEM_PROMPT,
                temperature=conf["temperature"],
                top_p=conf["top_p"],
                top_k=conf.get("top_k"),
                max_output_tokens=conf["max_output_tokens"],
                raise_on_error=False,
            )

            record = {
                "experiment_id": experiment_id,
                "config_name": conf["name"],
                "config_group": conf.get("group", "general"),
                "input_id": case["id"],
                "model_name": model_name,
                "temperature": conf["temperature"],
                "top_p": conf["top_p"],
                "top_k": conf.get("top_k"),
                "max_output_tokens": conf["max_output_tokens"],
                "success": run_result["success"],
                "execution_time_sec": run_result["execution_time"],
                "finish_reason": run_result["finish_reason"],
                "was_truncated": run_result["was_truncated"],
                "is_complete": run_result["is_complete"],
                "prompt_tokens": run_result["prompt_tokens"],
                "response_tokens": run_result["response_tokens"],
                "total_tokens": run_result["total_tokens"],
                "response_text_length": len(run_result["text"]) if run_result.get("text") else 0,
                "parameter_support": support_info,
                "error": run_result["error"],
            }
            experiment_runs.append(record)

    payload = {
        "experiment_id": experiment_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "input_id": case["id"],
        "total_configurations_tested": len(configs_to_run),
        "total_runs": len(experiment_runs),
        "runs": experiment_runs,
    }

    if save_results:
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    return payload


if __name__ == "__main__":
    print("Running Phase 5.5 Parameter Grid Experiments...")
    res = run_parameter_experiments()
    print(f"Completed {res['total_runs']} parameter runs.")

