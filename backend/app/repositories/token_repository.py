"""Token repository for refresh token storage and revocation."""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from google.cloud.firestore import AsyncClient

from app.repositories.base import BaseRepository


class TokenRepository(BaseRepository):
    """Repository for refresh token management in Firestore."""

    _collection_name = "refresh_tokens"

    def __init__(self, db: AsyncClient | None = None) -> None:
        """Initialize token repository."""
        super().__init__(db)

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for secure storage."""
        return sha256(token.encode()).hexdigest()

    async def store_refresh_token(
        self,
        user_id: str,
        token: str,
        expires_at: datetime,
    ) -> None:
        """Store refresh token for user.

        Args:
            user_id: The user's ID
            token: Raw refresh token (will be hashed)
            expires_at: When the token expires
        """
        token_hash = self.hash_token(token)

        doc_data = {
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "revoked": False,
            "created_at": datetime.now(UTC),
        }

        await self.collection.document(token_hash).set(doc_data)

    async def is_token_valid(self, token: str) -> bool:
        """Check if refresh token is valid (not revoked and not expired).

        Args:
            token: Raw refresh token

        Returns:
            True if token is valid, False otherwise
        """
        token_hash = self.hash_token(token)
        doc = await self.collection.document(token_hash).get()

        if not doc.exists:
            return False

        data: dict[str, Any] = doc.to_dict()
        if data.get("revoked", True):
            return False

        expires_at = data.get("expires_at")
        if expires_at and expires_at < datetime.now(UTC):
            return False

        return True

    async def revoke_token(self, token: str) -> None:
        """Revoke a refresh token.

        Args:
            token: Raw refresh token to revoke
        """
        token_hash = self.hash_token(token)
        doc_ref = self.collection.document(token_hash)
        doc = await doc_ref.get()

        if doc.exists:
            await doc_ref.update({"revoked": True, "revoked_at": datetime.now(UTC)})

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all refresh tokens for a user.

        Args:
            user_id: The user's ID

        Returns:
            Number of tokens revoked
        """
        query = self.collection.where("user_id", "==", user_id).where("revoked", "==", False)
        docs = query.stream()

        count = 0
        async for doc in docs:
            await self.collection.document(doc.id).update(
                {
                    "revoked": True,
                    "revoked_at": datetime.now(UTC),
                }
            )
            count += 1

        return count

    async def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from the database.

        Returns:
            Number of tokens removed
        """
        now = datetime.now(UTC)
        query = self.collection.where("expires_at", "<", now)
        docs = query.stream()

        count = 0
        async for doc in docs:
            await self.collection.document(doc.id).delete()
            count += 1

        return count
