"""Tests for the voice-eval TTS fixture synthesizer."""

import wave
from array import array
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from evals.audio import tts
from evals.audio.tts import (
    LIVE_INPUT_RATE,
    SILENCE_TAIL_MS,
    fixture_path,
    synthesize_turn_audio,
    write_wav,
)


def _fake_client(pcm_24k: bytes) -> MagicMock:
    """genai client whose generate_content returns inline audio bytes."""
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[SimpleNamespace(inline_data=SimpleNamespace(data=pcm_24k))]
                )
            )
        ]
    )
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=response)
    return client


@pytest.fixture
def fixtures_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(tts, "FIXTURES_DIR", tmp_path)
    return tmp_path


class TestSynthesize:
    async def test_synthesizes_resamples_and_pads_silence(self, fixtures_dir: Path) -> None:
        # 2400 samples @24k = 100ms -> ~1600 samples @16k + 16000 silence samples.
        pcm_24k = array("h", [1000] * 2400).tobytes()
        client = _fake_client(pcm_24k)

        audio = await synthesize_turn_audio("Hello there", settings=MagicMock(), client=client)

        samples = array("h")
        samples.frombytes(audio)
        silence_samples = LIVE_INPUT_RATE * SILENCE_TAIL_MS // 1000
        speech_samples = len(samples) - silence_samples
        assert 1590 <= speech_samples <= 1610
        # Tail is pure silence.
        assert all(s == 0 for s in samples[-silence_samples:])
        # Speech region survived the resample (constant signal stays constant).
        assert samples[10] == 1000

    async def test_caches_to_disk_and_skips_client_on_second_call(self, fixtures_dir: Path) -> None:
        pcm_24k = array("h", [500] * 240).tobytes()
        client = _fake_client(pcm_24k)

        first = await synthesize_turn_audio("Cache me", settings=MagicMock(), client=client)
        second = await synthesize_turn_audio("Cache me", settings=MagicMock(), client=client)

        assert first == second
        client.aio.models.generate_content.assert_awaited_once()
        assert fixture_path("Cache me", tts.SALESPERSON_VOICE, tts.DEFAULT_TTS_MODEL).exists()

    async def test_no_audio_in_response_raises(self, fixtures_dir: Path) -> None:
        client = _fake_client(b"")
        with pytest.raises(RuntimeError, match="no audio"):
            await synthesize_turn_audio("Silent", settings=MagicMock(), client=client)

    def test_fixture_path_varies_by_text_and_voice(self) -> None:
        a = fixture_path("hello", "kore", "m")
        b = fixture_path("hello!", "kore", "m")
        c = fixture_path("hello", "puck", "m")
        assert len({a, b, c}) == 3


class TestWriteWav:
    def test_writes_playable_wav(self, tmp_path: Path) -> None:
        pcm = array("h", [100, -100] * 1200).tobytes()
        path = tmp_path / "artifacts" / "turn0.wav"

        write_wav(path, pcm, 24000)

        with wave.open(str(path), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 24000
            assert wf.readframes(wf.getnframes()) == pcm
