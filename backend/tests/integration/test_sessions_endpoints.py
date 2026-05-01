"""Integration tests for session history endpoints.

Tests authentication and basic response structure.
Full functionality tests will be added once GCP/Firestore is configured.
"""

from httpx import AsyncClient


class TestListSessionsEndpoint:
    """Tests for GET /api/v1/sessions."""

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        """Should return 401 when no token provided."""
        response = await client.get("/api/v1/sessions")

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    async def test_returns_401_with_invalid_token(self, client: AsyncClient) -> None:
        """Should return 401 for invalid token."""
        response = await client.get(
            "/api/v1/sessions",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


class TestGetSessionDetailEndpoint:
    """Tests for GET /api/v1/sessions/{session_id}."""

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        """Should return 401 when no token provided."""
        response = await client.get("/api/v1/sessions/test-session-123")

        assert response.status_code == 401

    async def test_returns_401_with_invalid_token(self, client: AsyncClient) -> None:
        """Should return 401 for invalid token."""
        response = await client.get(
            "/api/v1/sessions/test-session-123",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


# TODO: Add tests with full Firestore mocking once GCP is configured:
# - test_returns_paginated_sessions
# - test_filters_by_session_type
# - test_includes_evaluation_flag
# - test_returns_404_for_missing_session
# - test_returns_403_for_unauthorized_session
# - test_returns_complete_session_detail
# - test_handles_missing_evaluation
