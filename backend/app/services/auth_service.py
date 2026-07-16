"""Authentication service for OAuth and JWT token management."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt

from app.config import Settings
from app.core.exceptions import (
    ForbiddenError,
    InvalidRequestError,
    TokenExpiredError,
    UnauthorizedError,
)
from app.models.auth import (
    GoogleUserInfo,
    LoginResponse,
    RefreshResponse,
    TokenPayload,
    TokenResponse,
)
from app.models.user import User, UserResponse
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    """Service for handling authentication and authorization."""

    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(
        self,
        settings: Settings,
        user_repository: UserRepository,
        token_repository: TokenRepository,
    ) -> None:
        """Initialize auth service.

        Args:
            settings: Application settings
            user_repository: User data repository
            token_repository: Refresh token repository
        """
        self.settings = settings
        self.user_repository = user_repository
        self.token_repository = token_repository

    def generate_auth_url(self, redirect_uri: str, provider: str = "google") -> LoginResponse:
        """Generate OAuth authorization URL for the given provider.

        Args:
            redirect_uri: Where the provider should redirect after auth
            provider: OAuth provider ("google")

        Returns:
            LoginResponse with auth URL and state
        """
        state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        auth_url = f"{self.GOOGLE_AUTH_URL}?{urlencode(params)}"

        return LoginResponse(auth_url=auth_url, state=state)

    async def exchange_code(
        self,
        code: str,
        state: str,
        expected_state: str,
        redirect_uri: str,
        provider: str = "google",
    ) -> TokenResponse:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from the OAuth provider
            state: State parameter from callback
            expected_state: State we generated (for CSRF protection)
            redirect_uri: Redirect URI used in initial request
            provider: OAuth provider ("google")

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            InvalidRequestError: If state doesn't match
            UnauthorizedError: If code exchange fails
            ForbiddenError: If email domain not allowed
        """
        if state != expected_state:
            raise InvalidRequestError("Invalid state parameter")

        user = await self._exchange_google_flow(code, redirect_uri)

        # Generate our JWT tokens
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)

        # Store refresh token
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days)
        await self.token_repository.store_refresh_token(
            user_id=user.user_id,
            token=refresh_token,
            expires_at=expires_at,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.settings.jwt_expire_minutes * 60,
            user=UserResponse.from_user(user),
        )

    async def _exchange_google_flow(self, code: str, redirect_uri: str) -> User:
        """Complete Google OAuth flow: exchange code, fetch user, validate, upsert."""
        google_tokens = await self._exchange_google_code(code, redirect_uri)
        google_user = await self._fetch_google_user_info(google_tokens["access_token"])
        self._validate_email_domain(google_user.email)
        return await self.user_repository.upsert_from_google(google_user)

    async def refresh_tokens(self, refresh_token: str) -> RefreshResponse:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Current refresh token

        Returns:
            RefreshResponse with new access token

        Raises:
            UnauthorizedError: If refresh token is invalid
        """
        # Validate refresh token
        if not await self.token_repository.is_token_valid(refresh_token):
            raise UnauthorizedError("Invalid or expired refresh token")

        # Decode token to get user info
        try:
            payload = self.decode_token(refresh_token)
        except (TokenExpiredError, UnauthorizedError) as e:
            raise UnauthorizedError("Invalid refresh token") from e

        if payload.type != "refresh":
            raise UnauthorizedError("Invalid token type")

        # Get user from database
        user = await self.user_repository.get_by_id(payload.sub)
        if not user:
            raise UnauthorizedError("User not found")

        # Generate new access token
        access_token = self.create_access_token(user)

        return RefreshResponse(
            access_token=access_token,
            expires_in=self.settings.jwt_expire_minutes * 60,
        )

    async def logout(self, user_id: str, refresh_token: str) -> None:
        """Invalidate refresh token on logout.

        Args:
            user_id: The user's ID
            refresh_token: Token to revoke
        """
        await self.token_repository.revoke_token(refresh_token)

    def create_access_token(self, user: User) -> str:
        """Create short-lived JWT access token.

        Args:
            user: User to create token for

        Returns:
            JWT access token string
        """
        now = datetime.now(UTC)
        expires = now + timedelta(minutes=self.settings.jwt_expire_minutes)

        payload = {
            "sub": user.user_id,
            "email": user.email,
            "iat": now,
            "exp": expires,
            "type": "access",
        }

        token: str = jwt.encode(
            payload,
            self.settings.secret_key,
            algorithm=self.settings.jwt_algorithm,
        )
        return token

    def create_refresh_token(self, user: User) -> str:
        """Create longer-lived JWT refresh token.

        Args:
            user: User to create token for

        Returns:
            JWT refresh token string
        """
        now = datetime.now(UTC)
        expires = now + timedelta(days=self.settings.refresh_token_expire_days)

        payload = {
            "sub": user.user_id,
            "email": user.email,
            "iat": now,
            "exp": expires,
            "type": "refresh",
        }

        token: str = jwt.encode(
            payload,
            self.settings.secret_key,
            algorithm=self.settings.jwt_algorithm,
        )
        return token

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenPayload with decoded claims

        Raises:
            TokenExpiredError: If token is expired
            UnauthorizedError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )
            return TokenPayload(
                sub=payload["sub"],
                email=payload["email"],
                exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
                iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
                type=payload["type"],
            )
        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredError() from e
        except JWTError as e:
            raise UnauthorizedError("Invalid token") from e

    async def get_current_user(self, token: str) -> User:
        """Get user from access token.

        Args:
            token: JWT access token

        Returns:
            User associated with token

        Raises:
            TokenExpiredError: If token is expired
            UnauthorizedError: If token is invalid or user not found
        """
        payload = self.decode_token(token)

        if payload.type != "access":
            raise UnauthorizedError("Invalid token type")

        user = await self.user_repository.get_by_id(payload.sub)
        if not user:
            raise UnauthorizedError("User not found")

        return user

    def _validate_email_domain(self, email: str) -> None:
        """Validate that the user's email domain is in the allowlist.

        Args:
            email: User's email address

        Raises:
            ForbiddenError: If domain is not in the allowlist
        """
        allowed = self.settings.allowed_email_domains
        if not allowed:
            return
        domain = email.split("@")[1].lower()
        if domain not in [d.lower() for d in allowed]:
            raise ForbiddenError("Email domain not allowed")

    async def _exchange_google_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange authorization code with Google OAuth endpoint.

        Args:
            code: Authorization code from Google
            redirect_uri: Redirect URI used in initial request

        Returns:
            Dict with access_token, refresh_token, etc.

        Raises:
            UnauthorizedError: If exchange fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )

            if response.status_code != 200:
                raise UnauthorizedError("Failed to exchange authorization code")

            result: dict[str, Any] = response.json()
            return result

    async def _fetch_google_user_info(self, access_token: str) -> GoogleUserInfo:
        """Fetch user info from Google API.

        Args:
            access_token: Google access token

        Returns:
            GoogleUserInfo with user details

        Raises:
            UnauthorizedError: If fetch fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                raise UnauthorizedError("Failed to fetch user info from Google")

            data = response.json()
            return GoogleUserInfo(
                id=data["id"],
                email=data["email"],
                name=data.get("name", data["email"]),
                picture=data.get("picture"),
                verified_email=data.get("verified_email", True),
            )
