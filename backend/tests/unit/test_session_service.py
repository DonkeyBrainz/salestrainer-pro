"""Unit tests for SessionService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.session import (
    Difficulty,
    Session,
    SessionCreate,
    SessionStatus,
    SessionType,
)
from app.models.transcript import (
    MessageRole,
    Transcript,
    TranscriptMessage,
)
from app.services.session_service import SessionService


@pytest.fixture
def mock_session_repo():
    """Mock SessionRepository."""
    return AsyncMock()


@pytest.fixture
def mock_transcript_repo():
    """Mock TranscriptRepository."""
    return AsyncMock()


@pytest.fixture
def mock_user_repo():
    """Mock UserRepository."""
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    return repo


@pytest.fixture
def session_service(mock_session_repo, mock_transcript_repo, mock_user_repo):
    """SessionService with mocked repositories."""
    return SessionService(
        session_repository=mock_session_repo,
        transcript_repository=mock_transcript_repo,
        user_repository=mock_user_repo,
    )


@pytest.fixture
def sample_session():
    """Sample session for testing."""
    return Session(
        session_id=str(uuid4()),
        user_id="test_user",
        session_type=SessionType.TRAINING,
        status=SessionStatus.ACTIVE,
        difficulty=Difficulty.MEDIUM_REGARD,
        started_at=datetime.now(UTC),
        message_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_messages():
    """Sample conversation messages."""
    return [
        TranscriptMessage(
            message_id=str(uuid4()),
            role=MessageRole.USER,
            text="Hello",
            timestamp=datetime.now(UTC),
        ),
        TranscriptMessage(
            message_id=str(uuid4()),
            role=MessageRole.ASSISTANT,
            text="Hi there!",
            timestamp=datetime.now(UTC),
        ),
    ]


class TestStartSession:
    """Tests for start_session method."""

    async def test_creates_session(self, session_service, mock_session_repo, sample_session):
        """Should create session via repository."""
        mock_session_repo.create.return_value = sample_session

        session_create = SessionCreate(
            user_id="test_user",
            session_type=SessionType.TRAINING,
            difficulty=Difficulty.MEDIUM_REGARD,
        )

        result = await session_service.start_session(session_create)

        mock_session_repo.create.assert_called_once_with(session_create, store_id=None)
        assert result == sample_session

    async def test_returns_session_with_id(
        self, session_service, mock_session_repo, sample_session
    ):
        """Should return session with generated ID."""
        mock_session_repo.create.return_value = sample_session

        session_create = SessionCreate(user_id="test_user")
        result = await session_service.start_session(session_create)

        assert result.session_id is not None
        assert result.user_id == "test_user"
        assert result.status == SessionStatus.ACTIVE


class TestEndSession:
    """Tests for end_session method."""

    async def test_updates_session_status(
        self,
        session_service,
        mock_session_repo,
        mock_transcript_repo,
        sample_session,
        sample_messages,
    ):
        """Should update session status to completed."""
        mock_session_repo.get_by_id.return_value = sample_session

        await session_service.end_session(
            session_id=sample_session.session_id,
            messages=sample_messages,
            status=SessionStatus.COMPLETED,
        )

        # Check update was called
        update_call = mock_session_repo.update.call_args
        assert update_call[0][0] == sample_session.session_id
        session_update = update_call[0][1]
        assert session_update.status == SessionStatus.COMPLETED

    async def test_saves_transcript(
        self,
        session_service,
        mock_session_repo,
        mock_transcript_repo,
        sample_session,
        sample_messages,
    ):
        """Should save transcript with messages."""
        mock_session_repo.get_by_id.return_value = sample_session

        await session_service.end_session(
            session_id=sample_session.session_id,
            messages=sample_messages,
        )

        # Check transcript was created
        create_call = mock_transcript_repo.create.call_args
        transcript_create = create_call[0][0]
        assert transcript_create.session_id == sample_session.session_id
        assert transcript_create.user_id == sample_session.user_id
        assert transcript_create.messages == sample_messages

    async def test_calculates_duration(
        self,
        session_service,
        mock_session_repo,
        mock_transcript_repo,
        sample_session,
        sample_messages,
    ):
        """Should calculate session duration in seconds."""
        mock_session_repo.get_by_id.return_value = sample_session

        await session_service.end_session(
            session_id=sample_session.session_id,
            messages=sample_messages,
        )

        update_call = mock_session_repo.update.call_args
        session_update = update_call[0][1]
        assert session_update.duration is not None
        assert session_update.duration >= 0

    async def test_raises_error_if_session_not_found(
        self, session_service, mock_session_repo, sample_messages
    ):
        """Should raise ValueError if session doesn't exist."""
        mock_session_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Session .* not found"):
            await session_service.end_session(
                session_id="nonexistent",
                messages=sample_messages,
            )


class TestGetSession:
    """Tests for get_session method."""

    async def test_returns_session(self, session_service, mock_session_repo, sample_session):
        """Should return session from repository."""
        mock_session_repo.get_by_id.return_value = sample_session

        result = await session_service.get_session(sample_session.session_id)

        mock_session_repo.get_by_id.assert_called_once_with(sample_session.session_id)
        assert result == sample_session


class TestGetTranscript:
    """Tests for get_transcript method."""

    async def test_returns_transcript(self, session_service, mock_transcript_repo):
        """Should return transcript from repository."""
        session_id = str(uuid4())
        transcript = Transcript(
            transcript_id=str(uuid4()),
            session_id=session_id,
            user_id="test_user",
            messages=[],
            total_messages=0,
            total_words=0,
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_transcript_repo.get_by_session_id.return_value = transcript

        result = await session_service.get_transcript(session_id)

        mock_transcript_repo.get_by_session_id.assert_called_once_with(session_id)
        assert result == transcript
