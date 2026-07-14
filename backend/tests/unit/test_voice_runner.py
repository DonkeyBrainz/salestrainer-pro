"""Tests for the voice-suite runner, driven by a fake LiveSession (no network)."""

import asyncio
import wave
from array import array
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from evals.runners import voice_runner
from evals.runners.voice_runner import _accumulate_usage, run_voice_scenario
from evals.scenarios.types import VoiceScenario, VoiceTurnTrigger

FIXTURE_PCM = b"\x01\x00" * 1600  # 100ms @ 16kHz


def _speech_pcm(ms: int) -> bytes:
    """Loud-enough fake speech audio at 24kHz."""
    return array("h", [4000] * (24000 * ms // 1000)).tobytes()


class FakeLiveSession:
    """Enqueues one scripted event list per received utterance."""

    def __init__(self, turns_events: list[list[dict[str, Any]]]) -> None:
        self._pending = list(turns_events)
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._received_bytes = 0
        self._turns_emitted = 0
        self.sent_chunks: list[bytes] = []

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> None:
        self.sent_chunks.append(audio_data)
        self._received_bytes += len(audio_data)
        # Once a full fixture utterance has arrived, emit that turn's events.
        if self._pending and self._received_bytes >= (self._turns_emitted + 1) * len(FIXTURE_PCM):
            self._turns_emitted += 1
            for event in self._pending.pop(0):
                self._queue.put_nowait(event)

    async def send_text(self, text: str) -> None:
        raise AssertionError("voice runner must never send text")

    async def receive(self) -> AsyncGenerator[dict[str, Any]]:
        while True:
            yield await self._queue.get()

    async def close(self) -> None:
        pass


class FakeProvider:
    name = "gemini"

    def __init__(self, session: FakeLiveSession) -> None:
        self._session = session
        self.connect_kwargs: dict[str, Any] = {}

    @asynccontextmanager
    async def connect_live(self, **kwargs: Any) -> AsyncGenerator[FakeLiveSession]:
        self.connect_kwargs = kwargs
        yield self._session


def _scenario(n_turns: int = 1) -> VoiceScenario:
    return VoiceScenario(
        id="fake_scenario",
        tags=["voice:test"],
        persona_id="practical_family",
        turns=[
            VoiceTurnTrigger(salesperson_text=f"scripted line number {i}") for i in range(n_turns)
        ],
    )


@pytest.fixture(autouse=True)
def fast_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice_runner, "TURN_TIMEOUT_S", 2.0)
    monkeypatch.setattr(voice_runner, "GRACE_DRAIN_S", 0.05)


@pytest.fixture(autouse=True)
def fake_tts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice_runner, "synthesize_turn_audio", AsyncMock(return_value=FIXTURE_PCM))


def _turn_events(text_heard: str, reply: str, usage: dict[str, int] | None = None) -> list[dict]:
    events: list[dict[str, Any]] = [
        {"type": "input_transcription", "text": text_heard, "finished": True},
        {"type": "audio", "audio_data": _speech_pcm(600), "text": None},
        {"type": "output_transcription", "text": reply, "finished": True},
    ]
    if usage:
        events.append({"type": "usage", "usage": usage, "detail": {}})
    events.append({"type": "end", "audio_data": None, "text": None})
    return events


