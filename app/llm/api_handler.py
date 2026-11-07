
import os
import time

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

    if isinstance(error, errors.ClientError):
        status_code = getattr(error, "code", None)
        message = str(error).lower()

        if status_code in (401, 403):
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

    except errors.APIError as error:
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

    config = create_generation_config(
        system_instruction=system_instruction,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        top_k=top_k,
    )

    logger.info("Using primary Gemini model: %s", primary_model)

    try:
        response_text = _generate_validated_response(
            client,
            primary_model,
            prompt,
            config,
        )

        logger.info("Primary model succeeded: %s", primary_model)

        return response_text

    except (
        APIQuotaExceededError,
        APIRateLimitError,
        APIServiceError,
        APIResponseTruncatedError,
    ):

        if not fallback_model:
            logger.exception(
                "Primary model failed and no fallback is configured."
            )
            raise

        logger.warning(
            "Primary model failed with an eligible error. "
            "Switching to fallback model: %s",
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
                "Fallback model succeeded: %s",
                fallback_model,
            )

            return response_text

        except TracePilotAPIError as fallback_error:
            logger.exception("Fallback model also failed.")

            raise TracePilotAPIError(
                "Both primary and fallback Gemini models failed."
            ) from fallback_error


def execute_single_model(
    model: str,
    prompt: str,
    system_instruction: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    max_output_tokens: int = 2048,
    top_k: int | None = None,
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

