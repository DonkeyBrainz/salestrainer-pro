"""Tests for exception handlers."""

from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    InternalError,
    InvalidRequestError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    TokenExpiredError,
    UnauthorizedError,
    ValidationError,
)


def test_validation_error():
    """ValidationError has correct code and status."""
    error = ValidationError("Test message", details=[{"field": "test", "message": "error"}])

    assert error.code == "VALIDATION_ERROR"
    assert error.status_code == 400
    assert error.message == "Test message"
    assert len(error.details) == 1


def test_invalid_request_error():
    """InvalidRequestError has correct code and status."""
    error = InvalidRequestError()

    assert error.code == "INVALID_REQUEST"
    assert error.status_code == 400


def test_unauthorized_error():
    """UnauthorizedError has correct code and status."""
    error = UnauthorizedError()

    assert error.code == "UNAUTHORIZED"
    assert error.status_code == 401


def test_token_expired_error():
    """TokenExpiredError has correct code and status."""
    error = TokenExpiredError()

    assert error.code == "TOKEN_EXPIRED"
    assert error.status_code == 401


def test_forbidden_error():
    """ForbiddenError has correct code and status."""
    error = ForbiddenError()

    assert error.code == "FORBIDDEN"
    assert error.status_code == 403


def test_not_found_error():
    """NotFoundError has correct code and status."""
    error = NotFoundError("Resource not found")

    assert error.code == "NOT_FOUND"
    assert error.status_code == 404
    assert error.message == "Resource not found"


def test_conflict_error():
    """ConflictError has correct code and status."""
    error = ConflictError()

    assert error.code == "CONFLICT"
    assert error.status_code == 409


def test_rate_limit_error():
    """RateLimitError has correct code and status."""
    error = RateLimitError(retry_after=60)

    assert error.code == "RATE_LIMITED"
    assert error.status_code == 429
    assert error.retry_after == 60
    assert len(error.details) == 1


def test_internal_error():
    """InternalError has correct code and status."""
    error = InternalError()

    assert error.code == "INTERNAL_ERROR"
    assert error.status_code == 500


def test_service_unavailable_error():
    """ServiceUnavailableError has correct code and status."""
    error = ServiceUnavailableError()

    assert error.code == "SERVICE_UNAVAILABLE"
    assert error.status_code == 503


def test_base_app_error():
    """AppError can be instantiated with custom values."""
    error = AppError(
        message="Custom error",
        code="CUSTOM_CODE",
        status_code=418,
        details=[{"key": "value"}],
    )

    assert error.message == "Custom error"
    assert error.code == "CUSTOM_CODE"
    assert error.status_code == 418
    assert len(error.details) == 1
