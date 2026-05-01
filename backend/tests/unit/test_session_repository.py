"""Unit tests for SessionRepository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.session import (
    Difficulty,
    SessionCreate,
    SessionStatus,
    SessionType,
    SessionUpdate,
)
from app.repositories.session_repository import SessionRepository


@pytest.fixture
def mock_firestore_client() -> MagicMock:
    """Create a mock Firestore client.

    Uses MagicMock because collection() is synchronous.
    Only get/set/update calls are async.
    """
    return MagicMock()


@pytest.fixture
def session_repository(mock_firestore_client: MagicMock) -> SessionRepository:
    """Create SessionRepository with mocked Firestore client."""
    return SessionRepository(db=mock_firestore_client)


@pytest.fixture
def sample_session_data() -> dict:
    """Sample session document data from Firestore."""
    return {
        "user_id": "test_user",
        "session_type": "training",
        "status": "active",
        "difficulty": "medium_regard",
        "selected_persona": None,
        "system_instruction": None,
        "started_at": datetime.now(UTC),
        "ended_at": None,
        "duration": None,
        "grade": None,
        "score": None,
        "message_count": 0,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "is_deleted": False,
        "deleted_at": None,
    }


class TestCreate:
    """Tests for create method."""

    async def test_creates_session_with_id(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should create session with generated UUID."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        session_create = SessionCreate(
            user_id="test_user",
            session_type=SessionType.TRAINING,
            difficulty=Difficulty.MEDIUM_REGARD,
        )

        result = await session_repository.create(session_create)

        assert result.session_id is not None
        assert result.user_id == "test_user"
        assert result.status == SessionStatus.ACTIVE
        mock_firestore_client.collection.assert_called_with("sessions")

    async def test_sets_timestamps(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should set created_at and updated_at to current time."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        session_create = SessionCreate(user_id="test_user")

        result = await session_repository.create(session_create)

        assert result.created_at is not None
        assert result.updated_at is not None
        assert result.started_at is not None

    async def test_saves_session_type_and_difficulty(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should save session type and difficulty."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        session_create = SessionCreate(
            user_id="test_user",
            session_type=SessionType.EVALUATION,
            difficulty=Difficulty.LOW_REGARD,
        )

        result = await session_repository.create(session_create)

        assert result.session_type == SessionType.EVALUATION
        assert result.difficulty == Difficulty.LOW_REGARD


class TestGetById:
    """Tests for get_by_id method."""

    async def test_returns_session_when_exists(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
        sample_session_data: dict,
    ) -> None:
        """Should return Session when document exists."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "session-123"
        mock_doc.to_dict.return_value = sample_session_data

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await session_repository.get_by_id("session-123")

        assert result is not None
        assert result.session_id == "session-123"
        assert result.user_id == "test_user"
        assert result.status == SessionStatus.ACTIVE

    async def test_returns_none_when_not_exists(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return None when document doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await session_repository.get_by_id("nonexistent-id")

        assert result is None

    async def test_returns_none_when_deleted(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
        sample_session_data: dict,
    ) -> None:
        """Should return None when session is marked as deleted."""
        deleted_data = {**sample_session_data, "is_deleted": True}
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = deleted_data

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await session_repository.get_by_id("deleted-session")

        assert result is None

    async def test_migrates_old_difficulty_values(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
        sample_session_data: dict,
    ) -> None:
        """Should migrate old difficulty values (easy/medium/hard) to new format."""
        # Test all three old values
        old_to_new = {
            "easy": Difficulty.HIGH_REGARD,
            "medium": Difficulty.MEDIUM_REGARD,
            "hard": Difficulty.LOW_REGARD,
        }

        for old_value, expected_new_value in old_to_new.items():
            old_data = {**sample_session_data, "difficulty": old_value}
            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.id = "session-123"
            mock_doc.to_dict.return_value = old_data

            mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
                return_value=mock_doc
            )

            result = await session_repository.get_by_id("session-123")

            assert result is not None
            assert result.difficulty == expected_new_value


class TestUpdate:
    """Tests for update method."""

    async def test_updates_status(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
        sample_session_data: dict,
    ) -> None:
        """Should update session status."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "session-123"
        mock_doc.to_dict.return_value = sample_session_data

        updated_data = {**sample_session_data, "status": "completed"}
        updated_doc = MagicMock()
        updated_doc.to_dict.return_value = updated_data

        doc_ref = mock_firestore_client.collection.return_value.document.return_value
        doc_ref.get = AsyncMock(side_effect=[mock_doc, updated_doc])
        doc_ref.update = AsyncMock()

        session_update = SessionUpdate(status=SessionStatus.COMPLETED)
        result = await session_repository.update("session-123", session_update)

        assert result is not None
        doc_ref.update.assert_called_once()

    async def test_returns_none_if_not_exists(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return None if session doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        session_update = SessionUpdate(status=SessionStatus.COMPLETED)
        result = await session_repository.update("nonexistent", session_update)

        assert result is None


class TestListByUser:
    """Tests for list_by_user method."""

    async def test_returns_user_sessions(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
        sample_session_data: dict,
    ) -> None:
        """Should return list of user's sessions."""
        mock_doc = MagicMock()
        mock_doc.id = "session-123"
        mock_doc.to_dict.return_value = sample_session_data

        mock_query = MagicMock()
        mock_query.get = AsyncMock(return_value=[mock_doc])
        (
            mock_firestore_client.collection.return_value.where.return_value.where.return_value.order_by.return_value.limit.return_value
        ) = mock_query

        result = await session_repository.list_by_user("test_user")

        assert len(result) == 1
        assert result[0].user_id == "test_user"

    async def test_returns_empty_list_when_no_sessions(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return empty list when user has no sessions."""
        mock_query = MagicMock()
        mock_query.get = AsyncMock(return_value=[])
        (
            mock_firestore_client.collection.return_value.where.return_value.where.return_value.order_by.return_value.limit.return_value
        ) = mock_query

        result = await session_repository.list_by_user("user-no-sessions")

        assert result == []

    async def test_respects_limit_parameter(
        self,
        session_repository: SessionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should apply limit to query."""
        mock_query = MagicMock()
        mock_query.get = AsyncMock(return_value=[])
        mock_limit = MagicMock(return_value=mock_query)
        (
            mock_firestore_client.collection.return_value.where.return_value.where.return_value.order_by.return_value.limit
        ) = mock_limit

        await session_repository.list_by_user("test_user", limit=10)

        mock_limit.assert_called_with(10)
