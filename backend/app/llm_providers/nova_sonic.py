"""Amazon Nova Sonic implementation of the LLMStreamProvider interface.

Drives a Nova Sonic bidirectional stream over Bedrock and translates its
event-scripted JSON protocol into the shared ``LiveEvent`` vocabulary. Browser
audio is 16 kHz PCM16 (Nova's input rate) so no resampling is needed; output is
24 kHz PCM16 (browser playback rate).

The Smithy-generated ``aws_sdk_bedrock_runtime`` client is experimental and is
imported lazily inside :meth:`NovaSonicProvider.connect_live`, so this module
imports cleanly without the optional ``nova`` extra installed. Verify the model
id, event field names, and voice IDs against current AWS docs when enabling.
"""

import base64
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from app.config import Settings
from app.core.exceptions import (
    InternalError,
    InvalidRequestError,
    ServiceUnavailableError,
)
from app.llm_providers.streaming import LiveEvent, LiveSession

logger = logging.getLogger(__name__)

_INPUT_SAMPLE_RATE = 16000
_OUTPUT_SAMPLE_RATE = 24000


def build_setup_events(
    *,
    prompt_name: str,
    text_content_name: str,
    audio_content_name: str,
    voice: str,
    system_instruction: str | None,
    temperature: float,
) -> list[dict[str, Any]]:
    """Build the ordered setup event sequence for a Nova Sonic session.

    Pure function (no I/O) so the protocol scripting is unit-testable without
    the Bedrock SDK. Returns the ``event`` bodies to send, in order:
    sessionStart -> promptStart(voiceId) -> system text block -> audio open.
    """
    events: list[dict[str, Any]] = [
        {
            "sessionStart": {
                "inferenceConfiguration": {
                    "maxTokens": 1024,
                    "topP": 0.95,
                    "temperature": temperature,
                }
            }
        },
        {
            "promptStart": {
                "promptName": prompt_name,
                "textOutputConfiguration": {"mediaType": "text/plain"},
                "audioOutputConfiguration": {
                    "mediaType": "audio/lpcm",
                    "sampleRateHertz": _OUTPUT_SAMPLE_RATE,
                    "sampleSizeBits": 16,
                    "channelCount": 1,
                    "voiceId": voice,
                    "encoding": "base64",
                    "audioType": "SPEECH",
                },
            }
        },
    ]

    if system_instruction:
        events.extend(
            [
                {
                    "contentStart": {
                        "promptName": prompt_name,
                        "contentName": text_content_name,
                        "type": "TEXT",
                        "interactive": False,
                        "role": "SYSTEM",
                        "textInputConfiguration": {"mediaType": "text/plain"},
                    }
                },
                {
                    "textInput": {
                        "promptName": prompt_name,
                        "contentName": text_content_name,
                        "content": system_instruction,
                    }
                },
                {
                    "contentEnd": {
                        "promptName": prompt_name,
                        "contentName": text_content_name,
                    }
                },
            ]
        )

    events.append(
        {
            "contentStart": {
                "promptName": prompt_name,
                "contentName": audio_content_name,
                "type": "AUDIO",
                "interactive": True,
                "role": "USER",
                "audioInputConfiguration": {
                    "mediaType": "audio/lpcm",
                    "sampleRateHertz": _INPUT_SAMPLE_RATE,
                    "sampleSizeBits": 16,
                    "channelCount": 1,
                    "audioType": "SPEECH",
                    "encoding": "base64",
                },
            }
        }
    )
    return events


