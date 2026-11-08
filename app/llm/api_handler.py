
import os
import time
import uuid
from datetime import UTC

from dotenv import load_dotenv
from google.genai import errors

from app.llm.client import create_gemini_client
from app.llm.exceptions import (
    APIAuthenticationError,
    APIQuotaExceededError,
    APIRateLimitError,
    APIRequestError,
    APIResourceNotFoundError,
    APIResponseTruncatedError,
    APIServiceError,
    APITimeoutError,
    TracePilotAPIError,
)
from app.llm.logger import get_logger
from app.llm.model_config import create_generation_config
from app.llm.response_handler import (
    extract_response_metadata,
    extract_response_text,
)
from app.llm.retry_handler import execute_with_retry

load_dotenv()

logger = get_logger("TracePilot.API")


def classify_api_error(error: Exception) -> TracePilotAPIError:
    """Convert Gemini SDK errors into TracePilot exceptions."""

    if isinstance(error, TimeoutError):
        return APITimeoutError("Gemini API request timed out.")

    err_msg = str(error).lower()
    if "deadline exceeded" in err_msg or "timed out" in err_msg or "timeout" in err_msg:
        return APITimeoutError("Gemini API request timed out.")

    if isinstance(error, errors.ClientError):
        status_code = getattr(error, "code", None)
        message = str(error).lower()

        if (
            status_code in (401, 403)
            or "api_key_invalid" in message
            or "api key not valid" in message
            or "api key invalid" in message
        ):
            return APIAuthenticationError(
                "Gemini authentication or permission failed."
            )

        if status_code == 429:
            quota_indicators = (
                "per day",
                "per-day",
                "daily limit",
                "requests per day",
                "daily quota",
                "quota exceeded",
            )

            if any(indicator in message for indicator in quota_indicators):
                return APIQuotaExceededError(
                    "Gemini model quota appears to be exhausted."
                )

            return APIRateLimitError(
                "Gemini temporary request rate limit exceeded."
            )

        if status_code == 404:
            return APIResourceNotFoundError(
                "Gemini model or resource was not found."
            )

        return APIRequestError(
            "Gemini rejected the API request."
        )

    if isinstance(error, errors.ServerError):
        return APIServiceError(
            "Gemini service is temporarily unavailable."
        )

    if isinstance(error, errors.APIError):
        return TracePilotAPIError(
            "An unexpected Gemini API error occurred."
        )

    return TracePilotAPIError(
        "An unexpected error occurred while communicating with Gemini."
    )


def _generate_with_classification(client, model, prompt, config):
    """Convert SDK errors before passing them to the retry mechanism."""

    try:
        return client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

    except (errors.APIError, TimeoutError) as error:
        raise classify_api_error(error) from error


def _request_model(client, model, prompt, config):
    """Execute one model request with retry handling."""

    return execute_with_retry(
        _generate_with_classification,
        client,
        model,
        prompt,
        config,
    )


def _generate_validated_response(client, model, prompt, config):
    """
    Generate a response and reject output truncated by the token limit.
    """

    response = _request_model(
        client,
        model,
        prompt,
        config,
    )

    metadata = extract_response_metadata(response)

    logger.info(
        "Response metadata from %s: %s",
        model,
        metadata,
    )

    if metadata["was_truncated"]:
        logger.warning(
            "Model %s reached the maximum output token limit.",
            model,
        )

        raise APIResponseTruncatedError(
            f"Model {model} output was truncated because it "
            "reached the maximum output token limit."
        )

    response_text = extract_response_text(response)

    if not metadata["is_complete"]:
        logger.warning(
            "Model %s finished with an unexpected finish reason: %s",
            model,
            metadata["finish_reason"],
        )

    return response_text


def generate_response(
    prompt: str,
    top_k: int | None = None,
    system_instruction: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    max_output_tokens: int = 2048,
    response_mime_type: str | None = None,
    response_schema: type | None = None,
) -> str:
    """Generate a response using primary and fallback Gemini models."""

    primary_model = os.getenv("GEMINI_MODEL")
    fallback_model = os.getenv("GEMINI_MODEL_FALLBACK")

    if not primary_model:
        raise ValueError("GEMINI_MODEL is missing from environment.")

    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    if fallback_model == primary_model:
        logger.warning(
            "Primary and fallback model are identical. "
            "Fallback will be disabled."
        )
        fallback_model = None

    client = create_gemini_client()
    request_id = f"req-{uuid.uuid4().hex[:8]}"

    config = create_generation_config(
        system_instruction=system_instruction,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        top_k=top_k,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
    )

    logger.info("[%s] Using primary Gemini model: %s", request_id, primary_model)

    try:
        response_text = _generate_validated_response(
            client,
            primary_model,
            prompt,
            config,
        )

        logger.info("[%s] Primary model succeeded: %s", request_id, primary_model)

        return response_text

    except (
        APIQuotaExceededError,
        APIRateLimitError,
        APIServiceError,
        APIResponseTruncatedError,
        APITimeoutError,
    ) as primary_error:

        if not fallback_model:
            logger.exception(
                "[%s] Primary model failed (%s) and no fallback is configured.",
                request_id,
                type(primary_error).__name__,
            )
            raise

        logger.warning(
            "[%s] Primary model (%s) failed with %s. Switching to fallback model: %s",
            request_id,
            primary_model,
            type(primary_error).__name__,
            fallback_model,
        )

        try:
            response_text = _generate_validated_response(
                client,
                fallback_model,
                prompt,
                config,
            )

            logger.info(
                "[%s] Fallback model succeeded: %s",
                request_id,
                fallback_model,
            )

            return response_text

        except TracePilotAPIError as fallback_error:
            logger.exception("[%s] Fallback model also failed.", request_id)

            raise TracePilotAPIError(
                "Both primary and fallback Gemini models failed."
            ) from fallback_error


