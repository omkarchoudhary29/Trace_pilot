from app.llm.api_handler import generate_response


def main():
    prompt = """
    Analyze this Python error:

    ModuleNotFoundError: No module named 'pandas'

    Explain:
    1. Error type
    2. Root cause
    3. Recommended fix
    """

    response = generate_response(
        prompt=prompt,
        temperature=0.2,
        max_output_tokens=1024
    )

    print("\n========== FLASH-LITE RESPONSE ==========\n")
    print(response)


if __name__ == "__main__":
    main()