"""Unit tests for TranscriptRepository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.transcript import (
    MessageRole,
    TranscriptCreate,
    TranscriptMessage,
)
from app.repositories.transcript_repository import TranscriptRepository


@pytest.fixture
def mock_firestore_client() -> MagicMock:
    """Create a mock Firestore client.

    Uses MagicMock because collection() is synchronous.
    Only get/set/update calls are async.
    """
    return MagicMock()


@pytest.fixture
def transcript_repository(mock_firestore_client: MagicMock) -> TranscriptRepository:
    """Create TranscriptRepository with mocked Firestore client."""
    return TranscriptRepository(db=mock_firestore_client)


@pytest.fixture
def sample_messages() -> list[TranscriptMessage]:
    """Sample conversation messages for testing."""
    return [
        TranscriptMessage(
            message_id=str(uuid4()),
            role=MessageRole.USER,
            text="Hello there",
            timestamp=datetime.now(UTC),
        ),
        TranscriptMessage(
            message_id=str(uuid4()),
            role=MessageRole.ASSISTANT,
            text="Hi! How can I help you?",
            timestamp=datetime.now(UTC),
        ),
    ]


class TestCreate:
    """Tests for create method."""

    async def test_creates_transcript_with_id(
        self,
        transcript_repository: TranscriptRepository,
        mock_firestore_client: MagicMock,
        sample_messages: list[TranscriptMessage],
    ) -> None:
        """Should create transcript with generated UUID."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        transcript_create = TranscriptCreate(
            session_id=str(uuid4()),
            user_id="test_user",
            messages=sample_messages,
        )

        result = await transcript_repository.create(transcript_create)

        assert result.transcript_id is not None
        assert result.user_id == "test_user"
        assert len(result.messages) == 2
        mock_firestore_client.collection.assert_called_with("transcripts")

    async def test_calculates_word_count(
        self,
        transcript_repository: TranscriptRepository,
        mock_firestore_client: MagicMock,
        sample_messages: list[TranscriptMessage],
    ) -> None:
        """Should calculate total word count from messages."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        transcript_create = TranscriptCreate(
            session_id=str(uuid4()),
            user_id="test_user",
            messages=sample_messages,
        )

        result = await transcript_repository.create(transcript_create)

        # "Hello there" = 2 words, "Hi! How can I help you?" = 6 words
        assert result.total_words == 8
        assert result.total_messages == 2

    async def test_handles_empty_messages(
        self,
        transcript_repository: TranscriptRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should handle transcript with no messages."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        transcript_create = TranscriptCreate(
            session_id=str(uuid4()),
            user_id="test_user",
            messages=[],
        )

        result = await transcript_repository.create(transcript_create)

        assert result.total_messages == 0
        assert result.total_words == 0
        assert result.messages == []

    async def test_sets_time_span_from_messages(
        self,
        transcript_repository: TranscriptRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should set started_at and ended_at from message timestamps."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        first_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        last_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=UTC)

        messages = [
            TranscriptMessage(
                message_id=str(uuid4()),
                role=MessageRole.USER,
                text="First message",
                timestamp=first_time,
            ),
            TranscriptMessage(
                message_id=str(uuid4()),
                role=MessageRole.ASSISTANT,
                text="Last message",
                timestamp=last_time,
            ),
        ]

        transcript_create = TranscriptCreate(
            session_id=str(uuid4()),
            user_id="test_user",
            messages=messages,
        )

        result = await transcript_repository.create(transcript_create)

        assert result.started_at == first_time
        assert result.ended_at == last_time


class TestGetById:
    """Tests for get_by_id method."""

    async def test_returns_transcript_when_exists(
        self,
        transcript_repository: TranscriptRepository,
        mock_firestore_client: MagicMock,
        sample_messages: list[TranscriptMessage],
    ) -> None:
        """Should return Transcript when document exists."""
        transcript_data = {
            "session_id": str(uuid4()),
            "user_id": "test_user",
            "messages": [msg.model_dump() for msg in sample_messages],
            "total_messages": 2,
            "total_words": 8,
            "started_at": datetime.now(UTC),
            "ended_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = transcript_data

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await transcript_repository.get_by_id("transcript-123")

        assert result is not None
        assert result.transcript_id == "transcript-123"
        assert result.user_id == "test_user"
        assert len(result.messages) == 2

    async def test_returns_none_when_not_exists(
        self,
        transcript_repository: TranscriptRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return None when document doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await transcript_repository.get_by_id("nonexistent-id")

        assert result is None


class TestGetBySessionId:
    """Tests for get_by_session_id method."""

    async def test_returns_transcript_for_session(
        self,
        transcript_repository: TranscriptRepository,
        mock_firestore_client: MagicMock,
        sample_messages: list[TranscriptMessage],
    ) -> None:
        """Should return transcript for session."""
        session_id = str(uuid4())
        transcript_data = {
            "session_id": session_id,
            "user_id": "test_user",
            "messages": [msg.model_dump() for msg in sample_messages],
            "total_messages": 2,
            "total_words": 8,
            "started_at": datetime.now(UTC),
            "ended_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        mock_doc = MagicMock()
        mock_doc.id = "transcript-123"
        mock_doc.to_dict.return_value = transcript_data

        async def mock_stream():
            yield mock_doc

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_stream()
        mock_firestore_client.collection.return_value.where.return_value.limit.return_value = (
            mock_query
        )

        result = await transcript_repository.get_by_session_id(session_id)

        assert result is not None
        assert result.session_id == session_id
        assert len(result.messages) == 2

    async def test_returns_none_when_no_transcript(
        self,
        transcript_repository: TranscriptRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return None when no transcript for session."""

        async def mock_stream():
            return
            yield  # Make it an async generator

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_stream()
        mock_firestore_client.collection.return_value.where.return_value.limit.return_value = (
            mock_query
        )

        result = await transcript_repository.get_by_session_id("session-no-transcript")

        assert result is None


