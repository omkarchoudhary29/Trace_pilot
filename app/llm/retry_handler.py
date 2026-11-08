
import os
import random
import time

from google.genai import errors

from app.llm.exceptions import (
    APIRateLimitError,
    APIServiceError,
    APITimeoutError,
)
from app.llm.logger import get_logger

DEFAULT_MAX_RETRIES = 2
DEFAULT_BASE_DELAY = 1.0

logger = get_logger("TracePilot.Retry")


def is_retryable_error(error: Exception) -> bool:
    """
    Identify temporary errors that can be retried.

    Retries:
    - APIRateLimitError (temporary request throttling)
    - APIServiceError (transient server errors)
    - APITimeoutError (network or request timeouts)
    - Google ServerError with HTTP 500, 502, 503, 504

    Never retries:
    - APIQuotaExceededError (daily/allocated quota exhausted)
    - APIAuthenticationError (invalid credentials)
    - APIRequestError (malformed requests)
    - APIResponseTruncatedError (token limit reached)
    """

    if isinstance(error, (APIRateLimitError, APIServiceError, APITimeoutError)):
        return True

    if isinstance(error, errors.ServerError):
        return getattr(error, "code", None) in (500, 502, 503, 504)

    return False


def get_retry_configuration(
    custom_max_retries: int | None = None,
    custom_base_delay: float | None = None,
) -> tuple[int, float]:
    """Resolve and clamp retry bounds to prevent unbounded retry loops."""
    if custom_max_retries is not None:
        retries = custom_max_retries
    else:
        try:
            retries = int(os.getenv("GEMINI_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)))
        except ValueError:
            retries = DEFAULT_MAX_RETRIES

    if custom_base_delay is not None:
        delay = custom_base_delay
    else:
        try:
            delay = float(os.getenv("GEMINI_RETRY_BASE_DELAY", str(DEFAULT_BASE_DELAY)))
        except ValueError:
            delay = DEFAULT_BASE_DELAY

    # Clamping: maximum 5 retries, minimum 0 retries; delay between 0.1s and 30s
    clamped_retries = max(0, min(5, retries))
    clamped_delay = max(0.1, min(30.0, delay))

    return clamped_retries, clamped_delay


def execute_with_retry(
    function,
    *args,
    max_retries: int | None = None,
    base_delay: float | None = None,
    **kwargs,
):
    """
    Execute a function with exponential backoff and randomized jitter.
    """
    retries, delay_base = get_retry_configuration(max_retries, base_delay)

    for attempt in range(retries + 1):

        try:
            return function(*args, **kwargs)

        except Exception as error:

            if not is_retryable_error(error):
                raise

            if attempt == retries:
                logger.error(
                    "Exhausted all %d retries for %s: %s",
                    retries,
                    getattr(function, "__name__", "operation"),
                    error,
                )
                raise

            delay = delay_base * (2 ** attempt)
            jitter = random.uniform(0.0, 0.5)
            wait_time = delay + jitter

            logger.warning(
                "Transient error encountered (%s). Retry attempt %d/%d in %.2fs...",
                type(error).__name__,
                attempt + 1,
                retries,
                wait_time,
            )

            time.sleep(wait_time)
