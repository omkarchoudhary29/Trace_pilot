
from google.genai import types


def create_generation_config(
    system_instruction: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    max_output_tokens: int = 2048,
    top_k: int | None = None,
    response_mime_type: str | None = None,
    response_schema: type | None = None,
) -> types.GenerateContentConfig:

    if not 0.0 <= temperature <= 2.0:
        raise ValueError("Temperature must be between 0 and 2.")

    if not 0.0 < top_p <= 1.0:
        raise ValueError("Top P must be greater than 0 and at most 1.")

    if max_output_tokens <= 0:
        raise ValueError("Max output tokens must be positive.")

    if top_k is not None and top_k <= 0:
        raise ValueError("Top K must be a positive integer.")

    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        max_output_tokens=max_output_tokens,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
    )
