"""Provider-agnostic speech-to-speech (Live) streaming interface.

Sibling to the turn-based ``LLMProvider`` (base.py). A ``LLMStreamProvider``
opens a bidirectional audio session; the WebSocket relay drives it identically
regardless of vendor because every adapter emits the same ``LiveEvent`` dict
vocabulary that ``GeminiLiveSession`` already produces.

LiveEvent vocabulary (dict with a ``type`` key):

Required for every provider — the relay depends on these:
    - ``audio``:                {"type", "audio_data": bytes, "text": None}
                                raw PCM16 @ 24kHz (browser playback rate)
    - ``input_transcription``:  {"type", "audio_data": None, "text": str,
                                 "finished": bool}   (user speech, ASR)
    - ``output_transcription``: {"type", "audio_data": None, "text": str,
                                 "finished": bool}   (model speech, transcript)
    - ``end``:                  {"type", "audio_data": None, "text": None}
                                (turn complete)
    - ``interrupted``:          {"type", "audio_data": None, "text": None}
                                (barge-in: the user spoke over the model; the
                                relay forwards this so the client flushes any
                                buffered/scheduled playback immediately)

Optional / provider-specific — the relay treats these as best-effort:
    - ``internal_reasoning``:        model's unspoken text (Gemini)
    - ``session_resumption_update``: {"new_handle", "resumable"} (Gemini)
    - ``go_away``:                   {"time_left"} (Gemini server drain notice)
    - ``usage``:                     {"usage": {"prompt_tokens",
                                     "completion_tokens", "total_tokens"},
                                     "detail": {...vendor audio/text token
                                     breakdown...}} — billed token counts, all
                                     three providers; consumed by the voice
                                     eval harness for cost accounting (the
                                     relay ignores it)

Non-Gemini adapters simply never emit the optional events; the relay's
reconnection logic keys off ``go_away`` / ``session_resumption_update`` and so
degrades to connect-once for providers that don't produce them.

Adapters raise the ``app.core.exceptions`` taxonomy (InvalidRequestError,
RateLimitError, ServiceUnavailableError, InternalError) so the relay's existing
error handling works unchanged.
"""

from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol, runtime_checkable

LiveEvent = dict[str, Any]


@runtime_checkable
class LiveSession(Protocol):
    """A live bidirectional audio session.

    Structurally satisfied by the existing ``GeminiLiveSession`` — new adapters
    implement the same four methods.
    """

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> None:
        """Send raw PCM16 audio (16kHz mono, as the browser captures it)."""
        ...

    async def send_text(self, text: str) -> None:
        """Send a text turn to the model."""
        ...

    def receive(self) -> AsyncGenerator[LiveEvent]:
        """Yield ``LiveEvent`` dicts until the session ends."""
        ...

    async def close(self) -> None:
        """Close the session. Safe to call more than once."""
        ...


@runtime_checkable
class LLMStreamProvider(Protocol):
    """Opens ``LiveSession`` instances for a specific speech-to-speech backend."""

    name: str

    def connect_live(
        self,
        *,
        system_instruction: str | None = None,
        voice: str | None = None,
        resumption_handle: str | None = None,
    ) -> AbstractAsyncContextManager[LiveSession]:
        """Open a live session as an async context manager.

        Args:
            system_instruction: System prompt for the persona.
            voice: Provider-specific prebuilt voice ID (already resolved via
                ``app.llm_providers.voices.resolve_voice``).
            resumption_handle: Gemini-only resumption handle; other providers
                accept and ignore it.
        """
        ...
