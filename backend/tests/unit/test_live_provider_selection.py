"""Tests for live-provider selection (allowlist gating + gemini reuse)."""

from unittest.mock import MagicMock

from app.config import Settings
from app.core.dependencies import get_live_provider
from app.llm_providers.gemini_live import GeminiLiveProvider
from app.llm_providers.openai_realtime import OpenAIRealtimeProvider


def _settings(**overrides: object) -> Settings:
    base = {
        "gemini_api_key": "g",
        "openai_api_key": "o",
        "live_provider": "gemini",
        "live_provider_allowlist": ["gemini", "openai"],
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


class TestGetLiveProvider:
    def test_gemini_reuses_injected_service(self) -> None:
        gemini_service = MagicMock()
        provider = get_live_provider("gemini", _settings(), gemini_service)
        assert isinstance(provider, GeminiLiveProvider)
        assert provider._gemini_service is gemini_service

    def test_openai_provider_built(self) -> None:
        provider = get_live_provider("openai", _settings(), MagicMock())
        assert isinstance(provider, OpenAIRealtimeProvider)

    def test_unknown_provider_returns_none(self) -> None:
        assert get_live_provider("does_not_exist", _settings(), MagicMock()) is None

    def test_provider_not_in_allowlist_returns_none(self) -> None:
        # 'openai' is a registered provider but excluded from the allowlist here.
        settings = _settings(live_provider_allowlist=["gemini"])
        assert get_live_provider("openai", settings, MagicMock()) is None
