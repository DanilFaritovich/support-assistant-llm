class TicketProcessingError(Exception):
    """Base exception for ticket processing failures."""


class NoDepartmentsAvailableError(TicketProcessingError, ValueError):
    """Raised when no departments are available for ticket processing."""


class InvalidDepartmentSelectionError(TicketProcessingError, ValueError):
    """Raised when routing selects an unavailable department."""


class DepartmentNotFoundError(TicketProcessingError):
    """Raised when the requested department does not exist."""
