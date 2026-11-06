
import os

from dotenv import load_dotenv
from google import genai


def create_gemini_client():
    """
    Load Gemini configuration and create a reusable client.
    """

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from environment.")

    client = genai.Client(api_key=api_key)

    return client
