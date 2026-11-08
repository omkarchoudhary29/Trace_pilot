
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

DEFAULT_REQUEST_TIMEOUT_MS = 30000


def get_configured_timeout_ms(custom_timeout_seconds: int | None = None) -> int:
    """Calculate request timeout in milliseconds with safe bounds (1s to 300s)."""
    if custom_timeout_seconds is not None:
        timeout_sec = custom_timeout_seconds
    else:
        try:
            timeout_sec = int(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "30"))
        except ValueError:
            timeout_sec = 30

    # Enforce safe boundary limits: between 1 and 300 seconds
    clamped_sec = max(1, min(300, timeout_sec))
    return clamped_sec * 1000


def create_gemini_client(timeout_seconds: int | None = None):
    """
    Load Gemini configuration and create a reusable client
    with a bounded HTTP timeout.
    """

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from environment.")

    timeout_ms = get_configured_timeout_ms(timeout_seconds)

    http_options = types.HttpOptions(
        timeout=timeout_ms
    )

    client = genai.Client(
        api_key=api_key,
        http_options=http_options
    )

    return client
