from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.models.session import (
    Difficulty,
    Session,
    SessionCreate,
    SessionStatus,
    SessionType,
    SessionUpdate,
)
from app.repositories.base import BaseRepository

# Migration mapping for old difficulty values
DIFFICULTY_MIGRATION_MAP = {
    "easy": "high_regard",
    "medium": "medium_regard",
    "hard": "low_regard",
}


class SessionRepository(BaseRepository):
    """Repository for session data access."""

    _collection_name = "sessions"

    async def create(self, session_create: SessionCreate) -> Session:
        """Create new session."""
        session_id = str(uuid4())
        now = datetime.now(UTC)

        session_data = {
            "session_id": session_id,
            "user_id": session_create.user_id,
            "session_type": session_create.session_type.value,
            "status": SessionStatus.ACTIVE.value,
            "selected_persona": session_create.selected_persona,
            "difficulty": session_create.difficulty.value,
            "system_instruction": session_create.system_instruction,
            "product_category": session_create.product_category,
            "product_type": session_create.product_type,
            "started_at": now,
            "ended_at": None,
            "duration": None,
            "grade": None,
            "score": None,
            "message_count": 0,
            "created_at": now,
            "updated_at": now,
            "is_deleted": False,
            "deleted_at": None,
        }

        await self.collection.document(session_id).set(session_data)
        return self._doc_to_session(session_id, session_data)

    async def get_by_id(self, session_id: str) -> Session | None:
        """Get session by ID."""
        doc = await self.collection.document(session_id).get()
        if not doc.exists:
            return None

        data = doc.to_dict()
        if data.get("is_deleted"):
            return None

        return self._doc_to_session(session_id, data)

    async def update(self, session_id: str, updates: SessionUpdate) -> Session | None:
        """Update session."""
        session = await self.get_by_id(session_id)
        if not session:
            return None

        update_data = updates.model_dump(exclude_none=True)
        update_data["updated_at"] = datetime.now(UTC)

        # Convert enums to values
        if "status" in update_data:
            update_data["status"] = update_data["status"].value

        await self.collection.document(session_id).update(update_data)

        # Fetch and return updated session
        updated_doc = await self.collection.document(session_id).get()
        return self._doc_to_session(session_id, updated_doc.to_dict())

    async def list_by_user(self, user_id: str, limit: int = 50) -> list[Session]:
        """List sessions for user, excluding deleted and abandoned sessions."""
        query = (
            self.collection.where("user_id", "==", user_id)
            .where("is_deleted", "==", False)
            .order_by("started_at", direction="DESCENDING")
            .limit(limit)
        )

        docs = await query.get()
        # Filter out abandoned sessions
        return [
            self._doc_to_session(doc.id, doc.to_dict())
            for doc in docs
            if doc.to_dict().get("status") != SessionStatus.ABANDONED.value
        ]

    async def list_all_completed_by_user(self, user_id: str) -> list[Session]:
        """List all completed sessions for a user, sorted newest-first.

        Used for streak and dashboard stats computation. Fetches everything in
        Python to avoid composite Firestore index requirements.
        """
        query = self.collection.where("user_id", "==", user_id)
        docs = await query.get()
        sessions = [
            self._doc_to_session(doc.id, doc.to_dict())
            for doc in docs
            if not doc.to_dict().get("is_deleted", False)
            and doc.to_dict().get("status") == SessionStatus.COMPLETED.value
        ]
        sessions.sort(key=lambda s: s.started_at, reverse=True)
        return sessions

    async def list_by_user_with_pagination(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        session_type: SessionType | None = None,
    ) -> tuple[list[Session], int]:
        """List sessions for user with pagination.

        Args:
            user_id: User ID to filter by
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            session_type: Optional session type filter

        Returns:
            Tuple of (sessions list, total count)
        """
        # Build base query - only filter by user_id to avoid composite index requirement
        # We'll filter, sort, and paginate in Python to avoid needing a Firestore index
        query = self.collection.where("user_id", "==", user_id)

        # Fetch all sessions for the user (Firestore will cache this efficiently)
        docs = await query.get()

        # Filter in Python to avoid composite index requirement
        all_sessions = [
            self._doc_to_session(doc.id, doc.to_dict())
            for doc in docs
            if not doc.to_dict().get("is_deleted", False)
            and doc.to_dict().get("status") != SessionStatus.ABANDONED.value
        ]

        # Apply session_type filter if provided
        if session_type:
            all_sessions = [s for s in all_sessions if s.session_type == session_type]

        # Sort by started_at descending (most recent first) in Python
        all_sessions.sort(key=lambda s: s.started_at, reverse=True)

        # Apply pagination
        total_count = len(all_sessions)
        sessions = all_sessions[offset : offset + limit]

        return sessions, total_count

    def _doc_to_session(self, doc_id: str, data: dict[str, Any]) -> Session:
        """Convert Firestore document to Session model."""
        # Migrate old difficulty values to new format
        difficulty_value = data["difficulty"]
        if difficulty_value in DIFFICULTY_MIGRATION_MAP:
            difficulty_value = DIFFICULTY_MIGRATION_MAP[difficulty_value]

        return Session(
            session_id=doc_id,
            user_id=data["user_id"],
            session_type=SessionType(data["session_type"]),
            status=SessionStatus(data["status"]),
            selected_persona=data.get("selected_persona"),
            difficulty=Difficulty(difficulty_value),
            system_instruction=data.get("system_instruction"),
            product_category=data.get("product_category"),
            product_type=data.get("product_type"),
            started_at=data["started_at"],
            ended_at=data.get("ended_at"),
            duration=data.get("duration"),
            grade=data.get("grade"),
            score=data.get("score"),
            message_count=data.get("message_count", 0),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            is_deleted=data.get("is_deleted", False),
            deleted_at=data.get("deleted_at"),
        )
