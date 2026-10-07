"""Structured exceptions for the AI Conversation subsystem.

Ensures cloud inference errors, timeouts, or invalid responses never crash the assistant.
"""


class AIError(Exception):
    """Base exception for all AI subsystem errors."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        return f"{self.message} ({self.details})" if self.details else self.message


class AIProviderError(AIError):
    """AI cloud provider returned an error or failed to process request."""
    pass


class AIAuthenticationError(AIError):
    """Invalid, missing, or unauthorized API key for the AI provider."""
    pass


class AITimeoutError(AIError):
    """AI provider request timed out."""
    pass


class AIRateLimitError(AIError):
    """AI provider quota or rate limit exceeded (HTTP 429)."""
    pass


class AIResponseError(AIError):
    """AI response was empty, blocked, truncated, or malformed."""
    pass


class AIConfigurationError(AIError):
    """Invalid or unsupported AI configuration / model."""
    pass


class EmptyPromptError(AIError):
    """User input prompt was empty or whitespace only."""
    pass
