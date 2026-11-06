
from google.genai import errors

from app.llm.api_handler import classify_api_error
from app.llm.exceptions import (
    APIAuthenticationError,
    APIRateLimitError,
    APIRequestError,
    APIResourceNotFoundError,
    APIServiceError,
)

test_cases = [
    (401, APIAuthenticationError),
    (403, APIAuthenticationError),
    (404, APIResourceNotFoundError),
    (429, APIRateLimitError),
    (400, APIRequestError),
    (500, APIServiceError)
]

print("API EXCEPTION CLASSIFICATION TEST")
print("=" * 50)

for status_code, expected_exception in test_cases:
    if status_code >= 500:
        sdk_error = errors.ServerError(
            status_code,
            {"error": {"message": "Test server error"}}
        )
    else:
        sdk_error = errors.ClientError(
            status_code,
            {"error": {"message": "Test client error"}}
        )

    result = classify_api_error(sdk_error)

    assert isinstance(result, expected_exception)

    print(f"{status_code} → {type(result).__name__}")

print("\nAll exception classification tests passed.")
