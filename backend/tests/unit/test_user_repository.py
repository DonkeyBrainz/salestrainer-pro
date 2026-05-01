"""Tests for UserRepository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.auth import GoogleUserInfo
from app.models.user import UserCreate
from app.repositories.user_repository import UserRepository


@pytest.fixture
def mock_firestore_client() -> MagicMock:
    """Create a mock Firestore client.

    Uses MagicMock because collection() is synchronous.
    Only get/set/update calls are async.
    """
    return MagicMock()


@pytest.fixture
def user_repository(mock_firestore_client: MagicMock) -> UserRepository:
    """Create UserRepository with mocked Firestore client."""
    return UserRepository(db=mock_firestore_client)


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user document data from Firestore."""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "google_id": "google-123",
        "picture_url": "https://example.com/pic.jpg",
        "preferences": {
            "voice_name": "Zephyr",
            "difficulty": "intermediate",
            "theme": "light",
            "notifications_enabled": True,
        },
        "created_at": datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
        "updated_at": None,
    }


class TestGetById:
    """Tests for get_by_id method."""

    async def test_returns_user_when_exists(
        self,
        user_repository: UserRepository,
        mock_firestore_client: MagicMock,
        sample_user_data: dict,
    ) -> None:
        """Should return User when document exists."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "user-123"
        mock_doc.to_dict.return_value = sample_user_data

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await user_repository.get_by_id("user-123")

        assert result is not None
        assert result.user_id == "user-123"
        assert result.email == "test@example.com"
        assert result.name == "Test User"

    async def test_returns_none_when_not_exists(
        self,
        user_repository: UserRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return None when document doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await user_repository.get_by_id("nonexistent-id")

        assert result is None


class TestGetByGoogleId:
    """Tests for get_by_google_id method."""

    async def test_returns_user_when_exists(
        self,
        user_repository: UserRepository,
        mock_firestore_client: MagicMock,
        sample_user_data: dict,
    ) -> None:
        """Should return User when found by Google ID."""
        mock_doc = MagicMock()
        mock_doc.id = "user-123"
        mock_doc.to_dict.return_value = sample_user_data

        async def mock_stream():
            yield mock_doc

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_stream()
        mock_firestore_client.collection.return_value.where.return_value.limit.return_value = (
            mock_query
        )

        result = await user_repository.get_by_google_id("google-123")

        assert result is not None
        assert result.google_id == "google-123"

    async def test_returns_none_when_not_exists(
        self,
        user_repository: UserRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return None when not found by Google ID."""

        async def mock_stream():
            return
            yield  # Make it an async generator

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_stream()
        mock_firestore_client.collection.return_value.where.return_value.limit.return_value = (
            mock_query
        )

        result = await user_repository.get_by_google_id("nonexistent-google-id")

        assert result is None


class TestCreate:
    """Tests for create method."""

    async def test_creates_user_in_firestore(
        self,
        user_repository: UserRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should create user and return User model."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        user_create = UserCreate(
            email="new@example.com",
            name="New User",
            google_id="google-new",
            picture_url="https://example.com/new.jpg",
        )

        with patch("app.repositories.user_repository.uuid4") as mock_uuid:
            mock_uuid.return_value = MagicMock(__str__=lambda _: "generated-uuid")
            result = await user_repository.create(user_create)

        assert result.user_id == "generated-uuid"
        assert result.email == "new@example.com"
        assert result.name == "New User"
        assert result.google_id == "google-new"
        assert result.created_at is not None
        assert result.updated_at is None

    async def test_create_sets_default_preferences(
        self,
        user_repository: UserRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should set default preferences for new user."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        user_create = UserCreate(
            email="new@example.com",
            name="New User",
            google_id="google-new",
        )

        result = await user_repository.create(user_create)

        # voice_name removed - voices are now persona-specific
        assert result.preferences.difficulty == "intermediate"
        assert result.preferences.theme == "light"
        assert result.preferences.notifications_enabled is True


class TestUpdate:
    """Tests for update method."""

    async def test_updates_user_fields(
        self,
        user_repository: UserRepository,
        mock_firestore_client: MagicMock,
        sample_user_data: dict,
    ) -> None:
        """Should update specified fields."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "user-123"
        mock_doc.to_dict.return_value = {**sample_user_data, "name": "Updated Name"}

        doc_ref = mock_firestore_client.collection.return_value.document.return_value
        doc_ref.get = AsyncMock(return_value=mock_doc)
        doc_ref.update = AsyncMock()

        result = await user_repository.update("user-123", {"name": "Updated Name"})

        assert result is not None
        assert result.name == "Updated Name"
        doc_ref.update.assert_called_once()

    async def test_returns_none_if_not_exists(
        self,
        user_repository: UserRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return None if user doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await user_repository.update("nonexistent", {"name": "New Name"})

        assert result is None


class TestUpsertFromGoogle:
    """Tests for upsert_from_google method."""

    async def test_creates_new_user_when_not_exists(
        self,
        user_repository: UserRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should create new user when Google ID not found."""

        async def mock_stream():
            return
            yield

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_stream()
        mock_firestore_client.collection.return_value.where.return_value.limit.return_value = (
            mock_query
        )
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        google_info = GoogleUserInfo(
            id="new-google-id",
            email="new@gmail.com",
            name="New Google User",
            picture="https://google.com/pic.jpg",
            verified_email=True,
        )

        result = await user_repository.upsert_from_google(google_info)

        assert result.email == "new@gmail.com"
        assert result.name == "New Google User"
        assert result.google_id == "new-google-id"

    async def test_updates_existing_user(
        self,
        user_repository: UserRepository,
        mock_firestore_client: MagicMock,
        sample_user_data: dict,
    ) -> None:
        """Should update existing user when Google ID found."""
        mock_doc = MagicMock()
        mock_doc.id = "existing-user-id"
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_user_data

        async def mock_stream():
            yield mock_doc

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_stream()
        mock_firestore_client.collection.return_value.where.return_value.limit.return_value = (
            mock_query
        )

        updated_data = {**sample_user_data, "name": "Updated Name", "picture_url": "new-pic.jpg"}
        updated_doc = MagicMock()
        updated_doc.id = "existing-user-id"
        updated_doc.exists = True
        updated_doc.to_dict.return_value = updated_data

        doc_ref = mock_firestore_client.collection.return_value.document.return_value
        doc_ref.get = AsyncMock(side_effect=[mock_doc, updated_doc])
        doc_ref.update = AsyncMock()

        google_info = GoogleUserInfo(
            id="google-123",
            email="test@example.com",
            name="Updated Name",
            picture="new-pic.jpg",
            verified_email=True,
        )

        result = await user_repository.upsert_from_google(google_info)

        assert result.name == "Updated Name"
