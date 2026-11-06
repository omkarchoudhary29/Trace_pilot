
from app.input.preprocessor import extract_metadata, normalize_error_text
from app.input.redactor import redact_secrets
from app.input.validators import validate_error_input
from app.llm.api_handler import generate_response
from app.prompting.system_prompts import TRACEPILOT_SYSTEM_PROMPT
from app.prompting.user_messages import build_user_message


def run_tracepilot(error_text: str) -> str:
    """
    Main TracePilot pipeline.

    Input → Validation → Normalization → Metadata
    → Redaction → Prompt → Gemini → Response
    """

    # STEP 1: Validate input
    validate_error_input(error_text)

    # STEP 2: Normalize input
    normalized_text = normalize_error_text(error_text)

    # STEP 3: Extract metadata
    metadata = extract_metadata(normalized_text)

    # STEP 4: Redact sensitive information
    sanitized_text = redact_secrets(normalized_text)

    # STEP 5: Build user prompt
    user_message = build_user_message(sanitized_text)

    # STEP 6: Generate Gemini response
    response = generate_response(
        prompt=user_message,
        system_instruction=TRACEPILOT_SYSTEM_PROMPT
    )

    # STEP 7: Display metadata and analysis
    print("\nTRACEPILOT DEBUGGING ANALYSIS")
    print("=" * 55)

    print("\nEXTRACTED METADATA")
    print("-" * 55)

    for key, value in metadata.items():
        print(f"{key}: {value}")

    print("\nAI DEBUGGING REPORT")
    print("-" * 55)
    print(response)

    return response


if __name__ == "__main__":

    error_text = """
    Traceback (most recent call last):
      File "main.py", line 10, in <module>
        import pandas
    ModuleNotFoundError: No module named pandas
    """

    run_tracepilot(error_text)
