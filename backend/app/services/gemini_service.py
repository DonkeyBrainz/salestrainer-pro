"""Gemini service for AI text generation and real-time audio streaming."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from google import genai
from google.genai import errors, types
from google.genai.live import AsyncSession
from google.genai.types import (
    Modality,
    SessionResumptionConfig,
)

from app.config import Settings
from app.core.exceptions import (
    InternalError,
    InvalidRequestError,
    RateLimitError,
    ServiceUnavailableError,
)
from app.models.gemini import (
    GeminiRequest,
    GeminiResponse,
    GeminiStreamChunk,
    ModelInfo,
    UsageMetadata,
)


class GeminiService:
    """Service for interacting with Google Gemini API."""

    def __init__(self, settings: Settings) -> None:
        """Initialize Gemini service.

        Args:
            settings: Application settings with Gemini configuration
        """
        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def generate(self, request: GeminiRequest) -> GeminiResponse:
        """Generate text using Gemini model.

        Args:
            request: Generation request with prompt and optional parameters

        Returns:
            GeminiResponse with generated text and metadata

        Raises:
            InvalidRequestError: If request is malformed or model rejects it
            RateLimitError: If rate limit is exceeded
            ServiceUnavailableError: If Gemini service is unavailable
            InternalError: For unexpected errors
        """
        # Use request overrides or fall back to settings defaults
        temperature = (
            request.temperature
            if request.temperature is not None
            else self.settings.gemini_temperature
        )
        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else self.settings.gemini_max_tokens
        )

        try:
            # Generate content with configuration
            response = self.client.models.generate_content(
                model=self.settings.gemini_model,
                contents=request.prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )

            # Extract text from response
            if not response.text:
                raise InternalError("Gemini returned empty response")

            # Extract usage metadata
            usage_metadata = response.usage_metadata
            if not usage_metadata:
                # Fallback if usage metadata is missing
                prompt_tokens = 0
                response_tokens = 0
                total_tokens = 0
            else:
                prompt_tokens = usage_metadata.prompt_token_count or 0
                # Note: response_token_count is the correct field in the SDK
                response_tokens = getattr(usage_metadata, "response_token_count", 0) or 0
                total_tokens = usage_metadata.total_token_count or 0

            return GeminiResponse(
                text=response.text,
                usage=UsageMetadata(
                    prompt_token_count=prompt_tokens,
                    candidates_token_count=response_tokens,
                    total_token_count=total_tokens,
                ),
                model_info=ModelInfo(
                    model=self.settings.gemini_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
            )

        except errors.APIError as e:
            # Map Gemini API errors to our exceptions
            if e.code == 429:
                raise RateLimitError("Gemini API rate limit exceeded") from e
            elif e.code == 400:
                raise InvalidRequestError(f"Invalid request to Gemini: {e.message}") from e
            elif e.code == 403:
                raise InvalidRequestError("Permission denied for Gemini API") from e
            elif e.code == 404:
                raise InvalidRequestError(f"Model not found: {self.settings.gemini_model}") from e
            elif e.code in (500, 502, 503, 504):
                raise ServiceUnavailableError("Gemini service temporarily unavailable") from e
            else:
                raise InternalError(f"Gemini API error: {e.message}") from e
        except Exception as e:
            # Catch any other unexpected errors
            raise InternalError(f"Unexpected error calling Gemini: {str(e)}") from e

    async def generate_stream(self, request: GeminiRequest) -> AsyncGenerator[GeminiStreamChunk]:
        """Generate text using Gemini model with streaming.

        Args:
            request: Generation request with prompt and optional parameters

        Yields:
            GeminiStreamChunk with incremental text content

        Raises:
            InvalidRequestError: If request is malformed or model rejects it
            RateLimitError: If rate limit is exceeded
            ServiceUnavailableError: If Gemini service is unavailable
            InternalError: For unexpected errors
        """
        # Use request overrides or fall back to settings defaults
        temperature = (
            request.temperature
            if request.temperature is not None
            else self.settings.gemini_temperature
        )
        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else self.settings.gemini_max_tokens
        )

        try:
            # Stream content with configuration
            chunks_yielded = False
            stream = self.client.aio.models.generate_content_stream(
                model=self.settings.gemini_model,
                contents=request.prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )

            async for chunk in stream:  # type: ignore[attr-defined]
                if chunk.text:
                    chunks_yielded = True
                    yield GeminiStreamChunk(text=chunk.text, is_final=False)

            # Yield final marker if we yielded any chunks
            if chunks_yielded:
                yield GeminiStreamChunk(text="", is_final=True)

        except errors.APIError as e:
            # Map Gemini API errors to our exceptions
            if e.code == 429:
                raise RateLimitError("Gemini API rate limit exceeded") from e
            elif e.code == 400:
                raise InvalidRequestError(f"Invalid request to Gemini: {e.message}") from e
            elif e.code == 403:
                raise InvalidRequestError("Permission denied for Gemini API") from e
            elif e.code == 404:
                raise InvalidRequestError(f"Model not found: {self.settings.gemini_model}") from e
            elif e.code in (500, 502, 503, 504):
                raise ServiceUnavailableError("Gemini service temporarily unavailable") from e
            else:
                raise InternalError(f"Gemini API error: {e.message}") from e
        except Exception as e:
            # Catch any other unexpected errors
            raise InternalError(f"Unexpected error calling Gemini: {str(e)}") from e

    @asynccontextmanager
    async def connect_live(
        self,
        model: str | None = None,
        system_instruction: str | None = None,
        voice_name: str | None = None,
        resumption_handle: str | None = None,
    ) -> AsyncGenerator["GeminiLiveSession"]:
        """Connect to Gemini Live API for real-time bidirectional streaming.

        Args:
            model: Optional model override (defaults to the configured gemini_live_model)
            system_instruction: Optional system instruction for the session
            voice_name: Optional Gemini voice identifier (e.g., 'leda', 'kore', 'puck', 'charon')
            resumption_handle: Optional handle from previous session for resumption

        Yields:
            GeminiLiveSession: Live session wrapper for bidirectional streaming

        Raises:
            InvalidRequestError: If connection parameters are invalid
            ServiceUnavailableError: If Gemini Live API is unavailable
            InternalError: For unexpected errors

        Example:
            async with gemini_service.connect_live(voice_name='leda') as session:
                await session.send_audio(audio_data)
                async for response in session.receive():
                    if response.audio_data:
                        # Process audio response
                        pass
        """
        live_model = model or self.settings.gemini_live_model

        # Build session resumption config
        session_resumption_cfg = SessionResumptionConfig(handle=resumption_handle)

        # Build speech config if voice_name is provided
        # Use dict-based config to avoid type issues
        speech_config = None
        if voice_name:
            speech_config = {"voice_config": {"prebuilt_voice_config": {"voice_name": voice_name}}}

        config = types.LiveConnectConfig(
            response_modalities=[Modality.AUDIO],
            speech_config=speech_config,  # type: ignore[arg-type]
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            session_resumption=session_resumption_cfg,
            system_instruction=system_instruction,
            temperature=self.settings.gemini_live_temperature,
        )

        try:
            async with self.client.aio.live.connect(
                model=live_model,
                config=config,
            ) as live_session:
                # Wrap the session for easier use
                yield GeminiLiveSession(live_session)

        except errors.APIError as e:
            # Map Gemini API errors to our exceptions
            if e.code == 429:
                raise RateLimitError("Gemini Live API rate limit exceeded") from e
            elif e.code == 400:
                raise InvalidRequestError(f"Invalid Live API request: {e.message}") from e
            elif e.code == 403:
                raise InvalidRequestError("Permission denied for Gemini Live API") from e
            elif e.code in (500, 502, 503, 504):
                raise ServiceUnavailableError("Gemini Live API temporarily unavailable") from e
            else:
                raise InternalError(f"Gemini Live API error: {e.message}") from e
        except Exception as e:
            raise InternalError(f"Unexpected error connecting to Gemini Live: {str(e)}") from e


class GeminiLiveSession:
    """Wrapper for Gemini Live API session with simplified interface."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize Live session wrapper.

        Args:
            session: The underlying AsyncSession from genai SDK
        """
        self._session = session
        self._closed = False

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> None:
        """Send audio data to Gemini.

        Args:
            audio_data: Raw audio bytes (PCM 16kHz mono recommended)
            mime_type: MIME type of audio data

        Raises:
            InternalError: If session is closed or send fails
        """
        if self._closed:
            raise InternalError("Cannot send to closed Live session")

        try:
            await self._session.send_realtime_input(
                audio={"data": audio_data, "mime_type": mime_type}
            )
        except Exception as e:
            raise InternalError(f"Failed to send audio to Gemini Live: {str(e)}") from e

    async def send_text(self, text: str) -> None:
        """Send text message to Gemini.

        Args:
            text: Text message to send

        Raises:
            InternalError: If session is closed or send fails
        """
        if self._closed:
            raise InternalError("Cannot send to closed Live session")

        try:
            await self._session.send_client_content(
                turns=[{"role": "user", "parts": [{"text": text}]}],
                turn_complete=True,
            )
        except Exception as e:
            raise InternalError(f"Failed to send text to Gemini Live: {str(e)}") from e

    async def receive(self) -> AsyncGenerator[dict[str, Any]]:
        """Receive responses from Gemini across multiple turns.

        Yields:
            dict with response data:
                - type (str): Response type
                    - "audio": Audio response from model
                    - "internal_reasoning": Model's internal text (not spoken)
                    - "input_transcription": User's speech transcribed
                    - "output_transcription": Model's speech transcribed
                    - "end": Turn complete
                - audio_data (bytes | None): Audio bytes if type="audio"
                - text (str | None): Text content for text-based types
                - finished (bool | None): Whether transcription is final

        Raises:
            InternalError: If receive fails
        """
        if self._closed:
            raise InternalError("Cannot receive from closed Live session")

        try:
            # Loop to handle multiple turns
            while not self._closed:
                # Get the turn generator
                turn = self._session.receive()

                # Iterate over responses in this turn
                async for response in turn:
                    # Check for session resumption update (before server_content)
                    if (
                        hasattr(response, "session_resumption_update")
                        and response.session_resumption_update
                    ):
                        update = response.session_resumption_update
                        yield {
                            "type": "session_resumption_update",
                            "new_handle": getattr(update, "new_handle", None),
                            "resumable": getattr(update, "resumable", False),
                        }

                    # Check for go_away (server requesting disconnect)
                    if hasattr(response, "go_away") and response.go_away:
                        yield {
                            "type": "go_away",
                            "time_left": getattr(response.go_away, "time_left", None),
                        }

                    # Surface token usage (billed audio/text tokens). Emitted
                    # under the vendor-agnostic usage keys so eval harnesses
                    # can do cost accounting; the relay ignores this type.
                    usage_event = self._extract_usage_event(response)
                    if usage_event is not None:
                        yield usage_event

                    server_content = response.server_content
                    if not server_content:
                        continue

                    # Barge-in: server-side VAD detected the user speaking over
                    # the model. Generation is already cancelled upstream; the
                    # client must flush any buffered/scheduled playback.
                    if getattr(server_content, "interrupted", False):
                        yield {
                            "type": "interrupted",
                            "audio_data": None,
                            "text": None,
                        }

                    # Check for input transcription (user's speech)
                    if hasattr(server_content, "input_transcription"):
                        input_trans = server_content.input_transcription
                        if input_trans and hasattr(input_trans, "text") and input_trans.text:
                            yield {
                                "type": "input_transcription",
                                "audio_data": None,
                                "text": input_trans.text,
                                "finished": getattr(input_trans, "finished", True),
                            }

                    # Check for output transcription (model's speech)
                    if hasattr(server_content, "output_transcription"):
                        output_trans = server_content.output_transcription
                        if output_trans and hasattr(output_trans, "text") and output_trans.text:
                            yield {
                                "type": "output_transcription",
                                "audio_data": None,
                                "text": output_trans.text,
                                "finished": getattr(output_trans, "finished", True),
                            }

                    # Handle model turn (audio + internal reasoning)
                    if server_content.model_turn:
                        model_turn = server_content.model_turn

                        # Extract parts from the turn
                        if model_turn.parts:
                            for part in model_turn.parts:
                                # Handle audio data
                                if part.inline_data and isinstance(part.inline_data.data, bytes):
                                    yield {
                                        "type": "audio",
                                        "audio_data": part.inline_data.data,
                                        "text": None,
                                    }

                                # Handle text data (internal reasoning, not spoken)
                                elif hasattr(part, "text") and part.text:
                                    yield {
                                        "type": "internal_reasoning",
                                        "audio_data": None,
                                        "text": part.text,
                                    }

                    # Check for turn end
                    if server_content.turn_complete:
                        yield {
                            "type": "end",
                            "audio_data": None,
                            "text": None,
                        }
                        # Break inner loop to get next turn
                        break

        except asyncio.CancelledError:
            # Allow graceful cancellation
            raise
        except Exception as e:
            raise InternalError(f"Failed to receive from Gemini Live: {str(e)}") from e

    @staticmethod
    def _extract_usage_event(response: Any) -> dict[str, Any] | None:
        """Map LiveServerMessage.usage_metadata to a "usage" LiveEvent (or None).

        Gemini reports cumulative token usage on some server messages; the
        per-modality breakdown (audio vs text) is preserved under "detail".
        Field values are coerced defensively (non-int -> 0) so SDK drift or
        partial payloads degrade to "no usage event" instead of crashing the
        receive loop.
        """

        def _as_int(value: Any) -> int:
            return value if isinstance(value, int) and not isinstance(value, bool) else 0

        usage_metadata = getattr(response, "usage_metadata", None)
        if usage_metadata is None:
            return None

        prompt_tokens = _as_int(getattr(usage_metadata, "prompt_token_count", 0))
        completion_tokens = _as_int(getattr(usage_metadata, "response_token_count", 0))
        total_tokens = _as_int(getattr(usage_metadata, "total_token_count", 0))
        if not (prompt_tokens or completion_tokens or total_tokens):
            return None

        detail: dict[str, Any] = {}
        for field in ("prompt_tokens_details", "response_tokens_details"):
            details = getattr(usage_metadata, field, None)
            if isinstance(details, list):
                detail[field] = [
                    {
                        "modality": str(getattr(d, "modality", "")),
                        "token_count": _as_int(getattr(d, "token_count", 0)),
                    }
                    for d in details
                ]
        thoughts = _as_int(getattr(usage_metadata, "thoughts_token_count", 0))
        if thoughts:
            detail["thoughts_token_count"] = thoughts

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

    async def close(self) -> None:
        """Close the Live session.

        Safe to call multiple times.
        """
        if not self._closed:
            self._closed = True
            # The underlying session is managed by the context manager
            # in GeminiService.connect_live(), so no explicit close needed
