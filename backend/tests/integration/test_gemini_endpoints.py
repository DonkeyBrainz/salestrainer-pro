"""Integration tests for Gemini API endpoints."""

from fastapi import status
from httpx import AsyncClient


class TestGenerateEndpoint:
    """Tests for POST /api/v1/gemini/generate endpoint."""

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        """Should return 401 if no auth token provided (HTTPBearer behavior)."""
        response = await client.post(
            "/api/v1/gemini/generate",
            json={"prompt": "Test prompt"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.json()
