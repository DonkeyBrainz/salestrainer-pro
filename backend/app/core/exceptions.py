"""Custom exception classes for the application.

These exceptions map to the error codes defined in the API specification.
"""

from typing import Any


class AppError(Exception):
    """Base exception for all application errors.

    Attributes:
        code: Error code as defined in API spec
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details (e.g., validation errors)
    """

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


class ValidationError(AppError):
    """Raised when request validation fails.

    HTTP 400 - VALIDATION_ERROR
    """

    def __init__(
        self,
        message: str = "Invalid request parameters",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class InvalidRequestError(AppError):
    """Raised when request body is malformed.

    HTTP 400 - INVALID_REQUEST
    """

    def __init__(self, message: str = "Malformed request body") -> None:
        super().__init__(
            message=message,
            code="INVALID_REQUEST",
            status_code=400,
        )


class UnauthorizedError(AppError):
    """Raised when authentication is missing or invalid.

    HTTP 401 - UNAUTHORIZED
    """

    def __init__(self, message: str = "Missing or invalid authentication") -> None:
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
        )


class TokenExpiredError(AppError):
    """Raised when access token has expired.

    HTTP 401 - TOKEN_EXPIRED
    """

    def __init__(self, message: str = "Access token has expired") -> None:
        super().__init__(
            message=message,
            code="TOKEN_EXPIRED",
            status_code=401,
        )


class ForbiddenError(AppError):
    """Raised when user lacks permissions for resource.

    HTTP 403 - FORBIDDEN
    """

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
        )


class NotFoundError(AppError):
    """Raised when requested resource doesn't exist.

    HTTP 404 - NOT_FOUND
    """

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
        )


class ConflictError(AppError):
    """Raised when resource already exists.

    HTTP 409 - CONFLICT
    """

    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
        )


class RateLimitError(AppError):
    """Raised when rate limit is exceeded.

    HTTP 429 - RATE_LIMITED
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="RATE_LIMITED",
            status_code=429,
            details=[{"retryAfter": retry_after}] if retry_after else [],
        )
        self.retry_after = retry_after


class InternalError(AppError):
    """Raised for unexpected server errors.

    HTTP 500 - INTERNAL_ERROR
    """

    def __init__(self, message: str = "An unexpected error occurred") -> None:
        super().__init__(
            message=message,
            code="INTERNAL_ERROR",
            status_code=500,
        )


class ServiceUnavailableError(AppError):
    """Raised when a dependency is unavailable.

    HTTP 503 - SERVICE_UNAVAILABLE
    """

    def __init__(self, message: str = "Service temporarily unavailable") -> None:
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=503,
        )
