
from app.llm.api_handler import generate_response

DEBUGGING_PROMPT = """
Analyze the following Python error.

Error:
ModuleNotFoundError: No module named 'pandas'

Provide:
1. Error classification.
2. Simple explanation.
3. Likely root cause.
4. Recommended debugging steps.
5. Possible fix.
6. Verification steps.

Be technically accurate.
Do not invent information.
"""


SYSTEM_INSTRUCTION = """
You are TracePilot, a professional software debugging assistant.

Provide accurate, clear and evidence-based explanations.
Separate observed facts from possible causes.
Do not claim to have executed code.
"""


TEMPERATURE_VALUES = [0.0, 0.2, 0.7, 1.0]


def run_temperature_experiment():

    for temperature in TEMPERATURE_VALUES:

        print("\n" + "=" * 60)
        print(f"TEMPERATURE EXPERIMENT: {temperature}")
        print("=" * 60)

        response = generate_response(
            prompt=DEBUGGING_PROMPT,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=temperature,
            max_output_tokens=1024
        )

        print("\nMODEL OUTPUT:")
        print(response)


if __name__ == "__main__":
    run_temperature_experiment()
