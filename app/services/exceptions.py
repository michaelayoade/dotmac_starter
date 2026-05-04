class DomainError(Exception):
    """Base class for service-layer errors."""


class BadRequestError(DomainError):
    """Raised when caller input is invalid."""


class ConflictError(DomainError):
    """Raised when a domain uniqueness or state conflict occurs."""


class NotFoundError(DomainError):
    """Raised when a requested domain object does not exist."""


class RateLimitError(DomainError):
    """Raised when caller exceeds a configured rate limit."""


class ServiceUnavailableError(DomainError):
    """Raised when a required backing service is unavailable."""
