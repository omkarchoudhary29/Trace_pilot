
import re

SECRET_PATTERNS = [

    # API keys and passwords
    (
        r'(?i)\b([A-Za-z0-9_-]*(?:api[_-]?key|password|passwd|secret))\s*[:=]\s*["\']?([^\s"\']+)',
        r'\1=[REDACTED]'
    ),

    # Bearer tokens
    (
        r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+',
        'Bearer [REDACTED]'
    ),

    # Database connection credentials
    (
        r'(?i)(://[^:/@\s]+:)[^@\s]+(@)',
        r'\1[REDACTED]\2'
    )
]


def redact_secrets(error_text: str) -> str:
    """
    Detect and redact common sensitive values.
    """

    sanitized_text = error_text

    for pattern, replacement in SECRET_PATTERNS:

        sanitized_text = re.sub(
            pattern,
            replacement,
            sanitized_text
        )

    return sanitized_text
