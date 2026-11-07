
from app.llm.api_handler import generate_response

PROMPT = """
Analyze this Python error:

TypeError: unsupported operand type(s) for +: 'int' and 'str'

Explain:
1. Error classification
2. Root cause
3. Recommended fix
4. Verification steps

Do not invent information.
"""


def run_experiment():
    experiments = [
        {"name": "Baseline", "top_p": 0.9, "top_k": None},
        {"name": "Top-P 0.5", "top_p": 0.5, "top_k": None},
        {"name": "Top-P 1.0", "top_p": 1.0, "top_k": None},
        {"name": "Top-K 10", "top_p": 0.9, "top_k": 10},
        {"name": "Top-K 40", "top_p": 0.9, "top_k": 40},
    ]

    for experiment in experiments:
        print("\n" + "=" * 60)
        print("Experiment:", experiment["name"])
        print("=" * 60)

        try:
            response = generate_response(
                prompt=PROMPT,
                top_p=experiment["top_p"],
                top_k=experiment["top_k"],
            )

            print(response)

        except (ValueError, RuntimeError) as error:
            print("Experiment failed:", error)


if __name__ == "__main__":
    run_experiment()
