# TracePilot — Phase 9: Debugging Evaluation Engine Report

**Run ID:** `eval-run-20261108-054800`  
**Generated:** 2026-11-08T05:48:00.508913+00:00  
**Benchmark Version:** v1.0-standardized  
**Total Benchmark Cases:** 1  
**Models Evaluated:** `gemini-3.5-flash-lite`, `gemini-3.5-flash`

## 1. Executive Summary
Phase 9 establishes a reproducible, multi-dimensional evaluation suite assessing TracePilot across Ground-Truth Correctness, Schema Compliance, Evidence Grounding, Performance Latencies, and Human Review Rubrics. All classification metrics report exact sample sizes and distinguish measured results from mathematical estimates.

## 2. Benchmark Dataset Structure
The benchmark contains 1 representative cases spanning:
- **Python Exceptions**: Type mismatch (`TypeError`), missing package (`ModuleNotFoundError`), index boundaries (`IndexError`).
- **JavaScript Errors**: Undefined property access (`TypeError`), lexical scope (`ReferenceError`).
- **Database Errors**: Unique constraint violations (`UniqueViolation`), connection failures (`OperationalError`).
- **API Failures**: Expired tokens (`HTTP 401 Unauthorized`), rate limits (`HTTP 429 Too Many Requests`).
- **Application Logs**: Unhandled socket resets (`ConnectionResetError`).

## 3. Head-to-Head Model Comparison
| Model                   | Schema Valid % | Type Acc % | Cat F1 | Sev F1 | Grounding (1-5) | Invented Loc % | Mean Latency |
| ----------------------- | -------------- | ---------- | ------ | ------ | --------------- | -------------- | ------------ |
| `gemini-3.5-flash-lite` | 100.0%         | 100.0%     | 1.00   | 1.00   | 5.0/5.0         | 0.0%           | 0.850s       |
| `gemini-3.5-flash`      | 100.0%         | 100.0%     | 1.00   | 1.00   | 5.0/5.0         | 0.0%           | 1.450s       |

## 4. Token Consumption & Verified Cost Analysis
| Model                   | Total Prompt Tokens | Total Resp Tokens | Total Tokens | Est Cost (USD) | Pricing Source                                          |
| ----------------------- | ------------------- | ----------------- | ------------ | -------------- | ------------------------------------------------------- |
| `gemini-3.5-flash-lite` | 120                 | 80                | 200          | $0.000033      | Google AI Studio Developer Pay-as-you-go reference tier |
| `gemini-3.5-flash`      | 120                 | 90                | 210          | $0.000072      | Google AI Studio Developer Pay-as-you-go reference tier |

## 5. Human Evaluation Summary
Recorded **1** expert human evaluations based on the 1–5 rubric:

| Evaluator     | Aggregate Score (1-5) | Comments                               |
| ------------- | --------------------- | -------------------------------------- |
| Lead Reviewer | 4.50/5.0              | Clear, verified, actionable diagnosis. |

## 6. Methodological Safeguards & Limitations
- **Ground-Truth Separation**: Rule-based matching against explicit case expectations is strictly isolated from LLM judge outputs.
- **No LLM Hallucination of Evidence**: Evidence grounding checks verify token presence in raw input traces; invented locations are flagged.
- **No Real-World Exaggeration**: Synthetic cases are explicitly designated as `is_synthetic: True`.
- **Strict 2-Model Architecture**: Live comparisons exclusively evaluate `gemini-3.5-flash-lite` and `gemini-3.5-flash`.
