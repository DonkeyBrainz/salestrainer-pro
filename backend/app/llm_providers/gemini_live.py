"""Gemini implementation of the LLMStreamProvider interface.

Thin adapter delegating to the existing ``GeminiService.connect_live`` — the
Gemini Live path is unchanged; this only wraps it behind the provider-agnostic
protocol so the relay can be provider-selected.
"""

from contextlib import AbstractAsyncContextManager

from app.config import Settings
from app.llm_providers.streaming import LiveSession
from app.services.gemini_service import GeminiService


class GeminiLiveProvider:
    """LLMStreamProvider backed by Gemini Live."""

    name = "gemini"

    def __init__(self, settings: Settings, gemini_service: GeminiService | None = None) -> None:
        """Initialize the provider.

        Args:
            settings: Application settings.
            gemini_service: Existing GeminiService to reuse (avoids constructing
                a second genai client). Defaults to a new instance.
        """
        self._settings = settings
        self._gemini_service = gemini_service or GeminiService(settings=settings)

    def connect_live(
        self,
        *,
        system_instruction: str | None = None,
        voice: str | None = None,
        resumption_handle: str | None = None,
    ) -> AbstractAsyncContextManager[LiveSession]:
        """Open a Gemini Live session (delegates to GeminiService)."""
        return self._gemini_service.connect_live(
            system_instruction=system_instruction,
            voice_name=voice,
            resumption_handle=resumption_handle,
        )
