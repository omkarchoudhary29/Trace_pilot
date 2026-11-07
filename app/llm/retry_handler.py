
import random
import time

from google.genai import errors

from app.llm.exceptions import APIRateLimitError, APIServiceError

MAX_RETRIES = 2
BASE_DELAY = 1


def is_retryable_error(error: Exception) -> bool:
    """
    Identify temporary errors that can be retried.
    """

    if isinstance(error, (APIRateLimitError, APIServiceError)):
        return True

    if isinstance(error, errors.ServerError):
        return error.code in (500, 502, 503, 504)

    # Do not retry every 429.
    # Daily quota exhaustion should move to fallback.
    return False


def execute_with_retry(function, *args, **kwargs):
    """
    Execute a function with exponential backoff and jitter.
    """

    for attempt in range(MAX_RETRIES + 1):

        try:
            return function(*args, **kwargs)

        except Exception as error:

            if not is_retryable_error(error):
                raise

            if attempt == MAX_RETRIES:
                raise

            delay = BASE_DELAY * (2 ** attempt)
            jitter = random.uniform(0, 0.5)

            wait_time = delay + jitter

            print(
                f"Temporary API failure. "
                f"Retry attempt {attempt + 1}/{MAX_RETRIES} "
                f"in {wait_time:.2f} seconds..."
            )

            time.sleep(wait_time)
