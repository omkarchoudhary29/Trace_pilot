"""
Phase 6: Structured Debugging Engine Pydantic Models and Parser.

Defines the complete schema for TracePilot structured debugging reports
covering Error Information, Summary, Evidence, Root-Cause Analysis,
Debugging Steps, Fixes, Verification, and Review/Confidence.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.llm.exceptions import ReportParsingError, ReportValidationError


class Severity(str, Enum):
    """Severity classification of the diagnosed error."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Broad domain classification of the error."""

    RUNTIME = "runtime"
    SYNTAX = "syntax"
    NETWORK = "network"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    LOGIC = "logic"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Model confidence level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# =====================================================================
# SECTION A: ERROR INFORMATION
# =====================================================================


class ErrorInfo(BaseModel):
    """Core technical identity and origin of the error."""

    error_type: str = Field(
        ...,
        description="Specific error class, name, or HTTP code (e.g., TypeError, 401 Unauthorized)",
    )
    error_message: str = Field(
        ...,
        description="The verbatim or primary error description extracted from the trace.",
    )
    programming_language: str = Field(
        default="Unknown",
        description="Programming language, runtime, or dialect (e.g., Python, JavaScript, SQL).",
    )
    severity: Severity = Field(
        ...,
        description="Assessed severity impact level.",
    )
    category: ErrorCategory = Field(
        default=ErrorCategory.UNKNOWN,
        description="High-level category of failure.",
    )
    filename: str | None = Field(
        default=None,
        description="Specific source file where failure occurred, if known from input.",
    )
    line_number: int | None = Field(
        default=None,
        description="Source line number where exception triggered, if known from input.",
    )
    function_name: str | None = Field(
        default=None,
        description="Function, method, or scope name if known from input.",
    )

    @field_validator("error_type", "error_message")
    @classmethod
    def validate_non_empty_strings(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Field cannot be empty or blank.")
        return value.strip()

    @field_validator("line_number")
    @classmethod
    def validate_positive_line_number(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("Line number must be a positive integer.")
        return value


# =====================================================================
# SECTION B: ERROR SUMMARY
# =====================================================================


class ErrorSummary(BaseModel):
    """High-level summary of what transpired."""

    short_description: str = Field(
        ...,
        description="Concise description of the failure.",
    )
    failed_operation: str = Field(
        ...,
        description="The operation that was underway when the exception fired.",
    )
    plain_language_explanation: str = Field(
        ...,
        description="Intuitive explanation in clear, non-jargon language.",
    )


# =====================================================================
# SECTION C: EVIDENCE
# =====================================================================


class EvidenceSection(BaseModel):
    """Grounding facts directly quoted or extracted from the submitted input."""

    error_message_excerpts: list[str] = Field(
        default_factory=list,
        description="Direct quotes from error text.",
    )
    traceback_or_log_excerpts: list[str] = Field(
        default_factory=list,
        description="Key frame lines from traceback or logs.",
    )
    extracted_file_and_line: str | None = Field(
        default=None,
        description="Location summary extracted from input (e.g. 'app.py:42').",
    )
    observed_facts: list[str] = Field(
        default_factory=list,
        description="Facts explicitly proven by the input data without speculation.",
    )
    inferred_information: list[str] = Field(
        default_factory=list,
        description="Contextual conclusions inferred by the model, clearly separated from facts.",
    )


# =====================================================================
# SECTION D: ROOT-CAUSE ANALYSIS
# =====================================================================


class RootCauseHypothesis(BaseModel):
    """Individual hypothesis explaining why the error occurred."""

    hypothesis: str = Field(
        ...,
        description="Explanation of the causal mechanism.",
    )
    supporting_evidence: list[str] = Field(
        default_factory=list,
        description="Direct observations supporting this hypothesis.",
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Confidence level for this specific cause.",
    )


class RootCauseAnalysis(BaseModel):
    """Evaluated hypotheses ranking root causes."""

    primary_hypothesis: RootCauseHypothesis = Field(
        ...,
        description="Most probable root cause based on available evidence.",
    )
    alternative_hypotheses: list[RootCauseHypothesis] = Field(
        default_factory=list,
        description="Other plausible candidate explanations.",
    )
    missing_information_to_confirm: list[str] = Field(
        default_factory=list,
        description="Information, code context, or logs needed to definitively confirm cause.",
    )


# =====================================================================
# SECTION E: RECOMMENDED DEBUGGING STEPS
# =====================================================================


class DebuggingStep(BaseModel):
    """A discrete, actionable investigation or debugging task."""

    step_number: int = Field(
        ...,
        ge=1,
        description="Sequential order of the step.",
    )
    action: str = Field(
        ...,
        description="Concrete action the developer should take.",
    )
    why_recommended: str = Field(
        ...,
        description="Reasoning linking this step to the diagnosis.",
    )
    relevant_evidence: str | None = Field(
        default=None,
        description="Input evidence motivating this check.",
    )
    expected_outcome: str = Field(
        ...,
        description="What the developer should look for or expect after performing the step.",
    )


# =====================================================================
# SECTION F: SUGGESTED FIX
# =====================================================================


class SuggestedFix(BaseModel):
    """Recommended code or configuration correction."""

    explanation: str = Field(
        ...,
        description="Explanation of the proposed change.",
    )
    code_example: str | None = Field(
        default=None,
        description="Small illustrative snippet showing the fix (never claimed to have been run).",
    )
    where_to_apply: str | None = Field(
        default=None,
        description="File, function, or configuration block where the change belongs.",
    )
    assumptions_and_limitations: list[str] = Field(
        default_factory=list,
        description="Assumptions made in proposing this fix.",
    )


# =====================================================================
# SECTION G: VERIFICATION
# =====================================================================


class VerificationSection(BaseModel):
    """Instructions to validate that the problem has been solved."""

    how_to_verify: str = Field(
        ...,
        description="Procedure to test the application after applying the fix.",
    )
    expected_behavior: str = Field(
        ...,
        description="Observable behavior confirming successful resolution.",
    )
    suggested_test_cases: list[str] = Field(
        default_factory=list,
        description="Specific tests or edge cases to execute.",
    )
    if_error_persists: str | None = Field(
        default=None,
        description="Secondary checks if the error continues to occur.",
    )


# =====================================================================
# SECTION H: CONFIDENCE AND REVIEW
# =====================================================================


class ReviewAndConfidence(BaseModel):
    """Overall confidence score and human review flags."""

    overall_confidence: ConfidenceLevel = Field(
        ...,
        description="Overall confidence in the diagnosis and fix.",
    )
    human_review_required: bool = Field(
        default=False,
        description="Whether an experienced developer must manually review before applying changes.",
    )
    uncertainty_explanation: str | None = Field(
        default=None,
        description="Clarification on ambiguities or missing information causing uncertainty.",
    )


# =====================================================================
# ROOT MODEL: COMPLETE DEBUGGING REPORT
# =====================================================================


class DebuggingReport(BaseModel):
    """Consolidated, validated machine-readable debugging report."""

    error_information: ErrorInfo
    error_summary: ErrorSummary
    evidence: EvidenceSection
    root_cause_analysis: RootCauseAnalysis
    debugging_steps: list[DebuggingStep] = Field(default_factory=list)
    suggested_fix: SuggestedFix
    verification: VerificationSection
    confidence_and_review: ReviewAndConfidence

    def to_json(self, indent: int = 2) -> str:
        """Serialize the report to a formatted JSON string."""
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> DebuggingReport:
        """Deserialize a JSON string into a validated DebuggingReport instance."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as error:
            raise ReportParsingError(
                f"Invalid JSON string provided for deserialization: {error}"
            ) from error

        try:
            return cls.model_validate(data)
        except ValidationError as error:
            raise ReportValidationError(
                f"JSON failed DebuggingReport schema validation: {error}"
            ) from error

    def to_markdown(self) -> str:
        """Render a human-readable Markdown summary of the structured report."""
        info = self.error_information
        summary = self.error_summary
        evidence = self.evidence
        rc = self.root_cause_analysis
        fix = self.suggested_fix
        verif = self.verification
        review = self.confidence_and_review

        loc = f"`{info.filename}`" if info.filename else ""
        if info.line_number:
            loc += f" on line {info.line_number}" if loc else f"line {info.line_number}"
        if info.function_name:
            loc += f" (`{info.function_name}`)"

        md = [
            f"# TracePilot Debugging Report: {info.error_type}",
            f"**Severity:** `{info.severity.value.upper()}` | **Category:** `{info.category.value}` | **Language:** `{info.programming_language}`",
            f"**Location:** {loc or 'Not specified in input'}\n",
            "## 1. Summary",
            f"{summary.short_description}\n",
            f"- **Failed Operation:** {summary.failed_operation}",
            f"- **Explanation:** {summary.plain_language_explanation}\n",
            "## 2. Evidence from Trace",
        ]

        if evidence.observed_facts:
            md.append("**Observed Facts:**")
            for fact in evidence.observed_facts:
                md.append(f"- {fact}")

        if evidence.error_message_excerpts:
            md.append("\n**Excerpts:**")
            for exc in evidence.error_message_excerpts:
                md.append(f"> {exc}")

        md.extend([
            "\n## 3. Root-Cause Analysis",
            f"**Primary Hypothesis (Confidence: `{rc.primary_hypothesis.confidence.value}`):**",
            f"{rc.primary_hypothesis.hypothesis}\n",
        ])

        if rc.alternative_hypotheses:
            md.append("**Alternative Hypotheses:**")
            for alt in rc.alternative_hypotheses:
                md.append(f"- {alt.hypothesis} (Confidence: `{alt.confidence.value}`)")

        if rc.missing_information_to_confirm:
            md.append("\n**Missing Information Needed to Confirm:**")
            for missing in rc.missing_information_to_confirm:
                md.append(f"- {missing}")

        md.append("\n## 4. Recommended Debugging Steps")
        for step in sorted(self.debugging_steps, key=lambda s: s.step_number):
            md.append(f"{step.step_number}. **{step.action}**")
            md.append(f"   - *Why:* {step.why_recommended}")
            md.append(f"   - *Expected Outcome:* {step.expected_outcome}")

        md.extend([
            "\n## 5. Suggested Fix",
            fix.explanation,
        ])
        if fix.code_example:
            md.extend([
                "\n```python",
                fix.code_example.strip(),
                "```",
            ])

        md.extend([
            "\n## 6. Verification",
            f"- **Procedure:** {verif.how_to_verify}",
            f"- **Expected Behavior:** {verif.expected_behavior}",
        ])
        if verif.suggested_test_cases:
            md.append("- **Test Cases:**")
            for tc in verif.suggested_test_cases:
                md.append(f"  - {tc}")

        md.extend([
            "\n## 7. Review & Confidence",
            f"- **Overall Confidence:** `{review.overall_confidence.value}`",
            f"- **Human Review Required:** {'Yes' if review.human_review_required else 'No'}",
        ])
        if review.uncertainty_explanation:
            md.append(f"- **Uncertainty Notes:** {review.uncertainty_explanation}")

        return "\n".join(md)


# =====================================================================
# RESPONSE EXTRACTION AND VALIDATION ENGINE
# =====================================================================


def _strip_markdown_code_fences(raw_text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` surrounding code fences."""
    text = raw_text.strip()

    # Match fenced block
    fence_pattern = r"^```(?:json)?\s*\n(.*?)\n```$"
    match = re.search(fence_pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # If starts with ``` and ends with ```
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()

    return text


def _extract_first_json_object(raw_text: str) -> str:
    """Extract outermost JSON object delimited by '{' and '}' if mixed with prose."""
    start = raw_text.find("{")
    end = raw_text.rfind("}")

    if start != -1 and end != -1 and end > start:
        return raw_text[start : end + 1]

    return raw_text


def parse_structured_debugging_report(response_text: str | None) -> DebuggingReport:
    """
    Parse and validate raw model output into a Pydantic DebuggingReport.

    Handles:
    - Empty or whitespace output
    - Markdown code fences
    - Extraneous text surrounding JSON
    - Malformed JSON syntax
    - Missing required fields, invalid enums, and schema violations
    """
    if not response_text or not response_text.strip():
        raise ReportParsingError("Model output is empty; no report could be parsed.")

    cleaned_text = _strip_markdown_code_fences(response_text)
    candidate_json = _extract_first_json_object(cleaned_text)

    try:
        parsed_data: Any = json.loads(candidate_json)
    except json.JSONDecodeError as error:
        raise ReportParsingError(
            f"Failed to parse model response into valid JSON: {error}. "
            f"Extracted payload was: {candidate_json[:200]}..."
        ) from error

    if not isinstance(parsed_data, dict):
        raise ReportValidationError(
            f"Expected JSON object at root of debugging report, got {type(parsed_data).__name__}."
        )

    try:
        report = DebuggingReport.model_validate(parsed_data)
        return report
    except ValidationError as error:
        error_messages = []
        for err in error.errors():
            loc = " -> ".join(str(p) for p in err.get("loc", []))
            msg = err.get("msg", "invalid")
            error_messages.append(f"[{loc}]: {msg}")

        detailed_err = "; ".join(error_messages)
        raise ReportValidationError(
            f"Debugging report failed schema validation: {detailed_err}"
        ) from error
