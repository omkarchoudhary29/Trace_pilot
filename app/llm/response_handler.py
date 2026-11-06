
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


def extract_response_metadata(response) -> dict:
    """
    Extract useful metadata from a Gemini response.
    """

    metadata = {
        "candidate_count": 0,
        "finish_reason": None,
        "prompt_tokens": None,
        "response_tokens": None,
        "total_tokens": None
    }

    if response.candidates:
        metadata["candidate_count"] = len(response.candidates)

        candidate = response.candidates[0]

        if candidate.finish_reason:
            metadata["finish_reason"] = str(candidate.finish_reason)

    usage = response.usage_metadata

    if usage:
        metadata["prompt_tokens"] = usage.prompt_token_count
        metadata["response_tokens"] = usage.candidates_token_count
        metadata["total_tokens"] = usage.total_token_count

    return metadata
