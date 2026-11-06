REASONING_DEBUGGING_PROMPT = """
Analyze the supplied software error using a structured
evidence-based debugging process.

ERROR INPUT:
{error_text}

Follow these stages:

STAGE 1: ERROR IDENTIFICATION
- Identify the exception or error type.
- Extract the error message.

STAGE 2: EVIDENCE
- Identify relevant information directly present in the input.
- Include filenames and line numbers only if provided.
- Quote short relevant evidence excerpts.

STAGE 3: INTERPRETATION
- Explain what the evidence establishes.
- Explain what cannot be determined from the input.

STAGE 4: ROOT-CAUSE HYPOTHESES
- List plausible causes.
- Rank them according to available evidence.
- Do not present hypotheses as confirmed facts.

STAGE 5: DEBUGGING RECOMMENDATIONS
- Give actionable debugging steps.
- Suggest possible fixes.
- Avoid assuming access to files or systems you cannot inspect.

STAGE 6: VERIFICATION
- Explain how the developer can verify a proposed fix.

FINAL RULES:
- Never invent evidence.
- Clearly separate facts from hypotheses.
- Communicate uncertainty.
- Do not claim to have executed code.
- Do not reveal private internal reasoning.
- Provide a concise explanation of the conclusions.
"""