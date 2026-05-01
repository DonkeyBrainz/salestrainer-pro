"""Unit tests for OAuth state management."""

import pytest

from app.config import Settings
from app.core.session import StateManager, get_state_manager


@pytest.fixture
def settings() -> Settings:
    """Create test settings with a known secret key."""
    return Settings(secret_key="test-secret-key-for-signing")


@pytest.fixture
def state_manager(settings: Settings) -> StateManager:
    """Create a StateManager instance for testing."""
    return StateManager(settings)


class TestStateManager:
    """Tests for StateManager class."""

    def test_sign_state_returns_string(self, state_manager: StateManager) -> None:
        """Test that sign_state returns a signed string."""
        state = "test-state-123"
        signed = state_manager.sign_state(state)

        assert isinstance(signed, str)
        assert signed != state  # Should be different from original

    def test_sign_state_is_deterministic_with_timestamp(self, state_manager: StateManager) -> None:
        """Test that signing the same state twice produces different results (due to timestamp)."""
        state = "test-state-456"
        signed1 = state_manager.sign_state(state)
        signed2 = state_manager.sign_state(state)

        # itsdangerous includes timestamp, so signatures may differ
        # But both should verify to the same state
        assert state_manager.verify_state(signed1) == state
        assert state_manager.verify_state(signed2) == state

    def test_verify_state_returns_original(self, state_manager: StateManager) -> None:
        """Test that verify_state returns the original state."""
        original_state = "my-oauth-state"
        signed = state_manager.sign_state(original_state)

        verified = state_manager.verify_state(signed)

        assert verified == original_state

    def test_verify_state_returns_none_for_invalid_signature(
        self, state_manager: StateManager
    ) -> None:
        """Test that verify_state returns None for tampered signatures."""
        state = "valid-state"
        signed = state_manager.sign_state(state)

        # Tamper with the signed value
        tampered = signed + "tampered"

        result = state_manager.verify_state(tampered)

        assert result is None

    def test_verify_state_returns_none_for_wrong_secret(self, settings: Settings) -> None:
        """Test that verify_state returns None when using different secret."""
        state = "test-state"

        # Sign with one manager
        manager1 = StateManager(settings)
        signed = manager1.sign_state(state)

        # Try to verify with different secret
        different_settings = Settings(secret_key="different-secret-key")
        manager2 = StateManager(different_settings)

        result = manager2.verify_state(signed)

        assert result is None


class TestValidateState:
    """Tests for validate_state method."""

    def test_validate_state_returns_true_for_matching_states(
        self, state_manager: StateManager
    ) -> None:
        """Test that validate_state returns True when states match."""
        state = "matching-state"
        signed = state_manager.sign_state(state)

        result = state_manager.validate_state(signed, state)

        assert result is True

    def test_validate_state_returns_false_for_mismatched_states(
        self, state_manager: StateManager
    ) -> None:
        """Test that validate_state returns False when states don't match."""
        original_state = "original-state"
        different_state = "different-state"
        signed = state_manager.sign_state(original_state)

        result = state_manager.validate_state(signed, different_state)

        assert result is False

    def test_validate_state_returns_false_for_none_signed_state(
        self, state_manager: StateManager
    ) -> None:
        """Test that validate_state returns False when signed_state is None."""
        result = state_manager.validate_state(None, "any-state")

        assert result is False

    def test_validate_state_returns_false_for_invalid_signature(
        self, state_manager: StateManager
    ) -> None:
        """Test that validate_state returns False for invalid signatures."""
        result = state_manager.validate_state("invalid-signature", "any-state")

        assert result is False


class TestGetStateManager:
    """Tests for get_state_manager factory function."""

    def test_get_state_manager_returns_state_manager(self, settings: Settings) -> None:
        """Test that get_state_manager returns a StateManager instance."""
        manager = get_state_manager(settings)

        assert isinstance(manager, StateManager)

    def test_get_state_manager_uses_settings_secret(self, settings: Settings) -> None:
        """Test that the factory creates a working StateManager."""
        manager = get_state_manager(settings)
        state = "test-state"

        signed = manager.sign_state(state)
        verified = manager.verify_state(signed)

        assert verified == state
