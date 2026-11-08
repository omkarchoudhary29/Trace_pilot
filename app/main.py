
from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

# Ensure project root is on sys.path when executed directly as a script
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.input.preprocessor import extract_metadata, normalize_error_text
from app.input.redactor import redact_secrets
from app.input.validators import validate_error_input
from app.llm.api_handler import generate_response
from app.llm.streaming import generate_response_stream
from app.prompting.system_prompts import (
    STRUCTURED_DEBUGGING_SYSTEM_PROMPT,
    TRACEPILOT_SYSTEM_PROMPT,
)
from app.prompting.user_messages import (
    build_structured_user_message,
    build_user_message,
)
from app.schemas.debugging_report import (
    DebuggingReport,
    parse_structured_debugging_report,
)


def run_tracepilot(
    error_text: str,
    structured: bool = True,
    stream: bool = False,
    on_chunk: Callable[[str], None] | None = None,
) -> DebuggingReport | str:
    """
    Main TracePilot pipeline.

    Raw error
    → Input validation
    → Normalization
    → Secret redaction
    → Metadata extraction
    → Prompt construction
    → Gemini generation (non-streaming or streaming)
    → Structured parsing & Pydantic validation
    → Debugging report
    """

    # STEP 1: Validate input
    validate_error_input(error_text)

    # STEP 2: Normalize input
    normalized_text = normalize_error_text(error_text)

    # STEP 3: Redact sensitive information first
    sanitized_text = redact_secrets(normalized_text)

    # STEP 4: Extract metadata from sanitized content
    metadata = extract_metadata(sanitized_text)

    # STEP 5: Streaming execution path
    if stream:
        if structured:
            user_message = build_structured_user_message(sanitized_text, metadata)
            stream_gen = generate_response_stream(
                prompt=user_message,
                system_instruction=STRUCTURED_DEBUGGING_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=DebuggingReport,
            )
            final_report = None
            raw_text = ""
            for event in stream_gen:
                if event.event_type == "text_chunk":
                    delta = event.data.get("delta", "")
                    if on_chunk:
                        on_chunk(delta)
                    else:
                        print(delta, end="", flush=True)
                elif event.event_type == "completed":
                    final_report = event.data.get("report")
                    raw_text = event.data.get("raw_text", "")

            if final_report is not None:
                print("\n" + "=" * 60)
                print("TRACEPILOT STRUCTURED DEBUGGING REPORT (STREAMED)")
                print("=" * 60)
                print(final_report.to_markdown())
                return final_report
            return raw_text

        # Unstructured streaming
        user_message = build_user_message(sanitized_text)
        stream_gen = generate_response_stream(
            prompt=user_message,
            system_instruction=TRACEPILOT_SYSTEM_PROMPT,
        )
        raw_text = ""
        for event in stream_gen:
            if event.event_type == "text_chunk":
                delta = event.data.get("delta", "")
                if on_chunk:
                    on_chunk(delta)
                else:
                    print(delta, end="", flush=True)
            elif event.event_type == "completed":
                raw_text = event.data.get("raw_text", "")

        return raw_text

    # Non-streaming structured path
    if structured:
        user_message = build_structured_user_message(sanitized_text, metadata)
        raw_response = generate_response(
            prompt=user_message,
            system_instruction=STRUCTURED_DEBUGGING_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=DebuggingReport,
        )
        report = parse_structured_debugging_report(raw_response)

        print("\n" + "=" * 60)
        print("TRACEPILOT STRUCTURED DEBUGGING REPORT")
        print("=" * 60)
        print(report.to_markdown())

        return report

    # Legacy unstructured plain-text fallback
    user_message = build_user_message(sanitized_text)
    response = generate_response(
        prompt=user_message,
        system_instruction=TRACEPILOT_SYSTEM_PROMPT,
    )

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
