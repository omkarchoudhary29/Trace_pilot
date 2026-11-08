
import re

SECRET_PATTERNS = [
    # API keys, tokens, and passwords
    (
        r'(?i)\b([A-Za-z0-9_-]*(?:api[_-]?key|password|passwd|secret|auth[_-]?token|access[_-]?token))\s*[:=]\s*["\']?([^\s"\']+)',
        r'\1=[REDACTED]',
    ),
    # Bearer tokens
    (
        r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+',
        'Bearer [REDACTED]',
    ),
    # Database connection URIs (e.g. postgres://user:pass@host:5432/db)
    (
        r'(?i)(://[^:/@\s]+:)[^@\s]+(@)',
        r'\1[REDACTED]\2',
    ),
    # Google API Keys
    (
        r'\bAIza[0-9A-Za-z-_]{35}\b',
        '[REDACTED_GOOGLE_KEY]',
    ),
    # AWS Access Key IDs
    (
        r'\bAKIA[0-9A-Z]{16}\b',
        '[REDACTED_AWS_KEY]',
    ),
    # GitHub Personal Access Tokens
    (
        r'\bghp_[A-Za-z0-9]{30,40}\b',
        '[REDACTED_GITHUB_TOKEN]',
    ),
    # JSON Web Tokens (JWT)
    (
        r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b',
        '[REDACTED_JWT]',
    ),
    # Private Key blocks
    (
        r'-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY-----[\s\S]*?-----END (?:[A-Z0-9_-]+ )?PRIVATE KEY-----',
        '[REDACTED_PRIVATE_KEY]',
    ),
]


def redact_secrets(error_text: str) -> str:
    """
    Detect and redact common sensitive values, credentials, and tokens.

    LIMITATION:
    Heuristic regex redaction provides defense-in-depth but is not mathematically
    guaranteed to detect all proprietary tokens, high-entropy variable names, or
    obfuscated secrets. Organizations must ensure that untrusted production secret
    dumps are sanitized at the ingestion boundary.
    """
    if not error_text:
        return ""

    sanitized_text = error_text

    for pattern, replacement in SECRET_PATTERNS:
        sanitized_text = re.sub(
            pattern,
            replacement,
            sanitized_text,
        )

    return sanitized_text

