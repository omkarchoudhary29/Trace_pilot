
class TracePilotAPIError(Exception):
    """Base exception for TracePilot API failures."""


class APIAuthenticationError(TracePilotAPIError):
    """Invalid API credentials or insufficient permissions."""


class APIRateLimitError(TracePilotAPIError):
    """Temporary API request rate limit exceeded."""


class APIQuotaExceededError(TracePilotAPIError):
    """Model-specific daily or allocated quota exhausted."""


class APIResourceNotFoundError(TracePilotAPIError):
    """Requested model or resource was not found."""


class APIServiceError(TracePilotAPIError):
    """Gemini service or server error."""


class APITimeoutError(TracePilotAPIError):
    """Gemini API request timed out."""



class APIRequestError(TracePilotAPIError):
    """Invalid API request."""


class APIResponseTruncatedError(TracePilotAPIError):
    """The model stopped because it reached the output token limit."""


class StructuredReportError(TracePilotAPIError):
    """Base exception for structured debugging report failures."""


class ReportParsingError(StructuredReportError):
    """Failed to parse model response into JSON or extract expected structure."""


class ReportValidationError(StructuredReportError):
    """Model output failed Pydantic schema validation."""

