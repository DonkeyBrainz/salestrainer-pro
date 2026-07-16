"""User repository for Firestore persistence."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from google.cloud.firestore import AsyncClient

from app.models.auth import GoogleUserInfo
from app.models.user import User, UserCreate, UserPreferences
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for user data in Firestore."""

    _collection_name = "users"

    def __init__(self, db: AsyncClient | None = None) -> None:
        """Initialize user repository."""
        super().__init__(db)

    async def get_by_id(self, user_id: str) -> User | None:
        """Get user by user_id."""
        doc = await self.collection.document(user_id).get()
        if not doc.exists:
            return None
        return self._doc_to_user(doc.id, doc.to_dict())

    async def get_by_google_id(self, google_id: str) -> User | None:
        """Get user by Google ID."""
        query = self.collection.where("google_id", "==", google_id).limit(1)
        docs = query.stream()
        async for doc in docs:
            return self._doc_to_user(doc.id, doc.to_dict())
        return None

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        query = self.collection.where("email", "==", email).limit(1)
        docs = query.stream()
        async for doc in docs:
            return self._doc_to_user(doc.id, doc.to_dict())
        return None

    async def create(self, user_data: UserCreate) -> User:
        """Create new user in Firestore."""
        user_id = str(uuid4())
        now = datetime.now(UTC)

        doc_data: dict[str, Any] = {
            "email": user_data.email,
            "name": user_data.name,
            "google_id": user_data.google_id,
            "picture_url": user_data.picture_url,
            "preferences": UserPreferences().model_dump(),
            "role": "agent",
            "store_id": None,
            "region": None,
            "created_at": now,
            "updated_at": None,
        }

        await self.collection.document(user_id).set(doc_data)

        return User(
            user_id=user_id,
            email=user_data.email,
            name=user_data.name,
            google_id=user_data.google_id,
            picture_url=user_data.picture_url,
            preferences=UserPreferences(),
            role="agent",
            store_id=None,
            region=None,
            created_at=now,
            updated_at=None,
        )

    async def update(self, user_id: str, updates: dict[str, Any]) -> User | None:
        """Update user fields."""
        doc_ref = self.collection.document(user_id)
        doc = await doc_ref.get()

        if not doc.exists:
            return None

        updates["updated_at"] = datetime.now(UTC)
        await doc_ref.update(updates)

        updated_doc = await doc_ref.get()
        return self._doc_to_user(updated_doc.id, updated_doc.to_dict())

    async def upsert_from_google(self, google_info: GoogleUserInfo) -> User:
        """Create or update user from Google OAuth info.

        If user exists (by google_id), update name/picture.
        If new user, create with generated UUID.
        """
        existing = await self.get_by_google_id(google_info.id)

        if existing:
            updates = {
                "name": google_info.name,
                "picture_url": google_info.picture,
            }
            updated = await self.update(existing.user_id, updates)
            if updated:
                return updated
            return existing

        return await self.create(
            UserCreate(
                email=google_info.email,
                name=google_info.name,
                google_id=google_info.id,
                picture_url=google_info.picture,
            )
        )

    async def list_by_store_ids(self, store_ids: list[str]) -> list[User]:
        """List users assigned to any of the given store_ids.

        Chunks the query into batches of 30 to respect Firestore's `in`
        filter limit (relevant for regional/national rollups with many stores).
        """
        if not store_ids:
            return []

        users: list[User] = []
        for i in range(0, len(store_ids), 30):
            chunk = store_ids[i : i + 30]
            query = self.collection.where("store_id", "in", chunk)
            docs = await query.get()
            users.extend(self._doc_to_user(doc.id, doc.to_dict()) for doc in docs)
        return users

    def _doc_to_user(self, user_id: str, data: dict[str, Any] | None) -> User:
        """Convert Firestore document to User model."""
        if data is None:
            raise ValueError("Document data is None")

        preferences_data = data.get("preferences", {})
        preferences = UserPreferences(**preferences_data) if preferences_data else UserPreferences()

        return User(
            user_id=user_id,
            email=data["email"],
            name=data["name"],
            google_id=data.get("google_id"),
            picture_url=data.get("picture_url"),
            preferences=preferences,
            role=data.get("role", "agent"),
            store_id=data.get("store_id"),
            region=data.get("region"),
            created_at=data["created_at"],
            updated_at=data.get("updated_at"),
        )
