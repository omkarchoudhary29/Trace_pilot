
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

REQUEST_TIMEOUT_MS = 30000


def create_gemini_client():
    """
    Load Gemini configuration and create a reusable client
    with an HTTP timeout.
    """

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from environment.")

    http_options = types.HttpOptions(
        timeout=REQUEST_TIMEOUT_MS
    )

    client = genai.Client(
        api_key=api_key,
        http_options=http_options
    )

    return client
