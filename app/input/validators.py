MAX_INPUT_LENGTH = 20000


def validate_error_input(error_text):

    # Check whether input is a string
    if not isinstance(error_text, str):
        raise TypeError("Error input must be a string.")

    # Check whether input is empty
    if not error_text.strip():
        raise ValueError("Error input cannot be empty.")

    # Check maximum input length
    if len(error_text) > MAX_INPUT_LENGTH:
        raise ValueError(
            f"Error input exceeds the maximum limit "
            f"of {MAX_INPUT_LENGTH} characters."
        )

    return True