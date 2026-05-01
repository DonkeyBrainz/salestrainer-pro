"""Integration tests for auth endpoints.

Note: Tests requiring Firestore are skipped until GCP is configured.
"""

from httpx import AsyncClient


class TestLoginEndpoint:
    """Tests for POST /auth/login."""

    async def test_returns_google_auth_url(self, client: AsyncClient) -> None:
        """Should return Google OAuth URL with state."""
        response = await client.post("/auth/login", json={})

        assert response.status_code == 200
        data = response.json()
        assert "authUrl" in data
        assert "state" in data
        assert data["authUrl"].startswith("https://accounts.google.com")

    async def test_sets_oauth_state_cookie(self, client: AsyncClient) -> None:
        """Should set oauth_state cookie for CSRF protection."""
        response = await client.post("/auth/login", json={})

        assert response.status_code == 200
        assert "oauth_state" in response.cookies
        # Cookie should be set with security attributes
        cookie = response.cookies.get("oauth_state")
        assert cookie is not None


class TestCallbackEndpoint:
    """Tests for POST /auth/callback state validation."""

    async def test_returns_400_without_state_cookie(self, client: AsyncClient) -> None:
        """Should return 400 when oauth_state cookie is missing."""
        response = await client.get(
            "/auth/callback?code=test-code&state=test-state",
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_REQUEST"
        assert "state" in data["error"]["message"].lower()

    async def test_returns_400_with_invalid_state(self, client: AsyncClient) -> None:
        """Should return 400 when state doesn't match cookie."""
        # First get a valid state from login
        login_response = await client.post("/auth/login", json={})
        assert login_response.status_code == 200

        # Try callback with different state value
        response = await client.get(
            "/auth/callback?code=test-code&state=wrong-state",
            cookies=login_response.cookies,
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_REQUEST"

    async def test_returns_400_with_expired_state(self, client: AsyncClient) -> None:
        """Should return 400 when state cookie is tampered."""
        response = await client.get(
            "/auth/callback?code=test-code&state=test-state",
            cookies={"oauth_state": "tampered-invalid-signature"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_REQUEST"


class TestMeEndpoint:
    """Tests for GET /auth/me."""

    async def test_returns_401_without_token(self, client: AsyncClient) -> None:
        """Should return 401 when no token provided (HTTPBearer behavior)."""
        response = await client.get("/auth/me")

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    async def test_returns_401_with_invalid_token(self, client: AsyncClient) -> None:
        """Should return 401 for invalid token."""
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


class TestLogoutEndpoint:
    """Tests for POST /auth/logout."""

    async def test_returns_401_without_token(self, client: AsyncClient) -> None:
        """Should return 401 when no access token provided."""
        response = await client.post(
            "/auth/logout",
            json={"refreshToken": "test-refresh-token"},
        )

        assert response.status_code == 401


# TODO: Add tests that require Firestore once GCP is configured
# - test_returns_user_with_valid_token (needs user in DB)
# - test_refresh_with_valid_token (needs token in DB)
# - test_callback_exchanges_code (needs Google OAuth mock)
