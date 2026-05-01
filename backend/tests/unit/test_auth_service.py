"""Tests for AuthService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from jose import jwt

from app.config import Settings
from app.core.exceptions import (
    ForbiddenError,
    InvalidRequestError,
    TokenExpiredError,
    UnauthorizedError,
)
from app.models.auth import GoogleUserInfo, MicrosoftUserInfo
from app.models.user import User, UserPreferences
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for tests."""
    return Settings(
        secret_key="test-secret-key-that-is-long-enough-for-jwt",
        google_client_id="test-client-id",
        google_client_secret="test-client-secret",
        google_redirect_uri="http://localhost:5173/auth/callback",
        jwt_algorithm="HS256",
        jwt_expire_minutes=60,
        refresh_token_expire_days=30,
        allowed_email_domains=[],
        azure_client_id="test-azure-client-id",
        azure_client_secret="test-azure-client-secret",
        azure_tenant_id="test-tenant-id",
        azure_redirect_uri="http://localhost:5173/auth/callback",
    )


@pytest.fixture
def mock_user_repository() -> AsyncMock:
    """Create mock user repository."""
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def mock_token_repository() -> AsyncMock:
    """Create mock token repository."""
    return AsyncMock(spec=TokenRepository)


@pytest.fixture
def auth_service(
    mock_settings: Settings,
    mock_user_repository: AsyncMock,
    mock_token_repository: AsyncMock,
) -> AuthService:
    """Create AuthService with mocked dependencies."""
    return AuthService(
        settings=mock_settings,
        user_repository=mock_user_repository,
        token_repository=mock_token_repository,
    )


@pytest.fixture
def sample_user() -> User:
    """Create sample user for tests."""
    return User(
        user_id="user-123",
        email="test@example.com",
        name="Test User",
        google_id="google-123",
        picture_url="https://example.com/pic.jpg",
        preferences=UserPreferences(),
        created_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
        updated_at=None,
    )


class TestGenerateAuthUrl:
    """Tests for generate_auth_url method."""

    def test_returns_google_auth_url(self, auth_service: AuthService) -> None:
        """Should return URL pointing to Google OAuth."""
        result = auth_service.generate_auth_url("http://localhost:3000/callback")

        assert result.auth_url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "client_id=test-client-id" in result.auth_url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fcallback" in result.auth_url

    def test_generates_state_parameter(self, auth_service: AuthService) -> None:
        """Should generate random state for CSRF protection."""
        result = auth_service.generate_auth_url("http://localhost:3000/callback")

        assert result.state
        assert len(result.state) > 20  # Should be cryptographically random

    def test_includes_required_scopes(self, auth_service: AuthService) -> None:
        """Should include required OAuth scopes."""
        result = auth_service.generate_auth_url("http://localhost:3000/callback")

        assert "scope=openid+email+profile" in result.auth_url


class TestExchangeCode:
    """Tests for exchange_code method."""

    async def test_raises_error_on_invalid_state(self, auth_service: AuthService) -> None:
        """Should raise InvalidRequestError if state doesn't match."""
        with pytest.raises(InvalidRequestError, match="Invalid state parameter"):
            await auth_service.exchange_code(
                code="auth-code",
                state="wrong-state",
                expected_state="expected-state",
                redirect_uri="http://localhost:3000/callback",
            )

    async def test_exchanges_code_and_returns_tokens(
        self,
        auth_service: AuthService,
        mock_user_repository: AsyncMock,
        mock_token_repository: AsyncMock,
        sample_user: User,
    ) -> None:
        """Should exchange code and return JWT tokens."""
        mock_user_repository.upsert_from_google.return_value = sample_user

        with (
            patch.object(
                auth_service,
                "_exchange_google_code",
                return_value={"access_token": "google-token"},
            ),
            patch.object(
                auth_service,
                "_fetch_google_user_info",
                return_value=GoogleUserInfo(
                    id="google-123",
                    email="test@example.com",
                    name="Test User",
                ),
            ),
        ):
            result = await auth_service.exchange_code(
                code="valid-code",
                state="same-state",
                expected_state="same-state",
                redirect_uri="http://localhost:3000/callback",
            )

        assert result.access_token
        assert result.refresh_token
        assert result.user.email == "test@example.com"
        mock_token_repository.store_refresh_token.assert_called_once()


