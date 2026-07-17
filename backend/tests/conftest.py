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
# Force the default live provider to gemini (fully mockable) regardless of a
# developer's local .env — e.g. LIVE_PROVIDER=nova for manual live-testing —
# since websocket tests build a real provider client via get_live_provider()
# and only mock GeminiService, not the AWS/Bedrock SDK.
os.environ.setdefault("LIVE_PROVIDER", "gemini")
# Dummy Langfuse keys + tracing disabled: a missing public_key logs a warning
# at client-init time regardless of the tracing_enabled flag, which pollutes
# caplog-based assertions; tracing_enabled=false additionally guarantees no
# network export attempts happen during tests.
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-lf-test-dummy")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-lf-test-dummy")
os.environ.setdefault("LANGFUSE_TRACING_ENABLED", "false")

from app.main import app  # noqa: E402


@pytest.fixture
async def client():
    """Async test client for API tests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
