from app.input.redactor import redact_secrets


def test_gemini_api_key():
    text = "GEMINI_API_KEY=secret123"
    result = redact_secrets(text)

    assert "secret123" not in result
    assert "[REDACTED]" in result


def test_bearer_token():
    text = "Authorization: Bearer abc.xyz123"
    result = redact_secrets(text)

    assert "abc.xyz123" not in result


def test_database_password():
    text = "postgresql://admin:password123@localhost/db"
    result = redact_secrets(text)

    assert "password123" not in result


def test_normal_error():
    text = "ModuleNotFoundError: No module named pandas"
    result = redact_secrets(text)

    assert result == text