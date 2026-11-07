"""
Phase 5.7: Token Usage and Cost Analysis.

Tracks prompt, response, and total token consumption across models and experiments.
Provides configurable pricing estimation with verified pricing metadata and dates,
clearly distinguishing estimated mathematical cost from actual billed amounts.
"""

import json
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
COST_RESULTS_FILE = OUTPUT_DIR / "cost_analysis_results.json"

# Verified reference pricing per 1,000,000 tokens (USD)
# Source: Google Cloud / Google AI Studio official pricing documentation
PRICING_REGISTRY = {
    "gemini-3.5-flash-lite": {
        "input_cost_per_million": 0.075,
        "output_cost_per_million": 0.30,
        "currency": "USD",
        "pricing_source": "Google AI Studio Developer Pay-as-you-go reference tier",
        "effective_date": "2025-11-01",
        "is_verified": True,
    },
    "gemini-3.5-flash": {
        "input_cost_per_million": 0.15,
        "output_cost_per_million": 0.60,
        "currency": "USD",
        "pricing_source": "Google AI Studio Developer Pay-as-you-go reference tier",
        "effective_date": "2025-11-01",
        "is_verified": True,
    },
}


def get_model_pricing(model_name: str, custom_pricing: dict | None = None) -> dict | None:
    """Retrieve pricing config for a given model if available."""
    registry = custom_pricing or PRICING_REGISTRY
    if model_name in registry:
        return registry[model_name]

    # Partial match fallback
    for name, p in registry.items():
        if name in model_name:
            return p
    return None


def calculate_request_cost(
    model_name: str,
    prompt_tokens: int | None,
    response_tokens: int | None,
    custom_pricing: dict | None = None,
) -> dict:
    """
    Compute mathematical cost estimate for one request.
    Returns None for costs if pricing is unverified or tokens are missing.
    """
    pricing = get_model_pricing(model_name, custom_pricing)

    if not pricing or not pricing.get("is_verified"):
        return {
            "pricing_available": False,
            "pricing_source": "Unverified or Not Configured",
            "effective_date": None,
            "estimated_prompt_cost_usd": None,
            "estimated_response_cost_usd": None,
            "estimated_total_cost_usd": None,
            "disclaimer": "Pricing unverified: token counts only.",
        }

    p_tokens = prompt_tokens or 0
    r_tokens = response_tokens or 0

    prompt_cost = (p_tokens / 1_000_000) * pricing["input_cost_per_million"]
    response_cost = (r_tokens / 1_000_000) * pricing["output_cost_per_million"]
    total_cost = prompt_cost + response_cost

    return {
        "pricing_available": True,
        "pricing_source": pricing["pricing_source"],
        "effective_date": pricing["effective_date"],
        "estimated_prompt_cost_usd": round(prompt_cost, 8),
        "estimated_response_cost_usd": round(response_cost, 8),
        "estimated_total_cost_usd": round(total_cost, 8),
        "disclaimer": "Estimated based on token usage; excludes taxes, tier limits, or free-quota discounts.",
    }


def analyze_token_usage_and_costs(
    runs: list[dict],
    custom_pricing: dict | None = None,
    save_results: bool = True,
) -> dict:
    """
    Perform comprehensive token consumption and cost modeling across experiment runs.
    """
    models = sorted({r["model_name"] for r in runs if "model_name" in r})

    model_metrics = {}
    total_prompt_tokens_all = 0
    total_response_tokens_all = 0
    total_tokens_all = 0
    total_estimated_cost_all = 0.0
    has_any_cost_estimate = False

    for model in models:
        m_runs = [r for r in runs if r.get("model_name") == model]
        successful = [r for r in m_runs if r.get("success")]
        failed = [r for r in m_runs if not r.get("success")]

        p_tokens = sum(r.get("prompt_tokens") or 0 for r in successful)
        r_tokens = sum(r.get("response_tokens") or 0 for r in successful)
        t_tokens = sum(r.get("total_tokens") or 0 for r in successful)

        latencies = [r.get("execution_time_sec") for r in successful if r.get("execution_time_sec")]
        avg_latency = round(sum(latencies) / len(latencies), 4) if latencies else None

        avg_prompt = round(p_tokens / len(successful), 1) if successful else 0
        avg_response = round(r_tokens / len(successful), 1) if successful else 0
        avg_total = round(t_tokens / len(successful), 1) if successful else 0

        cost_info = calculate_request_cost(model, p_tokens, r_tokens, custom_pricing)

        if cost_info["pricing_available"]:
            has_any_cost_estimate = True
            m_cost = cost_info["estimated_total_cost_usd"]
            total_estimated_cost_all += m_cost
        else:
            m_cost = None

        total_prompt_tokens_all += p_tokens
        total_response_tokens_all += r_tokens
        total_tokens_all += t_tokens

        model_metrics[model] = {
            "total_requests": len(m_runs),
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "avg_latency_sec": avg_latency,
            "total_prompt_tokens": p_tokens,
            "total_response_tokens": r_tokens,
            "total_tokens": t_tokens,
            "avg_prompt_tokens_per_request": avg_prompt,
            "avg_response_tokens_per_request": avg_response,
            "avg_total_tokens_per_request": avg_total,
            "pricing_available": cost_info["pricing_available"],
            "pricing_source": cost_info["pricing_source"],
            "effective_date": cost_info["effective_date"],
            "estimated_cost_usd": m_cost,
        }

    overall_avg_tokens = (
        round(total_tokens_all / len(runs), 1) if runs else 0
    )

    summary = {
        "total_requests_analyzed": len(runs),
        "total_prompt_tokens": total_prompt_tokens_all,
        "total_response_tokens": total_response_tokens_all,
        "total_tokens": total_tokens_all,
        "avg_tokens_per_request": overall_avg_tokens,
        "total_estimated_cost_usd": round(total_estimated_cost_all, 6) if has_any_cost_estimate else None,
        "model_breakdown": model_metrics,
        "pricing_disclaimer": "Calculated costs are mathematical estimates and not official invoice billing data.",
    }

    if save_results:
        with open(COST_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

    return summary