class TestRefreshTokens:
    """Tests for refresh_tokens method."""

    async def test_raises_error_for_invalid_token(
        self,
        auth_service: AuthService,
        mock_token_repository: AsyncMock,
    ) -> None:
        """Should raise UnauthorizedError for invalid refresh token."""
        mock_token_repository.is_token_valid.return_value = False

        with pytest.raises(UnauthorizedError, match="Invalid or expired refresh token"):
            await auth_service.refresh_tokens("invalid-token")

    async def test_returns_new_access_token(
        self,
        auth_service: AuthService,
        mock_settings: Settings,
        mock_user_repository: AsyncMock,
        mock_token_repository: AsyncMock,
        sample_user: User,
    ) -> None:
        """Should return new access token for valid refresh token."""
        mock_token_repository.is_token_valid.return_value = True
        mock_user_repository.get_by_id.return_value = sample_user

        # Create a valid refresh token
        refresh_token = auth_service.create_refresh_token(sample_user)

        result = await auth_service.refresh_tokens(refresh_token)

        assert result.access_token
        assert result.expires_in == 60 * 60  # 60 minutes in seconds

    async def test_raises_error_for_access_token_type(
        self,
        auth_service: AuthService,
        mock_token_repository: AsyncMock,
        sample_user: User,
    ) -> None:
        """Should raise error if token type is 'access' instead of 'refresh'."""
        mock_token_repository.is_token_valid.return_value = True

        # Create an access token (wrong type)
        access_token = auth_service.create_access_token(sample_user)

        with pytest.raises(UnauthorizedError, match="Invalid token type"):
            await auth_service.refresh_tokens(access_token)


class TestLogout:
    """Tests for logout method."""

    async def test_revokes_refresh_token(
        self,
        auth_service: AuthService,
        mock_token_repository: AsyncMock,
    ) -> None:
        """Should revoke the refresh token."""
        await auth_service.logout("user-123", "refresh-token")

        mock_token_repository.revoke_token.assert_called_once_with("refresh-token")


class TestCreateAccessToken:
    """Tests for create_access_token method."""

    def test_creates_valid_jwt(
        self,
        auth_service: AuthService,
        mock_settings: Settings,
        sample_user: User,
    ) -> None:
        """Should create a valid JWT access token."""
        token = auth_service.create_access_token(sample_user)

        payload = jwt.decode(
            token,
            mock_settings.secret_key,
            algorithms=[mock_settings.jwt_algorithm],
        )

        assert payload["sub"] == sample_user.user_id
        assert payload["email"] == sample_user.email
        assert payload["type"] == "access"

    def test_sets_correct_expiry(
        self,
        auth_service: AuthService,
        mock_settings: Settings,
        sample_user: User,
    ) -> None:
        """Should set expiry based on settings."""
        before = datetime.now(UTC)
        token = auth_service.create_access_token(sample_user)
        after = datetime.now(UTC)

        payload = jwt.decode(
            token,
            mock_settings.secret_key,
            algorithms=[mock_settings.jwt_algorithm],
        )

        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        # JWT timestamps are truncated to seconds, so allow 1 second tolerance
        expected_exp_min = (
            before + timedelta(minutes=mock_settings.jwt_expire_minutes) - timedelta(seconds=1)
        )
        expected_exp_max = (
            after + timedelta(minutes=mock_settings.jwt_expire_minutes) + timedelta(seconds=1)
        )

        assert expected_exp_min <= exp <= expected_exp_max


class TestCreateRefreshToken:
    """Tests for create_refresh_token method."""

    def test_creates_valid_jwt(
        self,
        auth_service: AuthService,
        mock_settings: Settings,
        sample_user: User,
    ) -> None:
        """Should create a valid JWT refresh token."""
        token = auth_service.create_refresh_token(sample_user)

        payload = jwt.decode(
            token,
            mock_settings.secret_key,
            algorithms=[mock_settings.jwt_algorithm],
        )

        assert payload["sub"] == sample_user.user_id
        assert payload["type"] == "refresh"

    def test_has_longer_expiry_than_access_token(
        self,
        auth_service: AuthService,
        mock_settings: Settings,
        sample_user: User,
    ) -> None:
        """Refresh token should have longer expiry than access token."""
        access_token = auth_service.create_access_token(sample_user)
        refresh_token = auth_service.create_refresh_token(sample_user)

        access_payload = jwt.decode(
            access_token,
            mock_settings.secret_key,
            algorithms=[mock_settings.jwt_algorithm],
        )
        refresh_payload = jwt.decode(
            refresh_token,
            mock_settings.secret_key,
            algorithms=[mock_settings.jwt_algorithm],
        )

        assert refresh_payload["exp"] > access_payload["exp"]


