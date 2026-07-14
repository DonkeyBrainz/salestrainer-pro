"""OpenAI Realtime implementation of the LLMStreamProvider interface.

Drives an OpenAI Realtime WebSocket session and translates its server events
into the same ``LiveEvent`` dict vocabulary the relay already consumes from
Gemini. Inbound browser audio (16 kHz PCM16) is upsampled to the 24 kHz the
Realtime API expects; outbound audio is already 24 kHz (browser playback rate).

Event names follow the GA ``gpt-realtime`` protocol, with the older beta names
accepted as fallbacks so the adapter tolerates both. Verify against the current
OpenAI Realtime docs if the API changes.
"""

import base64
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed, InvalidStatus

from app.config import Settings
from app.core.exceptions import (
    InternalError,
    InvalidRequestError,
    RateLimitError,
    ServiceUnavailableError,
)
from app.llm_providers.audio import PcmResampler
from app.llm_providers.streaming import LiveEvent, LiveSession

logger = logging.getLogger(__name__)

_REALTIME_URL = "wss://api.openai.com/v1/realtime"
_BROWSER_SAMPLE_RATE = 16000
_OPENAI_SAMPLE_RATE = 24000

# Server event types -> handling. GA names first; beta aliases included.
_AUDIO_DELTA_EVENTS = frozenset({"response.output_audio.delta", "response.audio.delta"})
_OUTPUT_TRANSCRIPT_EVENTS = frozenset(
    {"response.output_audio_transcript.delta", "response.audio_transcript.delta"}
)
_INPUT_TRANSCRIPT_DONE = "conversation.item.input_audio_transcription.completed"
_RESPONSE_DONE_EVENTS = frozenset({"response.done"})


