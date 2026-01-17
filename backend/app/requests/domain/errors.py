class DomainError(Exception):
    """Base domain error with a user-facing message."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class PermissionDenied(DomainError):
    """Raised when the user has insufficient permissions."""


class NotFound(DomainError):
    """Raised when a required entity is missing."""


class InvalidRequest(DomainError):
    """Raised when the request is not in a valid state."""