class NovaSonicSession:
    """A single Nova Sonic bidirectional stream session.

    ``chunk_cls`` / ``payload_cls`` are the Smithy input-chunk wrapper classes,
    injected by the provider so this class needs no direct SDK import (and is
    fully mockable in tests).
    """

    def __init__(
        self,
        stream: Any,
        *,
        chunk_cls: Any,
        payload_cls: Any,
        prompt_name: str,
        audio_content_name: str,
    ) -> None:
        self._stream = stream
        self._chunk_cls = chunk_cls
        self._payload_cls = payload_cls
        self._prompt_name = prompt_name
        self._audio_content_name = audio_content_name
        self._closed = False

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> None:
        """Send a 16 kHz PCM16 audio chunk as a base64 audioInput event."""
        if self._closed:
            raise InternalError("Cannot send to closed Nova Sonic session")
        content = base64.b64encode(audio_data).decode("ascii")
        await self._send_event(
            {
                "audioInput": {
                    "promptName": self._prompt_name,
                    "contentName": self._audio_content_name,
                    "content": content,
                }
            }
        )

    async def send_text(self, text: str) -> None:
        """Mid-session text injection is not supported by this adapter."""
        raise InvalidRequestError("Nova Sonic adapter does not support mid-session text input")

    async def receive(self) -> AsyncGenerator[LiveEvent]:
        """Yield translated LiveEvents until the stream ends."""
        if self._closed:
            raise InternalError("Cannot receive from closed Nova Sonic session")
        try:
            while not self._closed:
                output = await self._stream.await_output()
                result = await output[1].receive()
                if not (result.value and result.value.bytes_):
                    continue
                data = json.loads(result.value.bytes_.decode("utf-8"))
                event = data.get("event")
                if not event:
                    continue
                translated = self._translate(event)
                if translated is not None:
                    yield translated
                    if translated["type"] == "end":
                        # Turn boundary — keep looping for the next turn.
                        continue
        except StopAsyncIteration:
            return
        except (InvalidRequestError, InternalError, ServiceUnavailableError):
            raise
        except Exception as e:  # noqa: BLE001 - surface transport errors as retryable
            raise ServiceUnavailableError(f"Nova Sonic stream error: {e}") from e

    def _translate(self, event: dict[str, Any]) -> LiveEvent | None:
        """Map one Nova Sonic event to a LiveEvent (or None to ignore)."""
        if "audioOutput" in event:
            content = event["audioOutput"].get("content", "")
            return {"type": "audio", "audio_data": base64.b64decode(content), "text": None}

        if "textOutput" in event:
            text_out = event["textOutput"]
            role = str(text_out.get("role", "")).upper()
            text = text_out.get("content", "")
            if role == "USER":
                return {
                    "type": "input_transcription",
                    "audio_data": None,
                    "text": text,
                    "finished": True,
                }
            return {
                "type": "output_transcription",
                "audio_data": None,
                "text": text,
                "finished": True,
            }

        if "contentEnd" in event:
            stop_reason = str(event["contentEnd"].get("stopReason", "")).upper()
            if stop_reason in ("END_TURN", "INTERRUPTED"):
                return {"type": "end", "audio_data": None, "text": None}
            return None

        if "completionEnd" in event:
            return {"type": "end", "audio_data": None, "text": None}

        if "usageEvent" in event:
            usage = event["usageEvent"]
            prompt_tokens = int(usage.get("totalInputTokens") or 0)
            completion_tokens = int(usage.get("totalOutputTokens") or 0)
            total_tokens = int(usage.get("totalTokens") or (prompt_tokens + completion_tokens))
            if not total_tokens:
                return None
            detail = usage.get("details") or {}
            return {
                "type": "usage",
                "audio_data": None,
                "text": None,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                },
                # speechTokens/textTokens breakdown, cumulative + delta.
                "detail": detail,
            }

        # contentStart, toolUse, completionStart, etc. — not needed by the relay.
        logger.debug("Ignoring Nova Sonic event: %s", next(iter(event), "?"))
        return None

    async def _send_event(self, event: dict[str, Any]) -> None:
        body = json.dumps({"event": event}).encode("utf-8")
        chunk = self._chunk_cls(value=self._payload_cls(bytes_=body))
        await self._stream.input_stream.send(chunk)

    async def close(self) -> None:
        """Close the audio content, prompt, and session. Idempotent."""
        if self._closed:
            return
        self._closed = True
        try:
            await self._send_event(
                {
                    "contentEnd": {
                        "promptName": self._prompt_name,
                        "contentName": self._audio_content_name,
                    }
                }
            )
            await self._send_event({"promptEnd": {"promptName": self._prompt_name}})
            await self._send_event({"sessionEnd": {}})
            await self._stream.input_stream.close()
        except Exception as e:  # noqa: BLE001 - best-effort shutdown
            logger.debug("Nova Sonic close encountered an error: %s", e)


class NovaSonicProvider:
    """LLMStreamProvider backed by Amazon Nova Sonic (Bedrock)."""

    name = "nova"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @asynccontextmanager
    async def connect_live(
        self,
        *,
        system_instruction: str | None = None,
        voice: str | None = None,
        resumption_handle: str | None = None,  # unused: Nova has no resumption
    ) -> AsyncGenerator[LiveSession]:
        """Open a Nova Sonic bidirectional stream and script the session setup."""
        import uuid

        try:
            from aws_sdk_bedrock_runtime.client import (
                BedrockRuntimeClient,
                InvokeModelWithBidirectionalStreamOperationInput,
            )
            from aws_sdk_bedrock_runtime.config import Config
            from aws_sdk_bedrock_runtime.models import (
                BidirectionalInputPayloadPart,
                InvokeModelWithBidirectionalStreamInputChunk,
            )
            from smithy_aws_core.identity import EnvironmentCredentialsResolver
        except ImportError as e:  # pragma: no cover - requires the optional extra
            raise InvalidRequestError(
                "Nova Sonic support requires the 'nova' extra (uv sync --extra nova)"
            ) from e

        # Load credentials from boto3's full chain (~/.aws, IAM role) into the
        # environment — the Smithy resolver below only reads env vars.
        from app.llm_providers.aws_credentials import bootstrap_aws_env_credentials

        bootstrap_aws_env_credentials()

        region = self._settings.aws_region
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{region}.amazonaws.com",
            region=region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        client = BedrockRuntimeClient(config=config)

        try:
            stream = await client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(
                    model_id=self._settings.nova_sonic_model
                )
            )
        except Exception as e:  # noqa: BLE001 - map connection failures to retryable
            raise ServiceUnavailableError(f"Could not open Nova Sonic stream: {e}") from e

        prompt_name = f"prompt_{uuid.uuid4().hex[:12]}"
        audio_content_name = f"audio_{uuid.uuid4().hex[:12]}"
        text_content_name = f"text_{uuid.uuid4().hex[:12]}"

        session = NovaSonicSession(
            stream,
            chunk_cls=InvokeModelWithBidirectionalStreamInputChunk,
            payload_cls=BidirectionalInputPayloadPart,
            prompt_name=prompt_name,
            audio_content_name=audio_content_name,
        )

        setup_events = build_setup_events(
            prompt_name=prompt_name,
            text_content_name=text_content_name,
            audio_content_name=audio_content_name,
            voice=voice or "matthew",
            system_instruction=system_instruction,
            temperature=self._settings.nova_sonic_temperature,
        )
        try:
            for event in setup_events:
                await session._send_event(event)
            yield session
        finally:
            await session.close()
