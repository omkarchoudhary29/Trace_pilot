"""
FastAPI application server for TracePilot.

Exposes:
- GET /api/health: Service status, versions, and active model names.
- GET /api/examples: Preset benchmark cases for quick testing.
- POST /api/debug: Synchronous debugging with validated Pydantic report.
- POST /api/debug/stream: Server-Sent Events (SSE) streaming endpoint.
- GET /api/evaluation: Real benchmark evaluation metrics from Phase 9.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    DebugRequest,
    DebugResponse,
    EvaluationResponse,
    ExampleCase,
    HealthResponse,
)
from app.input.preprocessor import extract_metadata, normalize_error_text
from app.input.redactor import redact_secrets
from app.input.validators import validate_error_input
from app.llm.api_handler import generate_response_with_metrics
from app.llm.exceptions import (
    APIAuthenticationError,
    APIQuotaExceededError,
    APIRateLimitError,
    APIRequestError,
    APIResponseTruncatedError,
    APIServiceError,
    APITimeoutError,
    StructuredReportError,
    TracePilotAPIError,
)
from app.llm.logger import get_logger
from app.llm.streaming import generate_response_stream
from app.prompting.system_prompts import (
    STRUCTURED_DEBUGGING_SYSTEM_PROMPT,
    TRACEPILOT_SYSTEM_PROMPT,
)
from app.prompting.user_messages import (
    build_structured_user_message,
    build_user_message,
)
from app.schemas.debugging_report import (
    DebuggingReport,
    parse_structured_debugging_report,
)
from data.benchmark_inputs import BENCHMARK_INPUTS

logger = get_logger("TracePilot.API.Server")

app = FastAPI(
    title="TracePilot API",
    description="AI-Powered Error & Log Intelligence Platform REST and Streaming Engine",
    version="1.0.0",
)

# CORS configuration restricted to standard local frontend development servers
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

EVALUATION_FILE = Path("output") / "debugging_evaluation_results.json"


@app.get("/api/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return application availability and active model names without exposing keys."""
    primary = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    fallback = os.getenv("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")

    return HealthResponse(
        status="ok",
        version="1.0.0",
        primary_model=primary,
        fallback_model=fallback if fallback != primary else None,
        pricing_available=True,
    )


@app.get("/api/examples", response_model=list[ExampleCase])
def get_examples() -> list[ExampleCase]:
    """Provide benchmark cases for 1-click testing in the developer dashboard."""
    return [
        ExampleCase(
            id=case["id"],
            title=case["title"],
            category=case["category"],
            severity=case["severity"],
            programming_language=case["programming_language"],
            error_text=case["error_text"].strip(),
            description=case["description"],
        )
        for case in BENCHMARK_INPUTS
    ]