class TestDecodeToken:
    """Tests for decode_token method."""

    def test_decodes_valid_token(
        self,
        auth_service: AuthService,
        sample_user: User,
    ) -> None:
        """Should decode and return payload for valid token."""
        token = auth_service.create_access_token(sample_user)

        payload = auth_service.decode_token(token)

        assert payload.sub == sample_user.user_id
        assert payload.email == sample_user.email
        assert payload.type == "access"

    def test_raises_error_for_expired_token(
        self,
        auth_service: AuthService,
        mock_settings: Settings,
        sample_user: User,
    ) -> None:
        """Should raise TokenExpiredError for expired token."""
        # Create an expired token
        now = datetime.now(UTC)
        expired_payload = {
            "sub": sample_user.user_id,
            "email": sample_user.email,
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "type": "access",
        }
        expired_token = jwt.encode(
            expired_payload,
            mock_settings.secret_key,
            algorithm=mock_settings.jwt_algorithm,
        )

        with pytest.raises(TokenExpiredError):
            auth_service.decode_token(expired_token)

    def test_raises_error_for_invalid_token(self, auth_service: AuthService) -> None:
        """Should raise UnauthorizedError for malformed token."""
        with pytest.raises(UnauthorizedError, match="Invalid token"):
            auth_service.decode_token("not-a-valid-jwt")

    def test_raises_error_for_wrong_signature(
        self,
        auth_service: AuthService,
        sample_user: User,
    ) -> None:
        """Should raise UnauthorizedError for token with wrong signature."""
        # Create token with different secret
        wrong_token = jwt.encode(
            {
                "sub": sample_user.user_id,
                "email": sample_user.email,
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "type": "access",
            },
            "wrong-secret-key-that-is-long-enough",
            algorithm="HS256",
        )

        with pytest.raises(UnauthorizedError, match="Invalid token"):
            auth_service.decode_token(wrong_token)


class TestGetCurrentUser:
    """Tests for get_current_user method."""

    async def test_returns_user_for_valid_token(
        self,
        auth_service: AuthService,
        mock_user_repository: AsyncMock,
        sample_user: User,
    ) -> None:
        """Should return user for valid access token."""
        mock_user_repository.get_by_id.return_value = sample_user

        token = auth_service.create_access_token(sample_user)

        result = await auth_service.get_current_user(token)

        assert result.user_id == sample_user.user_id
        assert result.email == sample_user.email

    async def test_raises_error_for_refresh_token_type(
        self,
        auth_service: AuthService,
        sample_user: User,
    ) -> None:
        """Should raise error if token type is 'refresh' instead of 'access'."""
        token = auth_service.create_refresh_token(sample_user)

        with pytest.raises(UnauthorizedError, match="Invalid token type"):
            await auth_service.get_current_user(token)

    async def test_raises_error_if_user_not_found(
        self,
        auth_service: AuthService,
        mock_user_repository: AsyncMock,
        sample_user: User,
    ) -> None:
        """Should raise error if user doesn't exist."""
        mock_user_repository.get_by_id.return_value = None

        token = auth_service.create_access_token(sample_user)

        with pytest.raises(UnauthorizedError, match="User not found"):
            await auth_service.get_current_user(token)


class TestEmailDomainValidation:
    """Tests for _validate_email_domain method."""

    def test_allowed_domain_passes(self, auth_service: AuthService) -> None:
        """Should not raise for an allowed domain."""
        auth_service.settings.allowed_email_domains = ["example.com"]
        auth_service._validate_email_domain("user@example.com")

    def test_disallowed_domain_raises_forbidden(self, auth_service: AuthService) -> None:
        """Should raise ForbiddenError for a disallowed domain."""
        auth_service.settings.allowed_email_domains = ["example.com"]
        with pytest.raises(ForbiddenError, match="Email domain not allowed"):
            auth_service._validate_email_domain("user@other.com")

    def test_empty_allowlist_allows_any_domain(self, auth_service: AuthService) -> None:
        """Should allow any domain when the allowlist is empty."""
        auth_service.settings.allowed_email_domains = []
        auth_service._validate_email_domain("user@anything.com")

    def test_case_insensitive_matching(self, auth_service: AuthService) -> None:
        """Should match domains case-insensitively."""
        auth_service.settings.allowed_email_domains = ["Example.COM"]
        auth_service._validate_email_domain("user@EXAMPLE.com")


