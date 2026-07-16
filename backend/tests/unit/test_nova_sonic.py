"""Tests for the Amazon Nova Sonic speech-to-speech adapter."""

import base64
import json
from collections import namedtuple
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import InternalError, InvalidRequestError
from app.llm_providers.nova_sonic import (
    NovaSonicProvider,
    NovaSonicSession,
    build_setup_events,
)
from app.llm_providers.streaming import LiveSession, LLMStreamProvider

# Fake Smithy chunk wrappers that record the JSON bytes sent.
FakePayload = namedtuple("FakePayload", ["bytes_"])
FakeChunk = namedtuple("FakeChunk", ["value"])


def _session_with_stream() -> tuple[NovaSonicSession, MagicMock]:
    stream = MagicMock()
    stream.input_stream = AsyncMock()
    session = NovaSonicSession(
        stream,
        chunk_cls=FakeChunk,
        payload_cls=FakePayload,
        prompt_name="prompt_1",
        audio_content_name="audio_1",
    )
    return session, stream


def _sent_events(stream: MagicMock) -> list[dict]:
    events = []
    for call in stream.input_stream.send.await_args_list:
        chunk = call.args[0]
        events.append(json.loads(chunk.value.bytes_.decode())["event"])
    return events


class TestConformance:
    def test_provider_satisfies_protocol(self) -> None:
        provider = NovaSonicProvider(MagicMock())
        assert isinstance(provider, LLMStreamProvider)
        assert provider.name == "nova"

    def test_session_satisfies_protocol(self) -> None:
        assert issubclass(NovaSonicSession, LiveSession)


class TestSetupEvents:
    def test_order_and_voice(self) -> None:
        events = build_setup_events(
            prompt_name="p1",
            text_content_name="t1",
            audio_content_name="a1",
            voice="matthew",
            system_instruction="be a buyer",
            temperature=0.7,
        )
        keys = [next(iter(e)) for e in events]
        assert keys == [
            "sessionStart",
            "promptStart",
            "contentStart",  # system text open
            "textInput",
            "contentEnd",  # system text close
            "contentStart",  # audio open
        ]
        assert events[1]["promptStart"]["audioOutputConfiguration"]["voiceId"] == "matthew"
        assert events[3]["textInput"]["content"] == "be a buyer"
        assert events[1]["promptStart"]["audioOutputConfiguration"]["sampleRateHertz"] == 24000

    def test_no_system_instruction_skips_text_block(self) -> None:
        events = build_setup_events(
            prompt_name="p1",
            text_content_name="t1",
            audio_content_name="a1",
            voice="tiffany",
            system_instruction=None,
            temperature=0.7,
        )
        keys = [next(iter(e)) for e in events]
        assert keys == ["sessionStart", "promptStart", "contentStart"]


class TestSendAudio:
    async def test_base64_audio_input_event(self) -> None:
        session, stream = _session_with_stream()
        await session.send_audio(b"\x01\x02\x03\x04")

        events = _sent_events(stream)
        assert len(events) == 1
        audio_in = events[0]["audioInput"]
        assert audio_in["promptName"] == "prompt_1"
        assert audio_in["contentName"] == "audio_1"
        assert base64.b64decode(audio_in["content"]) == b"\x01\x02\x03\x04"

    async def test_send_after_close_raises(self) -> None:
        session, _ = _session_with_stream()
        await session.close()
        with pytest.raises(InternalError):
            await session.send_audio(b"\x00\x00")

    async def test_send_text_unsupported(self) -> None:
        session, _ = _session_with_stream()
        with pytest.raises(InvalidRequestError):
            await session.send_text("hello")