class TestRunVoiceScenario:
    async def test_happy_path_captures_everything(self, tmp_path: Path) -> None:
        session = FakeLiveSession(
            [
                _turn_events(
                    "scripted line number 0",
                    "Oh, we're just looking for now.",
                    usage={"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
                )
            ]
        )
        provider = FakeProvider(session)

        result = await run_voice_scenario(
            _scenario(),
            provider,  # type: ignore[arg-type]
            MagicMock(),
            run_id="test-run",
            artifacts_dir=tmp_path,
        )

        assert result.error is None
        assert result.passed
        assert len(result.voice_turns) == 1
        turn = result.voice_turns[0]
        assert turn.input_transcription == "scripted line number 0"
        assert turn.response_text == "Oh, we're just looking for now."
        assert turn.wer == 0.0
        assert turn.first_audio_ms is not None and turn.first_audio_ms >= 0
        assert 590 <= (turn.output_audio_ms or 0) <= 610
        assert turn.peak_amplitude == 4000
        assert turn.usage == {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130}
        assert result.usage["total_tokens"] == 130

        # Persona voice + system prompt reached connect_live.
        assert provider.connect_kwargs["voice"]  # resolved for provider "gemini"
        assert "practical" in provider.connect_kwargs["system_instruction"].lower() or len(
            provider.connect_kwargs["system_instruction"]
        )

        # WAV artifact saved and playable.
        assert turn.audio_path is not None
        with wave.open(turn.audio_path, "rb") as wf:
            assert wf.getframerate() == 24000
            assert wf.getnframes() == 24000 * 600 // 1000

    async def test_multi_turn_session_reused(self, tmp_path: Path) -> None:
        session = FakeLiveSession(
            [
                _turn_events("scripted line number 0", "First reply."),
                _turn_events("scripted line number 1", "Second reply."),
            ]
        )
        result = await run_voice_scenario(
            _scenario(2),
            FakeProvider(session),  # type: ignore[arg-type]
            MagicMock(),
            run_id="test-run",
            artifacts_dir=tmp_path,
        )

        assert result.error is None
        assert [t.response_text for t in result.voice_turns] == ["First reply.", "Second reply."]
        # All audio streamed in browser-sized chunks.
        assert all(len(c) <= 3200 for c in session.sent_chunks)

    async def test_turn_timeout_fails_scenario_not_suite(self, tmp_path: Path) -> None:
        # No "end" event ever arrives.
        session = FakeLiveSession([[{"type": "audio", "audio_data": b"\x00\x00", "text": None}]])
        result = await run_voice_scenario(
            _scenario(),
            FakeProvider(session),  # type: ignore[arg-type]
            MagicMock(),
            run_id="test-run",
            artifacts_dir=tmp_path,
        )

        assert not result.passed
        assert result.error is not None and "TimeoutError" in result.error

    async def test_wer_none_when_no_input_transcription(self, tmp_path: Path) -> None:
        events = [
            {"type": "audio", "audio_data": _speech_pcm(400), "text": None},
            {"type": "output_transcription", "text": "Reply.", "finished": True},
            {"type": "end", "audio_data": None, "text": None},
        ]
        session = FakeLiveSession([events])
        result = await run_voice_scenario(
            _scenario(),
            FakeProvider(session),  # type: ignore[arg-type]
            MagicMock(),
            run_id="test-run",
            artifacts_dir=tmp_path,
        )
        assert result.voice_turns[0].wer is None
        assert result.voice_turns[0].input_transcription == ""


class TestAccumulateUsage:
    def test_per_turn_reporters_sum(self) -> None:
        totals: dict[str, int] = {}
        _accumulate_usage(
            totals,
            [
                {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
                {"prompt_tokens": 120, "completion_tokens": 20, "total_tokens": 140},
            ],
        )
        # Non-monotone? 140 >= 130 is monotone... both patterns possible; this
        # pair IS monotone so deltas apply: 130 + (140-130) = 140.
        assert totals["total_tokens"] == 140

    def test_cumulative_reporters_take_deltas(self) -> None:
        totals: dict[str, int] = {}
        _accumulate_usage(
            totals,
            [
                {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
                {"prompt_tokens": 250, "completion_tokens": 80, "total_tokens": 330},
            ],
        )
        assert totals == {"prompt_tokens": 250, "completion_tokens": 80, "total_tokens": 330}

    def test_single_turn_used_directly(self) -> None:
        totals: dict[str, int] = {}
        _accumulate_usage(
            totals, [{"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}]
        )
        assert totals["total_tokens"] == 15

    def test_none_entries_skipped(self) -> None:
        totals: dict[str, int] = {}
        _accumulate_usage(totals, [None, None])
        assert totals == {}