def generate_response_with_metrics(
    prompt: str,
    top_k: int | None = None,
    system_instruction: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    max_output_tokens: int = 2048,
    response_mime_type: str | None = None,
    response_schema: type | None = None,
):
    """
    Generate a response and capture complete usage telemetry and cost metrics.
    """
    from datetime import datetime

    from app.llm.streaming import RequestUsageMetrics
    from experiments.cost_analyzer import calculate_request_cost

    primary_model = os.getenv("GEMINI_MODEL")
    fallback_model = os.getenv("GEMINI_MODEL_FALLBACK")

    if not primary_model:
        raise ValueError("GEMINI_MODEL is missing from environment.")

    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    if fallback_model == primary_model:
        fallback_model = None

    client = create_gemini_client()
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    start_iso = datetime.now(UTC).isoformat()
    start_perf = time.perf_counter()

    config = create_generation_config(
        system_instruction=system_instruction,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        top_k=top_k,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
    )

    active_model = primary_model
    fallback_used = False
    fallback_duration = None
    meta = {}

    try:
        response = _request_model(client, primary_model, prompt, config)
        meta = extract_response_metadata(response)
        if meta.get("was_truncated"):
            raise APIResponseTruncatedError(
                f"Model {primary_model} output was truncated because it reached maximum token limit."
            )
        response_text = extract_response_text(response)
    except (
        APIQuotaExceededError,
        APIRateLimitError,
        APIServiceError,
        APIResponseTruncatedError,
        APITimeoutError,
    ) as primary_error:
        if not fallback_model:
            raise

        logger.warning(
            "[%s] Primary model (%s) failed with %s. Switching to fallback model: %s",
            request_id,
            primary_model,
            type(primary_error).__name__,
            fallback_model,
        )
        fallback_start = time.perf_counter()
        active_model = fallback_model
        fallback_used = True

        try:
            response = _request_model(client, fallback_model, prompt, config)
            meta = extract_response_metadata(response)
            if meta.get("was_truncated"):
                raise APIResponseTruncatedError(
                    f"Model {fallback_model} output was truncated because it reached maximum token limit."
                )
            response_text = extract_response_text(response)
            fallback_duration = round(time.perf_counter() - fallback_start, 4)
        except TracePilotAPIError as fallback_error:
            raise TracePilotAPIError(
                "Both primary and fallback Gemini models failed."
            ) from fallback_error

    end_perf = time.perf_counter()
    end_iso = datetime.now(UTC).isoformat()
    total_duration = round(end_perf - start_perf, 4)

    prompt_tok = meta.get("prompt_tokens")
    resp_tok = meta.get("response_tokens")
    cost_info = None
    if prompt_tok is not None or resp_tok is not None:
        cost_info = calculate_request_cost(active_model, prompt_tok, resp_tok)

    metrics = RequestUsageMetrics(
        request_id=request_id,
        model_used=active_model,
        fallback_used=fallback_used,
        streaming=False,
        start_time=start_iso,
        completion_time=end_iso,
        total_duration_seconds=total_duration,
        time_to_first_chunk_seconds=None,
        streaming_duration_seconds=None,
        fallback_duration_seconds=fallback_duration,
        prompt_tokens=prompt_tok,
        response_tokens=resp_tok,
        total_tokens=meta.get("total_tokens"),
        finish_reason=meta.get("finish_reason"),
        is_complete=meta.get("is_complete", False),
        was_truncated=meta.get("was_truncated", False),
        error_category=None,
        cost_estimate=cost_info,
    )

    return response_text, metrics


def execute_single_model(
    model: str,
    prompt: str,
    system_instruction: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    max_output_tokens: int = 2048,
    top_k: int | None = None,
    response_mime_type: str | None = None,
    response_schema: type | None = None,
    raise_on_error: bool = False,
) -> dict:
    """
    Execute a specific Gemini model independently without automatic fallback.

    Used by Model Comparison and Parameter Experiment labs to evaluate
    models in isolation.
    """

    if not model or not model.strip():
        raise ValueError("Model name must be specified.")

    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    client = create_gemini_client()

    config = create_generation_config(
        system_instruction=system_instruction,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        top_k=top_k,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
    )

    logger.info("Executing independent model request for: %s", model)
    start_time = time.perf_counter()

    try:
        response = _request_model(client, model, prompt, config)
        metadata = extract_response_metadata(response)
        response_text = extract_response_text(response)
        elapsed_time = round(time.perf_counter() - start_time, 4)

        logger.info(
            "Independent execution for %s succeeded in %.4fs (finish_reason: %s)",
            model,
            elapsed_time,
            metadata.get("finish_reason"),
        )

        return {
            "model": model,
            "success": True,
            "text": response_text,
            "execution_time": elapsed_time,
            "finish_reason": metadata.get("finish_reason"),
            "prompt_tokens": metadata.get("prompt_tokens"),
            "response_tokens": metadata.get("response_tokens"),
            "total_tokens": metadata.get("total_tokens"),
            "is_complete": metadata.get("is_complete", False),
            "was_truncated": metadata.get("was_truncated", False),
            "metadata": metadata,
            "error": None,
        }

    except Exception as error:
        elapsed_time = round(time.perf_counter() - start_time, 4)
        logger.warning(
            "Independent execution for %s failed after %.4fs: %s",
            model,
            elapsed_time,
            error,
        )

        if raise_on_error:
            raise

        return {
            "model": model,
            "success": False,
            "text": None,
            "execution_time": elapsed_time,
            "finish_reason": None,
            "prompt_tokens": None,
            "response_tokens": None,
            "total_tokens": None,
            "is_complete": False,
            "was_truncated": False,
            "metadata": None,
            "error": str(error),
        }

