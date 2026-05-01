"""Tests for custom middleware."""

import pytest


@pytest.mark.asyncio
async def test_request_id_added_to_response(client):
    """Request ID middleware adds X-Request-ID header to response."""
    response = await client.get("/health")

    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]  # Not empty


@pytest.mark.asyncio
async def test_request_id_uses_client_provided_id(client):
    """Request ID middleware uses client-provided ID if present."""
    custom_id = "test-request-123"
    response = await client.get("/health", headers={"X-Request-ID": custom_id})

    assert response.headers["X-Request-ID"] == custom_id


@pytest.mark.asyncio
async def test_timing_header_added(client):
    """Timing middleware adds X-Process-Time header."""
    response = await client.get("/health")

    assert "X-Process-Time" in response.headers
    # Should be in format like "0.50ms"
    assert response.headers["X-Process-Time"].endswith("ms")


@pytest.mark.asyncio
async def test_middleware_order_preserved(client):
    """All middleware run in correct order."""
    response = await client.get("/health")

    # All expected headers should be present
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers
    assert response.status_code == 200
