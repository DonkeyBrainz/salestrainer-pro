"""Authentication models for the Luxe Sales Coach API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.user import UserResponse


class LoginRequest(BaseModel):
    """Request to initiate OAuth flow."""

    provider: Literal["google"] = "google"


class CallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str
    state: str


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(alias="refreshToken")

    model_config = {"populate_by_name": True}


class LogoutRequest(BaseModel):
    """Logout request with refresh token."""

    refresh_token: str = Field(alias="refreshToken")

    model_config = {"populate_by_name": True}


class LoginResponse(BaseModel):
    """OAuth URL response."""

    auth_url: str = Field(serialization_alias="authUrl")
    state: str


class TokenResponse(BaseModel):
    """Token response after successful auth."""

    access_token: str = Field(serialization_alias="accessToken")
    refresh_token: str = Field(serialization_alias="refreshToken")
    expires_in: int = Field(serialization_alias="expiresIn")
    token_type: str = Field(default="Bearer", serialization_alias="tokenType")
    user: UserResponse


class RefreshResponse(BaseModel):
    """Token refresh response."""

    access_token: str = Field(serialization_alias="accessToken")
    expires_in: int = Field(serialization_alias="expiresIn")
    token_type: str = Field(default="Bearer", serialization_alias="tokenType")


class LogoutResponse(BaseModel):
    """Logout response."""

    success: bool = True


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    email: str
    exp: datetime
    iat: datetime
    type: Literal["access", "refresh"]


class GoogleUserInfo(BaseModel):
    """User info from Google OAuth."""

    id: str
    email: str
    name: str
    picture: str | None = None
    verified_email: bool = True
