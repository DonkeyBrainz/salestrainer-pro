"""Tests for the LLMStreamProvider protocol, Gemini wrapper, and registry."""

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import InvalidRequestError
from app.llm_providers.gemini_live import GeminiLiveProvider
from app.llm_providers.registry import LIVE_PROVIDERS, build_live_provider
from app.llm_providers.streaming import LiveSession, LLMStreamProvider
from app.services.gemini_service import GeminiLiveSession


@pytest.fixture
def mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.gemini_api_key = "test-key"
    return settings


class TestProtocolConformance:
    def test_gemini_live_session_satisfies_live_session(self) -> None:
        # runtime_checkable structural check: the existing session is a LiveSession.
        assert issubclass(GeminiLiveSession, LiveSession)

    def test_gemini_provider_satisfies_stream_provider(self, mock_settings: MagicMock) -> None:
        provider = GeminiLiveProvider(mock_settings, gemini_service=MagicMock())
        assert isinstance(provider, LLMStreamProvider)
        assert provider.name == "gemini"


class TestGeminiLiveProvider:
    def test_connect_live_forwards_args(self, mock_settings: MagicMock) -> None:
        mock_service = MagicMock()
        sentinel = object()
        mock_service.connect_live.return_value = sentinel
        provider = GeminiLiveProvider(mock_settings, gemini_service=mock_service)

        result = provider.connect_live(
            system_instruction="be a customer",
            voice="puck",
            resumption_handle="handle-123",
        )

        assert result is sentinel
        mock_service.connect_live.assert_called_once_with(
            system_instruction="be a customer",
            voice_name="puck",  # note: 'voice' -> 'voice_name' at the SDK boundary
            resumption_handle="handle-123",
        )

    def test_reuses_injected_service(self, mock_settings: MagicMock) -> None:
        mock_service = MagicMock()
        provider = GeminiLiveProvider(mock_settings, gemini_service=mock_service)
        assert provider._gemini_service is mock_service


class TestRegistry:
    def test_gemini_registered(self) -> None:
        assert "gemini" in LIVE_PROVIDERS

    def test_build_known_provider(self, mock_settings: MagicMock) -> None:
        provider = build_live_provider("gemini", mock_settings)
        assert isinstance(provider, GeminiLiveProvider)

    def test_build_unknown_provider_raises(self, mock_settings: MagicMock) -> None:
        with pytest.raises(InvalidRequestError, match="Unknown live provider"):
            build_live_provider("does_not_exist", mock_settings)
