
from app.llm.api_handler import generate_response


def main():
    prompt = """
    Explain this Python error:

    ModuleNotFoundError: No module named 'pandas'
    """

    response = generate_response(prompt=prompt)

    print("\nGemini Response:\n")
    print(response)


if __name__ == "__main__":
    main()