class TestWordCountCalculation:
    """Tests for word count calculation."""

    async def test_counts_words_correctly(
        self,
        transcript_repository: TranscriptRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should count words across all messages."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        messages = [
            TranscriptMessage(
                message_id=str(uuid4()),
                role=MessageRole.USER,
                text="One two three",
                timestamp=datetime.now(UTC),
            ),
            TranscriptMessage(
                message_id=str(uuid4()),
                role=MessageRole.ASSISTANT,
                text="Four five",
                timestamp=datetime.now(UTC),
            ),
        ]

        transcript_create = TranscriptCreate(
            session_id=str(uuid4()),
            user_id="test_user",
            messages=messages,
        )

        result = await transcript_repository.create(transcript_create)

        assert result.total_words == 5  # "One two three Four five"


class TestMessageDeserialization:
    """Tests for message deserialization from Firestore."""

    async def test_deserializes_messages_correctly(
        self,
        transcript_repository: TranscriptRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should properly deserialize message objects from Firestore."""
        message_data = [
            {
                "message_id": "msg-1",
                "role": "user",
                "text": "Hello",
                "timestamp": datetime.now(UTC),
                "is_final": True,
                "audio_length_ms": 1500,
                "confidence": 0.95,
            },
            {
                "message_id": "msg-2",
                "role": "assistant",
                "text": "Hi there!",
                "timestamp": datetime.now(UTC),
                "is_final": True,
            },
        ]

        transcript_data = {
            "session_id": str(uuid4()),
            "user_id": "test_user",
            "messages": message_data,
            "total_messages": 2,
            "total_words": 3,
            "started_at": datetime.now(UTC),
            "ended_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = transcript_data

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await transcript_repository.get_by_id("transcript-123")

        assert result is not None
        assert len(result.messages) == 2
        assert result.messages[0].role == MessageRole.USER
        assert result.messages[0].text == "Hello"
        assert result.messages[0].audio_length_ms == 1500
        assert result.messages[0].confidence == 0.95
        assert result.messages[1].role == MessageRole.ASSISTANT
