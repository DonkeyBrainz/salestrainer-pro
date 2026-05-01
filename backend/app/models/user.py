"""User models for the Luxe Sales Coach API."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class UserPreferences(BaseModel):
    """User preference settings."""

    # Note: voice_name removed - voices are now persona-specific
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    theme: Literal["light", "dark"] = "light"
    notifications_enabled: bool = Field(default=True, alias="notificationsEnabled")

    model_config = {"populate_by_name": True}


class UserBase(BaseModel):
    """Base user model with common fields."""

    email: EmailStr
    name: str


class UserCreate(UserBase):
    """User creation model (from OAuth providers)."""

    google_id: str | None = None
    microsoft_id: str | None = None
    picture_url: str | None = None


class User(UserBase):
    """Full user model with database fields."""

    user_id: str
    google_id: str | None = None
    microsoft_id: str | None = None
    picture_url: str | None = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    created_at: datetime
    updated_at: datetime | None = None


class UserResponse(BaseModel):
    """API response model for user (camelCase for frontend)."""

    user_id: str = Field(serialization_alias="userId")
    email: str
    name: str
    created_at: str = Field(serialization_alias="createdAt")
    preferences: dict[str, Any]

    model_config = {"populate_by_name": True}

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        """Create response from User model."""
        return cls(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            created_at=user.created_at.isoformat(),
            preferences=user.preferences.model_dump(by_alias=True),
        )
