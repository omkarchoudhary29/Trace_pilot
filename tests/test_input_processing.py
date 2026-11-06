
import pytest

from app.input.preprocessor import (
    extract_exception_details,
    extract_metadata,
    extract_traceback_location,
    normalize_error_text,
)
from app.input.redactor import redact_secrets
from app.input.validators import MAX_INPUT_LENGTH, validate_error_input

# ==========================================
# 1. INPUT VALIDATION TESTS
# ==========================================

def test_valid_error_input():
    assert validate_error_input("ValueError: Invalid input") is True


def test_empty_input():
    with pytest.raises(ValueError):
        validate_error_input("")


def test_whitespace_input():
    with pytest.raises(ValueError):
        validate_error_input("   ")


def test_non_string_input():
    with pytest.raises(TypeError):
        validate_error_input(123)


def test_input_exceeds_maximum_length():
    error_text = "A" * (MAX_INPUT_LENGTH + 1)

    with pytest.raises(ValueError):
        validate_error_input(error_text)


def test_input_at_maximum_length():
    error_text = "A" * MAX_INPUT_LENGTH

    assert validate_error_input(error_text) is True


# ==========================================
# 2. TEXT NORMALIZATION TESTS
# ==========================================

def test_windows_newline_normalization():
    text = "Line 1\r\nLine 2"

    result = normalize_error_text(text)

    assert result == "Line 1\nLine 2"


def test_old_mac_newline_normalization():
    text = "Line 1\rLine 2"

    result = normalize_error_text(text)

    assert result == "Line 1\nLine 2"


def test_leading_and_trailing_whitespace():
    text = "   Error occurred   "

    result = normalize_error_text(text)

    assert result == "Error occurred"


def test_internal_indentation_preserved():
    text = "  File test.py\n    print('hello')"

    result = normalize_error_text(text)

    assert result == "File test.py\n    print('hello')"


# ==========================================
# 3. EXCEPTION EXTRACTION TESTS
# ==========================================

def test_extract_exception_details():
    text = """
Traceback (most recent call last):
  File "main.py", line 10, in <module>
    import pandas
ModuleNotFoundError: No module named 'pandas'
"""

    result = extract_exception_details(text)

    assert result["exception_type"] == "ModuleNotFoundError"
    assert result["error_message"] == "No module named 'pandas'"


def test_extract_exception_without_message():
    text = "Traceback information without an exception"

    result = extract_exception_details(text)

    assert result["exception_type"] is None
    assert result["error_message"] is None


# ==========================================
# 4. TRACEBACK LOCATION TESTS
# ==========================================

def test_extract_traceback_location():
    text = """
Traceback (most recent call last):
  File "calculator.py", line 15, in divide
    return a / b
ZeroDivisionError: division by zero
"""

    result = extract_traceback_location(text)

    assert result["filename"] == "calculator.py"
    assert result["line_number"] == 15
    assert result["function"] == "divide"


def test_extract_missing_traceback_location():
    text = "ValueError: Invalid input"

    result = extract_traceback_location(text)

    assert result["filename"] is None
    assert result["line_number"] is None
    assert result["function"] is None


# ==========================================
# 5. COMPLETE METADATA TESTS
# ==========================================

def test_extract_complete_metadata():
    text = """
Traceback (most recent call last):
  File "app.py", line 20, in process
    result = calculate()
ValueError: Invalid calculation
"""

    result = extract_metadata(text)

    assert result["exception_type"] == "ValueError"
    assert result["error_message"] == "Invalid calculation"
    assert result["filename"] == "app.py"
    assert result["line_number"] == 20
    assert result["function"] == "process"


# ==========================================
# 6. SECRET REDACTION TESTS
# ==========================================

def test_api_key_redaction():
    text = "GEMINI_API_KEY=secret123"

    result = redact_secrets(text)

    assert "secret123" not in result
    assert "[REDACTED]" in result


def test_password_redaction():
    text = "password=my_private_password"

    result = redact_secrets(text)

    assert "my_private_password" not in result
    assert "[REDACTED]" in result


def test_bearer_token_redaction():
    text = "Authorization: Bearer abc.xyz123"

    result = redact_secrets(text)

    assert "abc.xyz123" not in result
    assert "[REDACTED]" in result


def test_database_password_redaction():
    text = "postgresql://admin:password123@localhost/db"

    result = redact_secrets(text)

    assert "password123" not in result
    assert "[REDACTED]" in result


def test_normal_error_preserved():
    text = "ModuleNotFoundError: No module named pandas"

    result = redact_secrets(text)

    assert result == text
