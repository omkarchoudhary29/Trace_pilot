"""
Tests for Phase 5.8 Consolidated Experiment Report Generator.
"""

from experiments.generate_report import (
    build_markdown_report,
    format_table,
    load_json_file,
)


def test_format_table():
    headers = ["Col A", "Column B"]
    rows = [["Val 1", "Value 2"], ["V3", "V4"]]
    table = format_table(headers, rows)

    assert "| Col A" in table
    assert "| Column B" in table
    assert "---" in table
    assert "Val 1" in table


def test_build_markdown_report_sections():
    sample_data = {
        "timestamp": "2026-11-07 12:00:00 UTC",
        "model_comparison": {
            "summary": {
                "gemini-3.5-flash-lite": {
                    "total_requests": 5,
                    "success_rate_pct": 100.0,
                    "avg_latency_sec": 0.85,
                    "avg_prompt_tokens": 120,
                    "avg_response_tokens": 250,
                    "avg_total_tokens": 370,
                }
            }
        },
        "parameter_grid": {
            "total_configurations_tested": 16,
            "total_runs": 32,
        },
        "quality_evaluation": {
            "model_analysis": {
                "gemini-3.5-flash-lite": {
                    "overall_quality_score": 4.65,
                    "strengths": ["classification", "evidence"],
                    "weaknesses": ["verbosity"],
                }
            }
        },
        "cost_analysis": {
            "total_requests_analyzed": 5,
            "total_prompt_tokens": 600,
            "total_response_tokens": 1250,
            "total_tokens": 1850,
            "avg_tokens_per_request": 370.0,
            "total_estimated_cost_usd": 0.00042,
            "model_breakdown": {
                "gemini-3.5-flash-lite": {
                    "total_prompt_tokens": 600,
                    "total_response_tokens": 1250,
                    "pricing_source": "Test Source",
                    "effective_date": "2026-11-01",
                    "estimated_cost_usd": 0.00042,
                }
            },
        },
    }

    report = build_markdown_report(sample_data)

    # Verify all 12 key sections exist
    required_sections = [
        "## 1. Executive Summary",
        "## 2. Experiment Objectives",
        "## 3. Experiment Methodology",
        "## 4. Model Comparison",
        "## 5. Parameter Comparison",
        "## 6. Output Quality Evaluation",
        "## 7. Token Usage Analysis",
        "## 8. Cost Estimates",
        "## 9. Key Findings",
        "## 10. Limitations",
        "## 11. Recommended Configurations",
        "## 12. Future Improvements",
    ]

    for sec in required_sections:
        assert sec in report, f"Missing section: {sec}"

    assert "gemini-3.5-flash-lite" in report
    assert "$0.000420" in report


def test_load_json_file_nonexistent(tmp_path):
    missing_file = tmp_path / "missing.json"
    assert load_json_file(missing_file) is None

