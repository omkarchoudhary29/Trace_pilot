"""
Request and response schemas for the TracePilot API.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.llm.streaming import RequestUsageMetrics
from app.schemas.debugging_report import DebuggingReport


class HealthResponse(BaseModel):
    """System status and model configuration (no secrets)."""

    status: str = "ok"
    version: str = "1.0.0"
    primary_model: str
    fallback_model: str | None = None
    pricing_available: bool = True


class DebugRequest(BaseModel):
    """Payload for submitting an error or log for debugging."""

    error_text: str = Field(..., min_length=1, max_length=10000, description="Raw error text or log")
    programming_language: str | None = Field(default=None, description="Optional programming language hint")
    structured: bool = Field(default=True, description="Whether to produce a validated structured report")
    stream: bool = Field(default=False, description="Whether to stream the response via SSE")


class DebugResponse(BaseModel):
    """Complete debugging result including validated schema and metrics."""

    success: bool
    report: DebuggingReport | None = None
    raw_text: str | None = None
    metrics: RequestUsageMetrics | None = None
    error: str | None = None


class ExampleCase(BaseModel):
    """Benchmark scenario presented as an interactive preset."""

    id: str
    title: str
    category: str
    severity: str
    programming_language: str
    error_text: str
    description: str


class EvaluationResponse(BaseModel):
    """Actual benchmark evaluation metrics from Phase 9."""

    available: bool
    data: dict[str, Any] | None = None