class TestReceiveTranslation:
    def _stream_yielding(self, events: list[dict]) -> MagicMock:
        stream = MagicMock()
        queue = list(events)

        async def await_output():
            if not queue:
                raise StopAsyncIteration
            evt = queue.pop(0)
            reader = MagicMock()
            result = MagicMock()
            result.value.bytes_ = json.dumps({"event": evt}).encode()
            reader.receive = AsyncMock(return_value=result)
            return (None, reader)

        stream.await_output = AsyncMock(side_effect=await_output)
        return stream

    async def _run(self, events: list[dict]) -> list[dict]:
        stream = self._stream_yielding(events)
        session = NovaSonicSession(
            stream,
            chunk_cls=FakeChunk,
            payload_cls=FakePayload,
            prompt_name="p",
            audio_content_name="a",
        )
        return [ev async for ev in session.receive()]

    async def test_audio_output(self) -> None:
        pcm = b"\x10\x20\x30\x40"
        out = await self._run([{"audioOutput": {"content": base64.b64encode(pcm).decode()}}])
        assert out == [{"type": "audio", "audio_data": pcm, "text": None}]

    async def test_user_text_is_input_transcription(self) -> None:
        out = await self._run([{"textOutput": {"role": "USER", "content": "how much?"}}])
        assert out == [
            {
                "type": "input_transcription",
                "audio_data": None,
                "text": "how much?",
                "finished": True,
            }
        ]

    async def test_assistant_text_is_output_transcription(self) -> None:
        out = await self._run([{"textOutput": {"role": "ASSISTANT", "content": "It's $450k."}}])
        assert out[0]["type"] == "output_transcription"
        assert out[0]["text"] == "It's $450k."

    async def test_strips_interrupted_marker_from_text(self) -> None:
        out = await self._run(
            [
                {
                    "textOutput": {
                        "role": "ASSISTANT",
                        "content": '{ "interrupted" : true }Hi, thanks for having me.',
                    }
                }
            ]
        )
        assert out[0]["type"] == "output_transcription"
        assert out[0]["text"] == "Hi, thanks for having me."
        assert "interrupted" not in out[0]["text"]

    async def test_drops_text_that_is_only_the_interrupted_marker(self) -> None:
        out = await self._run(
            [{"textOutput": {"role": "ASSISTANT", "content": '{ "interrupted" : true }'}}]
        )
        assert out == []

    async def test_drops_non_speculative_assistant_text(self) -> None:
        speculative_start = {
            "contentStart": {"additionalModelFields": json.dumps({"generationStage": "FINAL"})}
        }
        out = await self._run(
            [speculative_start, {"textOutput": {"role": "ASSISTANT", "content": "duplicate text"}}]
        )
        assert out == []

    async def test_keeps_speculative_assistant_text(self) -> None:
        speculative_start = {
            "contentStart": {
                "additionalModelFields": json.dumps({"generationStage": "SPECULATIVE"})
            }
        }
        out = await self._run(
            [speculative_start, {"textOutput": {"role": "ASSISTANT", "content": "real text"}}]
        )
        assert len(out) == 1
        assert out[0]["text"] == "real text"

    async def test_user_text_ignores_speculative_stage(self) -> None:
        final_start = {
            "contentStart": {"additionalModelFields": json.dumps({"generationStage": "FINAL"})}
        }
        out = await self._run(
            [final_start, {"textOutput": {"role": "USER", "content": "how much?"}}]
        )
        assert len(out) == 1
        assert out[0]["type"] == "input_transcription"

    async def test_content_end_turn_is_end(self) -> None:
        out = await self._run([{"contentEnd": {"stopReason": "END_TURN"}}])
        assert out == [{"type": "end", "audio_data": None, "text": None}]

    async def test_unknown_events_ignored(self) -> None:
        out = await self._run([{"contentStart": {}}, {"toolUse": {}}])
        assert out == []

    async def test_usage_event_translated(self) -> None:
        detail = {
            "total": {
                "input": {"speechTokens": 80, "textTokens": 20},
                "output": {"speechTokens": 25, "textTokens": 5},
            }
        }
        out = await self._run(
            [
                {
                    "usageEvent": {
                        "totalInputTokens": 100,
                        "totalOutputTokens": 30,
                        "totalTokens": 130,
                        "details": detail,
                    }
                }
            ]
        )
        assert len(out) == 1
        assert out[0]["type"] == "usage"
        assert out[0]["usage"] == {
            "prompt_tokens": 100,
            "completion_tokens": 30,
            "total_tokens": 130,
        }
        assert out[0]["detail"] == detail

    async def test_empty_usage_event_ignored(self) -> None:
        out = await self._run([{"usageEvent": {"totalTokens": 0}}])
        assert out == []


class TestClose:
    async def test_close_sends_teardown_sequence(self) -> None:
        session, stream = _session_with_stream()
        await session.close()

        keys = [next(iter(e)) for e in _sent_events(stream)]
        assert keys == ["contentEnd", "promptEnd", "sessionEnd"]
        stream.input_stream.close.assert_awaited_once()

    async def test_close_is_idempotent(self) -> None:
        session, stream = _session_with_stream()
        await session.close()
        await session.close()  # second call must not send again
        assert stream.input_stream.close.await_count == 1


class TestConnectLiveWithoutSDK:
    async def test_missing_sdk_raises_invalid_request(self) -> None:
        # The optional 'nova' extra is not installed in the test env, so the
        # lazy import inside connect_live must surface a clear error.
        provider = NovaSonicProvider(MagicMock())
        with pytest.raises(InvalidRequestError, match="nova"):
            async with provider.connect_live(system_instruction="hi", voice="matthew"):
                pass
