def normalize_error_text(error_text: str) -> str:
    """
    Normalize error text while preserving traceback formatting.
    """

    # Convert Windows line endings to Unix line endings
    normalized_text = error_text.replace("\r\n", "\n")

    # Convert remaining carriage returns to Unix line endings
    normalized_text = normalized_text.replace("\r", "\n")

    # Remove whitespace only from the beginning and end
    normalized_text = normalized_text.strip()

    return normalized_text


import re


def extract_exception_details(error_text: str) -> dict:
    """
    Extract exception type and message from error text.
    """

    exception_pattern = r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)"

    matches = re.findall(exception_pattern, error_text)

    if matches:
        exception_type, error_message = matches[-1]
    else:
        exception_type = None
        error_message = None

    return {
        "exception_type": exception_type,
        "error_message": error_message
    }


def extract_traceback_location(error_text: str) -> dict:
    """
    Extract filename, line number and function from traceback.
    """

    location_pattern = (
        r'File "([^"]+)", line (\d+), in ([^\n]+)'
    )

    matches = re.findall(location_pattern, error_text)

    if matches:
        filename, line_number, function = matches[-1]

        line_number = int(line_number)

    else:
        filename = None
        line_number = None
        function = None

    return {
        "filename": filename,
        "line_number": line_number,
        "function": function
    }

def extract_metadata(error_text: str) -> dict:
    """
    Extract all available metadata from an error.
    """

    exception_details = extract_exception_details(error_text)

    traceback_location = extract_traceback_location(error_text)

    metadata = {
        **exception_details,
        **traceback_location
    }

    return metadata

