
import random
import time

from app.llm.exceptions import APIRateLimitError, APIServiceError

MAX_RETRIES = 3
BASE_DELAY = 1


def execute_with_retry(function, *args, **kwargs):
    """
    Execute a function with exponential backoff.

    Retries only rate-limit and temporary service errors.
    """

    for attempt in range(MAX_RETRIES + 1):
        try:
            return function(*args, **kwargs)

        except (APIRateLimitError, APIServiceError):

            if attempt == MAX_RETRIES:
                raise

            delay = BASE_DELAY * (2 ** attempt)
            jitter = random.uniform(0, 0.5)

            wait_time = delay + jitter

            print(
                f"Temporary API failure. "
                f"Retrying in {wait_time:.2f} seconds..."
            )

            time.sleep(wait_time)
