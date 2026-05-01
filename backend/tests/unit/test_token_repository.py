"""Tests for TokenRepository."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.token_repository import TokenRepository


@pytest.fixture
def mock_firestore_client() -> MagicMock:
    """Create a mock Firestore client."""
    return MagicMock()


@pytest.fixture
def token_repository(mock_firestore_client: MagicMock) -> TokenRepository:
    """Create TokenRepository with mocked Firestore client."""
    return TokenRepository(db=mock_firestore_client)


class TestHashToken:
    """Tests for hash_token static method."""

    def test_hash_token_returns_consistent_hash(self) -> None:
        """Should return same hash for same token."""
        token = "test-token-123"
        hash1 = TokenRepository.hash_token(token)
        hash2 = TokenRepository.hash_token(token)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest length

    def test_hash_token_returns_different_hash_for_different_tokens(self) -> None:
        """Should return different hashes for different tokens."""
        hash1 = TokenRepository.hash_token("token-1")
        hash2 = TokenRepository.hash_token("token-2")

        assert hash1 != hash2


class TestStoreRefreshToken:
    """Tests for store_refresh_token method."""

    async def test_stores_hashed_token(
        self,
        token_repository: TokenRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should store token with hash as document ID."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        token = "raw-token-value"
        expires_at = datetime.now(UTC) + timedelta(days=30)

        await token_repository.store_refresh_token(
            user_id="user-123",
            token=token,
            expires_at=expires_at,
        )

        # Verify document was created with hashed token as ID
        expected_hash = TokenRepository.hash_token(token)
        mock_firestore_client.collection.return_value.document.assert_called_with(expected_hash)
        mock_firestore_client.collection.return_value.document.return_value.set.assert_called_once()


class TestIsTokenValid:
    """Tests for is_token_valid method."""

    async def test_returns_true_for_valid_token(
        self,
        token_repository: TokenRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return True for valid, non-expired, non-revoked token."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "revoked": False,
            "expires_at": datetime.now(UTC) + timedelta(days=1),
        }

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await token_repository.is_token_valid("valid-token")

        assert result is True

    async def test_returns_false_for_nonexistent_token(
        self,
        token_repository: TokenRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return False when token doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await token_repository.is_token_valid("nonexistent-token")

        assert result is False

    async def test_returns_false_for_revoked_token(
        self,
        token_repository: TokenRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return False when token is revoked."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "revoked": True,
            "expires_at": datetime.now(UTC) + timedelta(days=1),
        }

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await token_repository.is_token_valid("revoked-token")

        assert result is False

    async def test_returns_false_for_expired_token(
        self,
        token_repository: TokenRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return False when token is expired."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "revoked": False,
            "expires_at": datetime.now(UTC) - timedelta(days=1),  # Expired
        }

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await token_repository.is_token_valid("expired-token")

        assert result is False


class TestRevokeToken:
    """Tests for revoke_token method."""

    async def test_revokes_existing_token(
        self,
        token_repository: TokenRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should mark token as revoked."""
        mock_doc = MagicMock()
        mock_doc.exists = True

        doc_ref = mock_firestore_client.collection.return_value.document.return_value
        doc_ref.get = AsyncMock(return_value=mock_doc)
        doc_ref.update = AsyncMock()

        await token_repository.revoke_token("token-to-revoke")

        doc_ref.update.assert_called_once()
        call_args = doc_ref.update.call_args[0][0]
        assert call_args["revoked"] is True
        assert "revoked_at" in call_args

    async def test_does_nothing_for_nonexistent_token(
        self,
        token_repository: TokenRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should not error when token doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False

        doc_ref = mock_firestore_client.collection.return_value.document.return_value
        doc_ref.get = AsyncMock(return_value=mock_doc)
        doc_ref.update = AsyncMock()

        await token_repository.revoke_token("nonexistent-token")

        doc_ref.update.assert_not_called()


class TestRevokeAllUserTokens:
    """Tests for revoke_all_user_tokens method."""

    async def test_revokes_all_user_tokens(
        self,
        token_repository: TokenRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should revoke all non-revoked tokens for user."""
        mock_doc1 = MagicMock()
        mock_doc1.id = "token-hash-1"
        mock_doc2 = MagicMock()
        mock_doc2.id = "token-hash-2"

        async def mock_stream():
            yield mock_doc1
            yield mock_doc2

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_stream()
        mock_firestore_client.collection.return_value.where.return_value.where.return_value = (
            mock_query
        )
        mock_firestore_client.collection.return_value.document.return_value.update = AsyncMock()

        result = await token_repository.revoke_all_user_tokens("user-123")

        assert result == 2


class TestCleanupExpiredTokens:
    """Tests for cleanup_expired_tokens method."""

    async def test_deletes_expired_tokens(
        self,
        token_repository: TokenRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should delete all expired tokens."""
        mock_doc1 = MagicMock()
        mock_doc1.id = "expired-token-1"
        mock_doc2 = MagicMock()
        mock_doc2.id = "expired-token-2"

        async def mock_stream():
            yield mock_doc1
            yield mock_doc2

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_stream()
        mock_firestore_client.collection.return_value.where.return_value = mock_query
        mock_firestore_client.collection.return_value.document.return_value.delete = AsyncMock()

        result = await token_repository.cleanup_expired_tokens()

        assert result == 2