class OpenAIRealtimeSession:
    """A single OpenAI Realtime WebSocket session."""

    def __init__(self, ws: ClientConnection) -> None:
        self._ws = ws
        self._closed = False
        # One resampler instance per session so fractional position carries
        # across audio chunks (16 kHz browser -> 24 kHz OpenAI).
        self._resampler = PcmResampler(_BROWSER_SAMPLE_RATE, _OPENAI_SAMPLE_RATE)

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> None:
        """Upsample browser PCM to 24 kHz and append it to the input buffer."""
        if self._closed:
            raise InternalError("Cannot send to closed Realtime session")
        resampled = self._resampler.process(audio_data)
        if not resampled:
            return
        payload = base64.b64encode(resampled).decode("ascii")
        await self._send({"type": "input_audio_buffer.append", "audio": payload})

    async def send_text(self, text: str) -> None:
        """Send a user text turn and request a response."""
        if self._closed:
            raise InternalError("Cannot send to closed Realtime session")
        await self._send(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}],
                },
            }
        )
        await self._send({"type": "response.create"})

    async def receive(self) -> AsyncGenerator[LiveEvent]:
        """Yield translated LiveEvents until the session closes."""
        if self._closed:
            raise InternalError("Cannot receive from closed Realtime session")
        try:
            async for raw in self._ws:
                event = json.loads(raw)
                # response.done carries the turn's token usage; surface it as
                # its own LiveEvent before the "end" it also translates to.
                if event.get("type") in _RESPONSE_DONE_EVENTS:
                    usage_event = self._extract_usage(event)
                    if usage_event is not None:
                        yield usage_event
                translated = self._translate(event)
                if translated is not None:
                    yield translated
        except ConnectionClosed as e:
            # Normal close -> just stop; abnormal -> surface as retryable.
            if e.rcvd is not None and e.rcvd.code not in (1000, 1001):
                raise ServiceUnavailableError(
                    f"OpenAI Realtime connection closed: {e.rcvd.code}"
                ) from e

    def _translate(self, event: dict[str, Any]) -> LiveEvent | None:
        """Map one OpenAI server event to a LiveEvent (or None to ignore)."""
        event_type = event.get("type", "")

        if event_type in _AUDIO_DELTA_EVENTS:
            delta = event.get("delta", "")
            return {"type": "audio", "audio_data": base64.b64decode(delta), "text": None}

        if event_type in _OUTPUT_TRANSCRIPT_EVENTS:
            return {
                "type": "output_transcription",
                "audio_data": None,
                "text": event.get("delta", ""),
                "finished": False,
            }

        if event_type == _INPUT_TRANSCRIPT_DONE:
            return {
                "type": "input_transcription",
                "audio_data": None,
                "text": event.get("transcript", ""),
                "finished": True,
            }

        if event_type in _RESPONSE_DONE_EVENTS:
            return {"type": "end", "audio_data": None, "text": None}

        if event_type == "error":
            raise self._map_error(event.get("error", {}))

        # session.created, response.created, speech_started/stopped, buffer
        # commits, etc. — not needed by the relay.
        logger.debug("Ignoring OpenAI Realtime event: %s", event_type)
        return None

    @staticmethod
    def _extract_usage(event: dict[str, Any]) -> LiveEvent | None:
        """Build a "usage" LiveEvent from a response.done payload (or None).

        The Realtime API reports usage on the response object, with per-modality
        breakdowns (audio vs text tokens) preserved under "detail".
        """
        usage = (event.get("response") or {}).get("usage") or {}
        prompt_tokens = int(usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
        if not total_tokens:
            return None

        detail = {
            key: usage[key]
            for key in ("input_token_details", "output_token_details")
            if isinstance(usage.get(key), dict)
        }
        return {
            "type": "usage",
            "audio_data": None,
            "text": None,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "detail": detail,
        }

    @staticmethod
    def _map_error(error: dict[str, Any]) -> Exception:
        """Map an OpenAI error payload to the app exception taxonomy."""
        code = str(error.get("code") or "")
        message = str(error.get("message") or "OpenAI Realtime error")
        if code in ("rate_limit_exceeded", "insufficient_quota"):
            return RateLimitError(message)
        if error.get("type") == "invalid_request_error":
            return InvalidRequestError(message)
        return InternalError(message)

    async def _send(self, message: dict[str, Any]) -> None:
        try:
            await self._ws.send(json.dumps(message))
        except ConnectionClosed as e:
            raise ServiceUnavailableError("OpenAI Realtime connection closed") from e

    async def close(self) -> None:
        """Close the WebSocket. Safe to call more than once."""
        if not self._closed:
            self._closed = True
            await self._ws.close()


class OpenAIRealtimeProvider:
    """LLMStreamProvider backed by the OpenAI Realtime API."""

    name = "openai"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @asynccontextmanager
    async def connect_live(
        self,
        *,
        system_instruction: str | None = None,
        voice: str | None = None,
        resumption_handle: str | None = None,  # unused: OpenAI has no resumption
    ) -> AsyncGenerator[LiveSession]:
        """Open an OpenAI Realtime session and configure it."""
        if not self._settings.openai_api_key:
            raise InvalidRequestError("OPENAI_API_KEY is not configured")

        url = f"{_REALTIME_URL}?model={self._settings.openai_realtime_model}"
        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        try:
            ws = await websockets.connect(url, additional_headers=headers)
        except InvalidStatus as e:
            raise self._map_handshake_error(e) from e
        except (OSError, ConnectionClosed) as e:
            raise ServiceUnavailableError("Could not connect to OpenAI Realtime") from e

        session = OpenAIRealtimeSession(ws)
        try:
            await self._configure(ws, system_instruction, voice)
            yield session
        finally:
            await session.close()

    async def _configure(
        self, ws: ClientConnection, system_instruction: str | None, voice: str | None
    ) -> None:
        """Send the initial session.update with audio + turn-detection config."""
        session_config: dict[str, Any] = {
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {"model": "gpt-4o-transcribe"},
            # Server VAD: the model handles turn-taking, like Gemini Live.
            "turn_detection": {"type": "server_vad"},
            "temperature": self._settings.openai_realtime_temperature,
        }
        if system_instruction:
            session_config["instructions"] = system_instruction
        if voice:
            session_config["voice"] = voice

        await ws.send(json.dumps({"type": "session.update", "session": session_config}))

    @staticmethod
    def _map_handshake_error(e: InvalidStatus) -> Exception:
        status = e.response.status_code
        if status in (401, 403):
            return InvalidRequestError("OpenAI Realtime authentication failed")
        if status == 429:
            return RateLimitError("OpenAI Realtime rate limit exceeded")
        return ServiceUnavailableError(f"OpenAI Realtime handshake failed: {status}")
