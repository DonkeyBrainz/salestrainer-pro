"""Tests for FastAPI dependencies."""

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_auth_token, get_request_id


@pytest.fixture
def test_app():
    """Create a test FastAPI app with dependency endpoints."""
    from app.main import app

    @app.get("/test-request-id")
    async def test_request_id(request_id: str = Depends(get_request_id)):
        return {"request_id": request_id}

    @app.get("/test-auth-token")
    async def test_auth_token(token: str = Depends(get_auth_token)):
        return {"token": token}

    return app


@pytest.mark.asyncio
async def test_get_request_id_dependency(test_app):
    """get_request_id returns request ID from middleware."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/test-request-id")

    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert data["request_id"]  # Not empty


@pytest.mark.asyncio
async def test_get_auth_token_with_valid_bearer(test_app):
    """get_auth_token extracts token from Bearer header."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get(
            "/test-auth-token",
            headers={"Authorization": "Bearer test-token-123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["token"] == "test-token-123"


@pytest.mark.asyncio
async def test_get_auth_token_missing_header(test_app):
    """get_auth_token raises 401 if header missing (HTTPBearer behavior)."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/test-auth-token")

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data  # FastAPI's default error format


@pytest.mark.asyncio
async def test_get_auth_token_invalid_format(test_app):
    """get_auth_token raises 401 if format invalid (HTTPBearer behavior)."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # Test without "Bearer" prefix
        response = await client.get(
            "/test-auth-token",
            headers={"Authorization": "test-token-123"},
        )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data  # FastAPI's default error format


@pytest.mark.asyncio
async def test_get_auth_token_only_bearer(test_app):
    """get_auth_token raises 401 if only 'Bearer' provided (HTTPBearer behavior)."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get(
            "/test-auth-token",
            headers={"Authorization": "Bearer"},
        )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data  # FastAPI's default error format
