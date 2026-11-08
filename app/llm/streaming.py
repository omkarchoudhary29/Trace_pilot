"""
Phase 8: Streaming and Usage Engine for TracePilot.

Provides:
- Incremental text streaming using Google GenAI SDK (client.models.generate_content_stream).
- Strict 2-model failover policy (gemini-3.5-flash-lite -> gemini-3.5-flash) with buffer reset.
- StreamEvent event model (start, text_chunk, completed, failed).
- RequestUsageMetrics capturing monotonic latencies (TTFC, streaming duration, fallback duration),
  token counts, finish reasons, completion/truncation status, and cost estimates.
- Post-stream Pydantic schema validation (DebuggingReport) ensuring incomplete fragments
  are never parsed mid-stream.
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any, Literal

from google.genai import errors
from pydantic import BaseModel, Field

from app.llm.api_handler import classify_api_error
from app.llm.client import create_gemini_client
from app.llm.exceptions import (
    APIQuotaExceededError,
    APIRateLimitError,
    APIResponseTruncatedError,
    APIServiceError,
    APITimeoutError,
    TracePilotAPIError,
)
from app.llm.logger import get_logger
from app.llm.model_config import create_generation_config
from app.schemas.debugging_report import (
    DebuggingReport,
    parse_structured_debugging_report,
)
from experiments.cost_analyzer import calculate_request_cost

logger = get_logger("TracePilot.Streaming")

RECOVERABLE_FALLBACK_ERRORS = (
    APIQuotaExceededError,
    APIRateLimitError,
    APIServiceError,
    APIResponseTruncatedError,
    APITimeoutError,
)


class RequestUsageMetrics(BaseModel):
    """
    Comprehensive request-level telemetry and usage metrics.
    Captures monotonic timing, token usage, finish reasons, and cost analysis.
    """

    request_id: str
    model_used: str
    fallback_used: bool = False
    streaming: bool = True
    start_time: str
    completion_time: str | None = None
    total_duration_seconds: float | None = None
    time_to_first_chunk_seconds: float | None = None
    streaming_duration_seconds: float | None = None
    fallback_duration_seconds: float | None = None
    prompt_tokens: int | None = None
    response_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None
    is_complete: bool = False
    was_truncated: bool = False
    error_category: str | None = None
    cost_estimate: dict[str, Any] | None = None


class StreamEvent(BaseModel):
    """
    Unified streaming event container for SSE / stream consumers.
    """

    event_type: Literal["start", "text_chunk", "completed", "failed"]
    data: dict[str, Any] = Field(default_factory=dict)


def _extract_chunk_finish_reason(chunk: Any) -> str | None:
    """Extract and normalize finish_reason from chunk candidates if present."""
    candidates = getattr(chunk, "candidates", None)
    if not candidates:
        return None

    first_cand = candidates[0]
    fr = getattr(first_cand, "finish_reason", None)
    if fr is None:
        return None

    if hasattr(fr, "name"):
        return fr.name
    return str(fr).split(".")[-1]


def _extract_chunk_tokens(chunk: Any) -> tuple[int | None, int | None, int | None]:
    """Extract token counts (prompt, response, total) from chunk usage_metadata if present."""
    usage = getattr(chunk, "usage_metadata", None)
    if not usage:
        return None, None, None

    prompt_tokens = getattr(usage, "prompt_token_count", None)
    response_tokens = getattr(usage, "candidates_token_count", None)
    total_tokens = getattr(usage, "total_token_count", None)
    return prompt_tokens, response_tokens, total_tokens


def generate_response_stream(
    prompt: str,
    system_instruction: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    max_output_tokens: int = 2048,
    top_k: int | None = None,
    response_mime_type: str | None = None,
    response_schema: type | None = None,
    custom_client: Any | None = None,
) -> Generator[StreamEvent, None, None]:
    """
    Generate Gemini response as an incremental stream of events.

    Lifecycle:
    1. Yields 'start' event with request ID, primary model, and start timestamp.
    2. Streams chunks from primary model (gemini-3.5-flash-lite).
    3. Yields 'text_chunk' events with text delta and accumulated length.
    4. On recoverable failure: resets buffer, yields warning, switches cleanly
       to fallback model (gemini-3.5-flash) without mixing partial text.
    5. On non-recoverable failure: yields 'failed' event and raises typed error.
    6. On completion: calculates monotonic timings, extracts tokens, calculates
       cost, validates structured schema (if requested), and yields 'completed' event.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    primary_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    fallback_model = os.getenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    if fallback_model == primary_model:
        logger.warning(
            "Primary and fallback model are identical. Fallback disabled for streaming."
        )
        fallback_model = None

    request_id = f"req-{uuid.uuid4().hex[:8]}"
    start_iso = datetime.now(UTC).isoformat()
    total_start_perf = time.perf_counter()

    config = create_generation_config(
        system_instruction=system_instruction,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        top_k=top_k,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
    )

    client = custom_client or create_gemini_client()

    logger.info("[%s] Initiating stream with primary model: %s", request_id, primary_model)

    yield StreamEvent(
        event_type="start",
        data={
            "request_id": request_id,
            "model": primary_model,
            "streaming": True,
            "start_time": start_iso,
        },
    )

    active_model = primary_model
    fallback_used = False
    fallback_start_perf: float | None = None
    accumulated_chunks: list[str] = []
    chunk_index = 0
    first_chunk_perf: float | None = None
    stream_start_perf: float | None = None
    last_finish_reason: str | None = None
    prompt_tokens: int | None = None
    response_tokens: int | None = None
    total_tokens: int | None = None

    def _stream_iterator(model_target: str):
        try:
            return client.models.generate_content_stream(
                model=model_target,
                contents=prompt,
                config=config,
            )
        except (errors.APIError, TimeoutError, Exception) as err:
            raise classify_api_error(err) from err

    # Step 1: Execute primary stream
    try:
        iterator = _stream_iterator(primary_model)
        for chunk in iterator:
            if first_chunk_perf is None:
                first_chunk_perf = time.perf_counter()
                stream_start_perf = first_chunk_perf

            fr = _extract_chunk_finish_reason(chunk)
            if fr:
                last_finish_reason = fr

            p_tok, r_tok, t_tok = _extract_chunk_tokens(chunk)
            if p_tok is not None:
                prompt_tokens = p_tok
            if r_tok is not None:
                response_tokens = r_tok
            if t_tok is not None:
                total_tokens = t_tok

            chunk_text = getattr(chunk, "text", None) or ""
            if chunk_text:
                accumulated_chunks.append(chunk_text)
                yield StreamEvent(
                    event_type="text_chunk",
                    data={
                        "request_id": request_id,
                        "chunk_index": chunk_index,
                        "delta": chunk_text,
                        "accumulated_length": len("".join(accumulated_chunks)),
                    },
                )
                chunk_index += 1

        if last_finish_reason == "MAX_TOKENS":
            raise APIResponseTruncatedError(
                f"Primary model {primary_model} output was truncated (MAX_TOKENS reached)."
            )

    except Exception as primary_raw_err:
        primary_error = (
            primary_raw_err
            if isinstance(primary_raw_err, TracePilotAPIError)
            else classify_api_error(primary_raw_err)
        )

        is_recoverable = isinstance(primary_error, RECOVERABLE_FALLBACK_ERRORS)

        if not is_recoverable or not fallback_model:
            logger.exception(
                "[%s] Primary streaming failed non-recoverably (%s) or no fallback available.",
                request_id,
                type(primary_error).__name__,
            )
            yield StreamEvent(
                event_type="failed",
                data={
                    "request_id": request_id,
                    "model": primary_model,
                    "error": str(primary_error),
                    "error_type": type(primary_error).__name__,
                    "recoverable": False,
                    "fallback_attempted": False,
                },
            )
            raise primary_error

        # Recoverable failure: discard partial primary chunks and initiate clean fallback stream
        logger.warning(
            "[%s] Primary streaming (%s) failed with %s. Switching to fallback model: %s",
            request_id,
            primary_model,
            type(primary_error).__name__,
            fallback_model,
        )

        accumulated_chunks.clear()
        chunk_index = 0
        first_chunk_perf = None
        stream_start_perf = None
        last_finish_reason = None
        fallback_used = True
        active_model = fallback_model
        fallback_start_perf = time.perf_counter()

        try:
            fallback_iterator = _stream_iterator(fallback_model)
            for chunk in fallback_iterator:
                if first_chunk_perf is None:
                    first_chunk_perf = time.perf_counter()
                    stream_start_perf = first_chunk_perf

                fr = _extract_chunk_finish_reason(chunk)
                if fr:
                    last_finish_reason = fr

                p_tok, r_tok, t_tok = _extract_chunk_tokens(chunk)
                if p_tok is not None:
                    prompt_tokens = p_tok
                if r_tok is not None:
                    response_tokens = r_tok
                if t_tok is not None:
                    total_tokens = t_tok

                chunk_text = getattr(chunk, "text", None) or ""
                if chunk_text:
                    accumulated_chunks.append(chunk_text)
                    yield StreamEvent(
                        event_type="text_chunk",
                        data={
                            "request_id": request_id,
                            "chunk_index": chunk_index,
                            "delta": chunk_text,
                            "accumulated_length": len("".join(accumulated_chunks)),
                        },
                    )
                    chunk_index += 1

            if last_finish_reason == "MAX_TOKENS":
                raise APIResponseTruncatedError(
                    f"Fallback model {fallback_model} output was truncated (MAX_TOKENS reached)."
                )

        except Exception as fallback_raw_err:
            fallback_error = (
                fallback_raw_err
                if isinstance(fallback_raw_err, TracePilotAPIError)
                else classify_api_error(fallback_raw_err)
            )
            logger.exception("[%s] Fallback streaming also failed.", request_id)
            yield StreamEvent(
                event_type="failed",
                data={
                    "request_id": request_id,
                    "model": fallback_model,
                    "error": str(fallback_error),
                    "error_type": type(fallback_error).__name__,
                    "recoverable": False,
                    "fallback_attempted": True,
                },
            )
            raise TracePilotAPIError(
                "Both primary and fallback Gemini models failed streaming."
            ) from fallback_error

    # Finalization: Calculate latencies and validate accumulated response
    total_end_perf = time.perf_counter()
    end_iso = datetime.now(UTC).isoformat()

    total_duration = round(total_end_perf - total_start_perf, 4)
    time_to_first_chunk = (
        round(first_chunk_perf - total_start_perf, 4) if first_chunk_perf else None
    )
    streaming_duration = (
        round(total_end_perf - stream_start_perf, 4) if stream_start_perf else None
    )
    fallback_duration = (
        round(total_end_perf - fallback_start_perf, 4) if fallback_start_perf else None
    )

    full_text = "".join(accumulated_chunks)
    if not full_text:
        raise ValueError("Stream completed but produced an empty response text.")

    # Calculate cost via Phase 5 cost analyzer without duplicating logic
    cost_info = None
    if prompt_tokens is not None or response_tokens is not None:
        cost_info = calculate_request_cost(active_model, prompt_tokens, response_tokens)

    is_complete = last_finish_reason == "STOP"
    was_truncated = last_finish_reason == "MAX_TOKENS"

    metrics = RequestUsageMetrics(
        request_id=request_id,
        model_used=active_model,
        fallback_used=fallback_used,
        streaming=True,
        start_time=start_iso,
        completion_time=end_iso,
        total_duration_seconds=total_duration,
        time_to_first_chunk_seconds=time_to_first_chunk,
        streaming_duration_seconds=streaming_duration,
        fallback_duration_seconds=fallback_duration,
        prompt_tokens=prompt_tokens,
        response_tokens=response_tokens,
        total_tokens=total_tokens,
        finish_reason=last_finish_reason,
        is_complete=is_complete,
        was_truncated=was_truncated,
        error_category=None,
        cost_estimate=cost_info,
    )

    # Perform Phase 6 Pydantic schema validation after full stream accumulation
    parsed_report = None
    if response_schema is DebuggingReport or response_mime_type == "application/json":
        parsed_report = parse_structured_debugging_report(full_text)

    logger.info(
        "[%s] Stream finished successfully (%s in %.4fs, TTFC: %ss)",
        request_id,
        active_model,
        total_duration,
        time_to_first_chunk,
    )

    yield StreamEvent(
        event_type="completed",
        data={
            "request_id": request_id,
            "model": active_model,
            "raw_text": full_text,
            "report": parsed_report,
            "metrics": metrics.model_dump(),
        },
    )
