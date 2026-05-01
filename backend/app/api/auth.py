"""Authentication endpoints for OAuth and token management.

OAuth Flow Variants:

1. Browser/Manual Testing (GET /auth/login):
   - User navigates to GET /auth/login
   - Server sets cookie and redirects to Google
   - Google redirects back to /auth/callback
   - Tokens returned as JSON

2. SPA Frontend (POST /auth/login):
   - Frontend calls POST /auth/login
   - Server returns authUrl as JSON
   - Frontend redirects browser to authUrl
   - Google redirects to /auth/callback
   - Tokens returned as JSON

Both flows use the same callback endpoint and state validation.
"""

from fastapi import APIRouter, Cookie, Response, status
from fastapi.responses import RedirectResponse

from app.config import Settings
from app.core.dependencies import (
    AuthServiceDep,
    CurrentUserDep,
    SettingsDep,
    StateManagerDep,
)
from app.core.exceptions import InvalidRequestError
from app.models.auth import (
    CallbackRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
    TokenResponse,
)
from app.models.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Cookie name for OAuth state storage
OAUTH_STATE_COOKIE = "oauth_state"


def _get_redirect_uri(settings: Settings, provider: str) -> str:
    """Get the redirect URI for the given provider."""
    if provider == "microsoft":
        return settings.azure_redirect_uri
    return settings.google_redirect_uri


@router.get("/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def login_redirect(
    auth_service: AuthServiceDep,
    state_manager: StateManagerDep,
    settings: SettingsDep,
    provider: str = "google",
) -> RedirectResponse:
    """Initiate OAuth flow with direct redirect (for manual testing).

    Supports Google and Microsoft providers via the `provider` query parameter.
    Sets the oauth_state cookie and redirects to the provider.

    For SPA frontends, use POST /auth/login instead to get the URL as JSON.
    """
    redirect_uri = _get_redirect_uri(settings, provider)
    login_response = auth_service.generate_auth_url(redirect_uri, provider=provider)

    # Sign and store state in HTTP-only cookie (includes provider)
    signed_state = state_manager.sign_state(login_response.state, provider=provider)

    # Create redirect response and set cookie on it directly
    redirect_response = RedirectResponse(url=login_response.auth_url, status_code=307)
    redirect_response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=signed_state,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=600,
    )

    return redirect_response


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    auth_service: AuthServiceDep,
    state_manager: StateManagerDep,
    settings: SettingsDep,
    response: Response,
) -> LoginResponse:
    """Initiate OAuth flow (SPA/API mode).

    Accepts an optional `provider` field ("google" or "microsoft", default "google").
    Returns the OAuth URL as JSON for client-side redirect handling.
    Sets a signed cookie with the state and provider for validation on callback.
    """
    provider = request.provider
    redirect_uri = _get_redirect_uri(settings, provider)
    login_response = auth_service.generate_auth_url(redirect_uri, provider=provider)

    # Sign and store state in HTTP-only cookie for CSRF protection (includes provider)
    signed_state = state_manager.sign_state(login_response.state, provider=provider)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=signed_state,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=600,
    )

    return login_response


@router.get("/callback", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def callback(
    code: str,
    state: str,
    auth_service: AuthServiceDep,
    state_manager: StateManagerDep,
    settings: SettingsDep,
    response: Response,
    oauth_state: str | None = Cookie(default=None),
) -> TokenResponse:
    """Handle OAuth callback from provider.

    Exchanges authorization code for access and refresh tokens.
    Creates or updates user in database.
    Validates state parameter against signed cookie for CSRF protection.
    Provider is determined from the signed state cookie.
    """
    # Validate state from cookie against request state
    if not state_manager.validate_state(oauth_state, state):
        raise InvalidRequestError("Invalid or expired state parameter")

    # Clear the state cookie after validation
    response.delete_cookie(
        key=OAUTH_STATE_COOKIE,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
    )

    # Extract expected state and provider from signed cookie
    expected_state, provider = (
        state_manager.verify_state_with_provider(oauth_state) if oauth_state else ("", "google")
    )
    redirect_uri = _get_redirect_uri(settings, provider)

    return await auth_service.exchange_code(
        code=code,
        state=state,
        expected_state=expected_state or "",
        redirect_uri=redirect_uri,
        provider=provider,
    )


@router.post("/callback", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def callback_post(
    request: CallbackRequest,
    auth_service: AuthServiceDep,
    state_manager: StateManagerDep,
    settings: SettingsDep,
    response: Response,
    oauth_state: str | None = Cookie(default=None),
) -> TokenResponse:
    """Handle OAuth callback from SPA frontend.

    SPA flow:
    1. Frontend calls POST /auth/login with provider, receives authUrl, cookie is set
    2. Frontend redirects to provider (Google or Microsoft)
    3. Provider redirects to frontend /auth/callback with code and state in URL
    4. Frontend calls this POST endpoint with code and state in body
    5. Backend validates state against cookie and exchanges code for tokens

    Provider is determined from the signed state cookie.
    Requires credentials: 'include' on frontend fetch for cookie to be sent.
    """
    # Validate state from cookie against request state
    if not state_manager.validate_state(oauth_state, request.state):
        raise InvalidRequestError("Invalid or expired state parameter")

    # Clear the state cookie after validation
    response.delete_cookie(
        key=OAUTH_STATE_COOKIE,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
    )

    # Extract expected state and provider from signed cookie
    expected_state, provider = (
        state_manager.verify_state_with_provider(oauth_state) if oauth_state else ("", "google")
    )
    redirect_uri = _get_redirect_uri(settings, provider)

    return await auth_service.exchange_code(
        code=request.code,
        state=request.state,
        expected_state=expected_state or "",
        redirect_uri=redirect_uri,
        provider=provider,
    )


@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_200_OK)
async def refresh(
    request: RefreshRequest,
    auth_service: AuthServiceDep,
) -> RefreshResponse:
    """Refresh an expired access token.

    Uses refresh token to generate a new access token.
    """
    return await auth_service.refresh_tokens(request.refresh_token)


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(
    current_user: CurrentUserDep,
) -> UserResponse:
    """Get current authenticated user.

    Requires valid access token in Authorization header.
    """
    return UserResponse.from_user(current_user)


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(
    request: LogoutRequest,
    current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
) -> LogoutResponse:
    """Invalidate current session and revoke refresh token.

    Requires valid access token in Authorization header for authentication
    and refresh token in request body to revoke.
    """
    await auth_service.logout(current_user.user_id, request.refresh_token)
    return LogoutResponse(success=True)
