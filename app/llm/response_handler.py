
def extract_response_text(response) -> str:
    """
    Extract generated text from a Gemini response.
    """

    if not response:
        raise ValueError("Gemini returned no response.")

    if not response.candidates:
        raise ValueError("Gemini returned no response candidates.")

    if not response.text:
        raise ValueError("Gemini returned an empty text response.")

    return response.text


def extract_finish_reason(response) -> str | None:
    """
    Extract and normalize the model's generation finish reason.
    """

    if not response or not response.candidates:
        return None

    finish_reason = response.candidates[0].finish_reason

    if finish_reason is None:
        return None

    # Enum values may expose their name directly.
    if hasattr(finish_reason, "name"):
        return finish_reason.name

    return str(finish_reason).split(".")[-1]


def is_response_complete(response) -> bool:
    """
    Check whether Gemini completed generation normally.

    STOP means normal completion.
    Other reasons should not be treated as confirmed completion.
    """

    return extract_finish_reason(response) == "STOP"


def is_response_truncated(response) -> bool:
    """
    Detect whether the output was cut off by the token limit.
    """

    return extract_finish_reason(response) == "MAX_TOKENS"


def extract_response_metadata(response) -> dict:
    """
    Extract token usage and generation completion metadata.
    """

    metadata = {
        "candidate_count": 0,
        "finish_reason": None,
        "prompt_tokens": None,
        "response_tokens": None,
        "total_tokens": None,
        "is_complete": False,
        "was_truncated": False,
    }

    if not response:
        return metadata

    if response.candidates:
        metadata["candidate_count"] = len(response.candidates)

        metadata["finish_reason"] = extract_finish_reason(response)

        metadata["is_complete"] = is_response_complete(response)

        metadata["was_truncated"] = is_response_truncated(response)

    usage = response.usage_metadata

    if usage:
        metadata["prompt_tokens"] = usage.prompt_token_count
        metadata["response_tokens"] = usage.candidates_token_count
        metadata["total_tokens"] = usage.total_token_count

    return metadata
