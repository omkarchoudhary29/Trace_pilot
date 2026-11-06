
class TracePilotAPIError(Exception):
    """Base exception for TracePilot API failures."""


class APIAuthenticationError(TracePilotAPIError):
    """Invalid API credentials or insufficient permissions."""


class APIRateLimitError(TracePilotAPIError):
    """API quota or rate limit exceeded."""


class APIResourceNotFoundError(TracePilotAPIError):
    """Requested model or resource was not found."""


class APIServiceError(TracePilotAPIError):
    """Gemini service or server error."""


class APIRequestError(TracePilotAPIError):
    """Invalid API request."""