@app.get("/api/evaluation", response_model=EvaluationResponse)
def get_evaluation_data() -> EvaluationResponse:
    """Return stored Phase 9 benchmark evaluation results if available."""
    if not EVALUATION_FILE.exists():
        return EvaluationResponse(available=False, data=None)

    try:
        with open(EVALUATION_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return EvaluationResponse(available=True, data=data)
    except (json.JSONDecodeError, OSError) as err:
        logger.warning("Could not read evaluation results file: %s", err)
        return EvaluationResponse(available=False, data=None)


@app.post("/api/debug", response_model=DebugResponse)
def debug_error(request: DebugRequest) -> DebugResponse:
    """
    Synchronous debugging endpoint.

    Validates, redacts secrets, queries Gemini (primary/fallback),
    and validates structured DebuggingReport.
    """
    try:
        # Step 1: Input validation
        validate_error_input(request.error_text)
    except (ValueError, TypeError) as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    # Step 2: Normalization and secret redaction
    normalized = normalize_error_text(request.error_text)
    sanitized = redact_secrets(normalized)
    metadata = extract_metadata(sanitized)

    # If language hint was supplied, include in metadata
    if request.programming_language and request.programming_language.lower() != "auto":
        metadata["language_hint"] = request.programming_language

    try:
        if request.structured:
            user_msg = build_structured_user_message(sanitized, metadata)
            raw_text, metrics = generate_response_with_metrics(
                prompt=user_msg,
                system_instruction=STRUCTURED_DEBUGGING_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=DebuggingReport,
            )
            report = parse_structured_debugging_report(raw_text)
            return DebugResponse(
                success=True,
                report=report,
                raw_text=raw_text,
                metrics=metrics,
            )

        # Unstructured fallback mode
        user_msg = build_user_message(sanitized)
        raw_text, metrics = generate_response_with_metrics(
            prompt=user_msg,
            system_instruction=TRACEPILOT_SYSTEM_PROMPT,
        )
        return DebugResponse(
            success=True,
            report=None,
            raw_text=raw_text,
            metrics=metrics,
        )

    except APIAuthenticationError as err:
        logger.error("Authentication failure: %s", err)
        raise HTTPException(
            status_code=401,
            detail="Gemini API authentication failed. Verify server GEMINI_API_KEY.",
        ) from err

    except (APIRateLimitError, APIQuotaExceededError) as err:
        logger.warning("Rate limit / quota exceeded: %s", err)
        raise HTTPException(
            status_code=429,
            detail="API rate limit or quota exceeded. Please retry shortly.",
        ) from err

    except APITimeoutError as err:
        logger.error("Request timed out: %s", err)
        raise HTTPException(
            status_code=504,
            detail="Gemini API request timed out after configured deadline.",
        ) from err

    except APIServiceError as err:
        logger.error("Gemini service unavailable: %s", err)
        raise HTTPException(
            status_code=503,
            detail="Gemini service is temporarily unavailable. Please retry.",
        ) from err

    except APIResponseTruncatedError as err:
        logger.warning("Response truncated: %s", err)
        raise HTTPException(
            status_code=502,
            detail="Model output was truncated because it exceeded output token limits.",
        ) from err

    except StructuredReportError as err:
        logger.error("Structured report parsing/validation failure: %s", err)
        raise HTTPException(
            status_code=502,
            detail=f"Model output failed structured schema validation: {err}",
        ) from err

    except (APIRequestError, TracePilotAPIError) as err:
        logger.error("API error during debugging: %s", err)
        status_code = 400 if isinstance(err, APIRequestError) else 500
        detail_msg = str(err) if isinstance(err, APIRequestError) else "A failure occurred while processing the debugging analysis."
        raise HTTPException(
            status_code=status_code,
            detail=detail_msg,
        ) from err


@app.post("/api/debug/stream")
def debug_error_stream(request: DebugRequest) -> StreamingResponse:
    """
    Server-Sent Events (SSE) streaming endpoint.

    Streams chunks incrementally and validates final structured report upon completion.
    """
    try:
        validate_error_input(request.error_text)
    except (ValueError, TypeError) as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    normalized = normalize_error_text(request.error_text)
    sanitized = redact_secrets(normalized)
    metadata = extract_metadata(sanitized)

    if request.programming_language and request.programming_language.lower() != "auto":
        metadata["language_hint"] = request.programming_language

    def event_generator():
        try:
            if request.structured:
                user_msg = build_structured_user_message(sanitized, metadata)
                stream = generate_response_stream(
                    prompt=user_msg,
                    system_instruction=STRUCTURED_DEBUGGING_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=DebuggingReport,
                )
            else:
                user_msg = build_user_message(sanitized)
                stream = generate_response_stream(
                    prompt=user_msg,
                    system_instruction=TRACEPILOT_SYSTEM_PROMPT,
                )

            for event in stream:
                # Format as Server-Sent Event frame
                data_dict = event.data
                # Serialize report if present
                if data_dict.get("report") and hasattr(data_dict["report"], "model_dump"):
                    data_dict = {**data_dict, "report": data_dict["report"].model_dump()}

                yield f"event: {event.event_type}\ndata: {json.dumps(data_dict)}\n\n"

        except (TracePilotAPIError, ValueError, RuntimeError, OSError) as stream_err:
            logger.error("Error during streaming generation: %s", stream_err)
            err_payload = {
                "error": str(stream_err),
                "error_type": type(stream_err).__name__,
            }
            yield f"event: failed\ndata: {json.dumps(err_payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Optional: Mount compiled frontend static assets for unified deployment
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists() and (_frontend_dist / "index.html").exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


