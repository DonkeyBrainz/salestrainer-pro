"""Tests for health check endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """Health endpoint returns 200 with status."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_ready_returns_valid_response(client):
    """Ready endpoint returns valid response with dependency checks."""
    response = await client.get("/ready")

    # Status depends on whether credentials are configured
    assert response.status_code in [200, 503]
    data = response.json()
    assert data["status"] in ["ready", "degraded"]
    assert "checks" in data
    assert "database" in data["checks"]
    assert "geminiApi" in data["checks"]
    assert "secretManager" in data["checks"]
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_ready_check_structure(client):
    """Ready endpoint has correct response structure."""
    response = await client.get("/ready")

    data = response.json()
    assert data["status"] in ["ready", "degraded"]

    # Check all expected dependency checks are present
    checks = data["checks"]
    assert isinstance(checks["database"], bool)
    assert isinstance(checks["geminiApi"], bool)
    assert isinstance(checks["secretManager"], bool)


@pytest.mark.asyncio
async def test_root_returns_app_info(client):
    """Root endpoint returns app information."""
    response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "docs" in data
