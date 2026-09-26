class TicketProcessingError(Exception):
    """Base exception for ticket processing failures."""


class NoDepartmentsAvailableError(TicketProcessingError, ValueError):
    """Raised when no departments are available for ticket processing."""


class InvalidDepartmentSelectionError(TicketProcessingError, ValueError):
    """Raised when routing selects an unavailable department."""


class DepartmentNotFoundError(TicketProcessingError):
    """Raised when the requested department does not exist."""


class LLMQuotaExceededError(TicketProcessingError):
    """Raised when a client has exhausted an LLM operation quota."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("LLM operation quota exceeded.")


class LLMQuotaUnavailableError(TicketProcessingError):
    """Raised when shared LLM quota state cannot be accessed."""
