"""Base repository with Firestore client management."""

from typing import Any

from google.cloud.firestore import AsyncClient

from app.config import get_settings

_firestore_client: AsyncClient | None = None


def get_firestore_client() -> AsyncClient:
    """Get or create the Firestore async client singleton."""
    global _firestore_client
    if _firestore_client is None:
        settings = get_settings()
        _firestore_client = AsyncClient(
            project=settings.gcp_project_id,
            database=settings.firestore_database,
        )
    return _firestore_client


class BaseRepository:
    """Base repository with Firestore client access."""

    _collection_name: str = ""

    def __init__(self, db: AsyncClient | None = None) -> None:
        """Initialize repository with optional Firestore client.

        Args:
            db: Optional Firestore client. If not provided, uses singleton.
        """
        self._db = db

    @property
    def db(self) -> AsyncClient:
        """Get Firestore client (lazy initialization)."""
        if self._db is None:
            self._db = get_firestore_client()
        return self._db

    @property
    def collection(self) -> Any:
        """Get collection reference."""
        if not self._collection_name:
            raise ValueError("_collection_name must be set in subclass")
        return self.db.collection(self._collection_name)
