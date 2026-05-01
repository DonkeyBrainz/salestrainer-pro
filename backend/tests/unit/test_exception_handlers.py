"""Tests for exception handlers."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import NotFoundError, UnauthorizedError
from app.main import app


@pytest.mark.asyncio
async def test_app_exception_handler():
    """AppException is handled correctly."""

    # Create a test route that raises an exception
    @app.get("/test-not-found")
    async def test_route():
        raise NotFoundError("Test resource not found")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/test-not-found")

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Test resource not found"
    assert "requestId" in data["error"]


@pytest.mark.asyncio
async def test_validation_exception_handler():
    """FastAPI validation errors are converted to standard format."""
    from pydantic import BaseModel

    class TestModel(BaseModel):
        email: str
        age: int

    @app.post("/test-validation")
    async def test_route(data: TestModel):
        return data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/test-validation",
            json={"email": "not-an-email", "age": "not-a-number"},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "Invalid request parameters"
    assert "details" in data["error"]
    assert len(data["error"]["details"]) > 0


@pytest.mark.asyncio
async def test_unauthorized_exception():
    """UnauthorizedError returns 401 with correct format."""

    @app.get("/test-unauthorized")
    async def test_route():
        raise UnauthorizedError("Custom auth error")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/test-unauthorized")

    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "Custom auth error"


@pytest.mark.asyncio
async def test_generic_exception_handler():
    """Unhandled exceptions return 500 with standard format.

    Note: Due to Python 3.14's exception group handling in Starlette middleware,
    we test the exception handler directly rather than through the full stack.
    In production, the handler works correctly for exceptions raised in routes
    defined at application startup.
    """
    from app.main import generic_exception_handler

    # Create a mock request with request_id
    class MockState:
        request_id = "test-request-123"

    class MockRequest:
        state = MockState()

    request = MockRequest()
    exc = ValueError("Unexpected error")

    # Call the exception handler directly
    response = await generic_exception_handler(request, exc)

    assert response.status_code == 500
    assert response.body is not None

    import json

    data = json.loads(response.body)
    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert data["error"]["message"] == "An unexpected error occurred"
    assert data["error"]["requestId"] == "test-request-123"
    # Should not expose internal error details
    assert "ValueError" not in data["error"]["message"]
