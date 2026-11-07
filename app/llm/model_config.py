
from google.genai import types


def create_generation_config(
    system_instruction: str | None = None
) -> types.GenerateContentConfig:
    """
    Create Gemini generation configuration.
    """

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.2,
        top_p=0.9,
        max_output_tokens=2048
    )

    return config

