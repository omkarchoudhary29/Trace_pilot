
import logging
import re
from pathlib import Path

DEFAULT_LOG_DIRECTORY = Path("logs")
DEFAULT_LOG_FILE = DEFAULT_LOG_DIRECTORY / "tracepilot.log"

SENSITIVE_LOG_PATTERNS = [
    (r'(?i)\b([A-Za-z0-9_-]*(?:api[_-]?key|password|passwd|secret|token))\s*[:=]\s*["\']?([^\s"\']+)', r'\1=[REDACTED]'),
    (r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+', 'Bearer [REDACTED]'),
    (r'(?i)(://[^:/@\s]+:)[^@\s]+(@)', r'\1[REDACTED]\2'),
    (r'AIza[0-9A-Za-z-_]{35}', '[REDACTED_API_KEY]'),
]


def sanitize_for_logging(message: str) -> str:
    """Scrub sensitive credentials from log messages prior to output."""
    if not isinstance(message, str):
        return str(message)

    sanitized = message
    for pattern, replacement in SENSITIVE_LOG_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized


class SensitiveDataFilter(logging.Filter):
    """Logging filter ensuring secrets are never persisted in log streams."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_for_logging(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: sanitize_for_logging(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, (tuple, list)):
                record.args = tuple(
                    sanitize_for_logging(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True


def get_logger(name: str = "TracePilot", log_file: Path | None = None) -> logging.Logger:
    """
    Create and return a configured, secret-safe application logger.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    secret_filter = SensitiveDataFilter()
    logger.addFilter(secret_filter)

    target_file = log_file or DEFAULT_LOG_FILE
    target_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(
        target_file,
        encoding="utf-8",
    )
    console_handler = logging.StreamHandler()

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    file_handler.addFilter(secret_filter)
    console_handler.addFilter(secret_filter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