class TestExchangeCodeDomainValidation:
    """Tests for domain validation during exchange_code."""

    async def test_disallowed_domain_blocks_upsert(
        self,
        auth_service: AuthService,
        mock_user_repository: AsyncMock,
    ) -> None:
        """Should raise ForbiddenError and never call upsert_from_google."""
        auth_service.settings.allowed_email_domains = ["allowed.com"]

        with (
            patch.object(
                auth_service,
                "_exchange_google_code",
                return_value={"access_token": "google-token"},
            ),
            patch.object(
                auth_service,
                "_fetch_google_user_info",
                return_value=GoogleUserInfo(
                    id="google-456",
                    email="user@disallowed.com",
                    name="Bad User",
                ),
            ),
            pytest.raises(ForbiddenError, match="Email domain not allowed"),
        ):
            await auth_service.exchange_code(
                code="valid-code",
                state="same-state",
                expected_state="same-state",
                redirect_uri="http://localhost:3000/callback",
            )

        mock_user_repository.upsert_from_google.assert_not_called()


class TestGenerateMicrosoftAuthUrl:
    """Tests for Microsoft auth URL generation."""

    def test_returns_microsoft_auth_url(self, auth_service: AuthService) -> None:
        """Should return URL pointing to Microsoft login."""
        result = auth_service.generate_auth_url(
            "http://localhost:3000/callback", provider="microsoft"
        )

        assert "login.microsoftonline.com" in result.auth_url
        assert "test-tenant-id" in result.auth_url
        assert "client_id=test-azure-client-id" in result.auth_url

    def test_includes_microsoft_scopes(self, auth_service: AuthService) -> None:
        """Should include required Microsoft scopes."""
        result = auth_service.generate_auth_url(
            "http://localhost:3000/callback", provider="microsoft"
        )

        assert "User.Read" in result.auth_url

    def test_generates_state_parameter(self, auth_service: AuthService) -> None:
        """Should generate random state for CSRF protection."""
        result = auth_service.generate_auth_url(
            "http://localhost:3000/callback", provider="microsoft"
        )

        assert result.state
        assert len(result.state) > 20


class TestExchangeCodeMicrosoft:
    """Tests for Microsoft code exchange flow."""

    async def test_exchanges_microsoft_code_and_returns_tokens(
        self,
        auth_service: AuthService,
        mock_user_repository: AsyncMock,
        mock_token_repository: AsyncMock,
        sample_user: User,
    ) -> None:
        """Should exchange Microsoft code and return JWT tokens."""
        mock_user_repository.upsert_from_microsoft.return_value = sample_user

        with (
            patch.object(
                auth_service,
                "_exchange_microsoft_code",
                return_value={"access_token": "ms-token"},
            ),
            patch.object(
                auth_service,
                "_fetch_microsoft_user_info",
                return_value=MicrosoftUserInfo(
                    id="ms-123",
                    email="test@example.com",
                    name="Test User",
                ),
            ),
        ):
            result = await auth_service.exchange_code(
                code="valid-code",
                state="same-state",
                expected_state="same-state",
                redirect_uri="http://localhost:3000/callback",
                provider="microsoft",
            )

        assert result.access_token
        assert result.refresh_token
        assert result.user.email == "test@example.com"
        mock_user_repository.upsert_from_microsoft.assert_called_once()

    async def test_microsoft_domain_validation(
        self,
        auth_service: AuthService,
        mock_user_repository: AsyncMock,
    ) -> None:
        """Should apply domain validation to Microsoft provider."""
        auth_service.settings.allowed_email_domains = ["allowed.com"]

        with (
            patch.object(
                auth_service,
                "_exchange_microsoft_code",
                return_value={"access_token": "ms-token"},
            ),
            patch.object(
                auth_service,
                "_fetch_microsoft_user_info",
                return_value=MicrosoftUserInfo(
                    id="ms-456",
                    email="user@disallowed.com",
                    name="Bad User",
                ),
            ),
            pytest.raises(ForbiddenError, match="Email domain not allowed"),
        ):
            await auth_service.exchange_code(
                code="valid-code",
                state="same-state",
                expected_state="same-state",
                redirect_uri="http://localhost:3000/callback",
                provider="microsoft",
            )

        mock_user_repository.upsert_from_microsoft.assert_not_called()
