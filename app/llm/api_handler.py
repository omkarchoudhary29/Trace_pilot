
import os

from dotenv import load_dotenv
from google.genai import errors

from app.llm.client import create_gemini_client
from app.llm.exceptions import (
    APIAuthenticationError,
    APIRateLimitError,
    APIRequestError,
    APIResourceNotFoundError,
    APIServiceError,
    TracePilotAPIError,
)
from app.llm.logger import get_logger
from app.llm.model_config import create_generation_config
from app.llm.response_handler import extract_response_metadata, extract_response_text
from app.llm.retry_handler import execute_with_retry

load_dotenv()
logger = get_logger("TracePilot.API")

def classify_api_error(error: Exception) -> TracePilotAPIError:
    """
    Convert Gemini SDK errors into TracePilot exceptions.
    """

    if isinstance(error, errors.ClientError):
        status_code = getattr(error, "code", None)

        if status_code in (401, 403):
            return APIAuthenticationError(
                "Gemini authentication or permission failed."
            )

        if status_code == 429:
            return APIRateLimitError(
                "Gemini API rate limit or quota exceeded."
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



def generate_response(
    prompt: str,
    system_instruction: str | None = None
) -> str:

    # STEP 1: Load model name
    model = os.getenv("GEMINI_MODEL")

    # STEP 2: Validate model
    if not model:
        raise ValueError("GEMINI_MODEL is missing from environment.")

    # STEP 3: Validate prompt
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    # STEP 4: Log request
    logger.info("Sending request to Gemini model: %s", model)

    try:
        # STEP 5: Create client and configuration
        client = create_gemini_client()
        config = create_generation_config(system_instruction)

        # STEP 6: Send request with retry
        response = execute_with_retry(
            client.models.generate_content,
            model=model,
            contents=prompt,
            config=config
        )

        # STEP 7: Process response
        response_text = extract_response_text(response)
        metadata = extract_response_metadata(response)

        logger.info("Gemini response received successfully.")
        logger.info("Gemini response metadata: %s", metadata)

        return response_text

    except errors.APIError as error:
        logger.exception("Gemini API request failed.")
        raise classify_api_error(error) from error
