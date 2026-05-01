"""Shared pytest fixtures."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Set dummy env vars for CI where .env file doesn't exist.
# These allow services to initialize without real credentials.
# Tests that exercise these services use mocks/dependency overrides.
os.environ.setdefault("GEMINI_API_KEY", "test-dummy-key")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")

from app.main import app  # noqa: E402


@pytest.fixture
async def client():
    """Async test client for API tests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
