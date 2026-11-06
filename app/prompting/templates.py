DEBUGGING_PROMPT_TEMPLATE = """
Analyze the following software error.

ERROR INPUT:
{error_text}

ADDITIONAL CONTEXT:
{additional_context}

PROGRAMMING LANGUAGE:
{programming_language}

Provide a debugging report containing:

1. Error classification.
2. Simple explanation.
3. Likely root cause.
4. Evidence from the supplied input.
5. Recommended debugging steps.
6. Possible fixes.
7. Verification steps.

RULES:
- Do not invent filenames or line numbers.
- Clearly distinguish facts from hypotheses.
- If context is unavailable, state that.
- Do not claim that you executed or tested the code.
"""


def build_debugging_prompt(
    error_text: str,
    additional_context: str = "Not provided",
    programming_language: str = "Unknown"
) -> str:

    prompt = DEBUGGING_PROMPT_TEMPLATE.format(
        error_text=error_text,
        additional_context=additional_context,
        programming_language=programming_language
    )

    return prompt