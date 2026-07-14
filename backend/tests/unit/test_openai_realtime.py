"""Tests for the OpenAI Realtime speech-to-speech adapter."""

import base64
import json
from array import array
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import (
    InternalError,
    InvalidRequestError,
    RateLimitError,
)
from app.llm_providers.openai_realtime import OpenAIRealtimeProvider, OpenAIRealtimeSession
from app.llm_providers.streaming import LiveSession, LLMStreamProvider


@pytest.fixture
def settings() -> MagicMock:
    s = MagicMock()
    s.openai_api_key = "sk-test"
    s.openai_realtime_model = "gpt-realtime"
    s.openai_realtime_temperature = 0.8
    return s


def _pcm16k(n: int) -> bytes:
    return array("h", list(range(n))).tobytes()


class TestConformance:
    def test_provider_satisfies_protocol(self, settings: MagicMock) -> None:
        assert isinstance(OpenAIRealtimeProvider(settings), LLMStreamProvider)
        assert OpenAIRealtimeProvider(settings).name == "openai"

    def test_session_satisfies_protocol(self) -> None:
        assert issubclass(OpenAIRealtimeSession, LiveSession)


class TestSendAudio:
    async def test_resamples_and_base64_appends(self) -> None:
        ws = AsyncMock()
        session = OpenAIRealtimeSession(ws)

        await session.send_audio(_pcm16k(100))

        ws.send.assert_awaited_once()
        sent = json.loads(ws.send.await_args.args[0])
        assert sent["type"] == "input_audio_buffer.append"
        # Payload decodes to int16 PCM ~1.5x longer (16k->24k upsample).
        decoded = base64.b64decode(sent["audio"])
        out = array("h")
        out.frombytes(decoded)
        assert 140 <= len(out) <= 152

    async def test_send_after_close_raises(self) -> None:
        session = OpenAIRealtimeSession(AsyncMock())
        await session.close()
        with pytest.raises(InternalError):
            await session.send_audio(_pcm16k(10))


class TestSendText:
    async def test_creates_item_and_response(self) -> None:
        ws = AsyncMock()
        session = OpenAIRealtimeSession(ws)

        await session.send_text("hello")

        types_sent = [json.loads(c.args[0])["type"] for c in ws.send.await_args_list]
        assert types_sent == ["conversation.item.create", "response.create"]


class TestReceiveTranslation:
    async def _run(self, server_events: list[dict]) -> list[dict]:
        ws = MagicMock()

        async def _aiter():
            for e in server_events:
                yield json.dumps(e)

        ws.__aiter__ = lambda self=ws: _aiter()
        session = OpenAIRealtimeSession(ws)
        return [ev async for ev in session.receive()]

    async def test_audio_delta_to_audio_event(self) -> None:
        pcm = b"\x01\x02\x03\x04"
        events = await self._run(
            [{"type": "response.output_audio.delta", "delta": base64.b64encode(pcm).decode()}]
        )
        assert events == [{"type": "audio", "audio_data": pcm, "text": None}]

    async def test_beta_audio_delta_name_also_supported(self) -> None:
        pcm = b"\x00\x10"
        events = await self._run(
            [{"type": "response.audio.delta", "delta": base64.b64encode(pcm).decode()}]
        )
        assert events[0]["type"] == "audio"
        assert events[0]["audio_data"] == pcm

    async def test_output_transcript_delta(self) -> None:
        events = await self._run(
            [{"type": "response.output_audio_transcript.delta", "delta": "hel"}]
        )
        assert events == [
            {"type": "output_transcription", "audio_data": None, "text": "hel", "finished": False}
        ]

    async def test_input_transcription_completed(self) -> None:
        events = await self._run(
            [
                {
                    "type": "conversation.item.input_audio_transcription.completed",
                    "transcript": "what's the price?",
                }
            ]
        )
        assert events == [
            {
                "type": "input_transcription",
                "audio_data": None,
                "text": "what's the price?",
                "finished": True,
            }
        ]

    async def test_response_done_to_end(self) -> None:
        events = await self._run([{"type": "response.done"}])
        assert events == [{"type": "end", "audio_data": None, "text": None}]

    async def test_response_done_with_usage_yields_usage_then_end(self) -> None:
        events = await self._run(
            [
                {
                    "type": "response.done",
                    "response": {
                        "usage": {
                            "total_tokens": 130,
                            "input_tokens": 100,
                            "output_tokens": 30,
                            "input_token_details": {"audio_tokens": 90, "text_tokens": 10},
                            "output_token_details": {"audio_tokens": 25, "text_tokens": 5},
                        }
                    },
                }
            ]
        )
        assert [e["type"] for e in events] == ["usage", "end"]
        assert events[0]["usage"] == {
            "prompt_tokens": 100,
            "completion_tokens": 30,
            "total_tokens": 130,
        }
        assert events[0]["detail"]["input_token_details"]["audio_tokens"] == 90

    async def test_response_done_without_usage_yields_only_end(self) -> None:
        events = await self._run([{"type": "response.done", "response": {}}])
        assert [e["type"] for e in events] == ["end"]

    async def test_unknown_events_ignored(self) -> None:
        events = await self._run(
            [{"type": "session.created"}, {"type": "input_audio_buffer.speech_started"}]
        )
        assert events == []

    async def test_error_event_maps_rate_limit(self) -> None:
        ws = MagicMock()

        async def _aiter():
            yield json.dumps({"type": "error", "error": {"code": "rate_limit_exceeded"}})

        ws.__aiter__ = lambda self=ws: _aiter()
        session = OpenAIRealtimeSession(ws)
        with pytest.raises(RateLimitError):
            [ev async for ev in session.receive()]


class TestConnectLive:
    async def test_missing_api_key_raises(self) -> None:
        settings = MagicMock()
        settings.openai_api_key = ""
        provider = OpenAIRealtimeProvider(settings)
        with pytest.raises(InvalidRequestError):
            async with provider.connect_live(system_instruction="hi", voice="cedar"):
                pass

    async def test_sends_session_update_on_connect(
        self, settings: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ws = AsyncMock()

        async def fake_connect(url: str, additional_headers: dict) -> AsyncMock:
            assert "gpt-realtime" in url
            assert additional_headers["Authorization"] == "Bearer sk-test"
            return ws

        monkeypatch.setattr("app.llm_providers.openai_realtime.websockets.connect", fake_connect)

        provider = OpenAIRealtimeProvider(settings)
        async with provider.connect_live(system_instruction="be a buyer", voice="cedar"):
            pass

        update = json.loads(ws.send.await_args_list[0].args[0])
        assert update["type"] == "session.update"
        assert update["session"]["instructions"] == "be a buyer"
        assert update["session"]["voice"] == "cedar"
        assert update["session"]["input_audio_format"] == "pcm16"
        assert update["session"]["turn_detection"] == {"type": "server_vad"}
        ws.close.assert_awaited()  # closed on context exit
