"""Tests for the PcmResampler linear PCM resampler."""

import math
from array import array

import pytest

from app.core.exceptions import InvalidRequestError
from app.llm_providers.audio import PcmResampler


def _pcm(samples: list[int]) -> bytes:
    return array("h", samples).tobytes()


def _unpcm(data: bytes) -> list[int]:
    a = array("h")
    a.frombytes(data)
    return list(a)


class TestConstruction:
    def test_rejects_non_positive_rates(self) -> None:
        with pytest.raises(ValueError):
            PcmResampler(0, 24000)
        with pytest.raises(ValueError):
            PcmResampler(16000, -1)


class TestPassthrough:
    def test_equal_rates_returns_input(self) -> None:
        r = PcmResampler(24000, 24000)
        data = _pcm([1, 2, 3, 4, 5])
        assert r.process(data) == data

    def test_odd_length_raises(self) -> None:
        r = PcmResampler(16000, 24000)
        with pytest.raises(InvalidRequestError):
            r.process(b"\x01\x02\x03")  # 3 bytes = not whole int16 samples

    def test_empty_chunk(self) -> None:
        r = PcmResampler(16000, 24000)
        assert r.process(b"") == b""


class TestUpsample:
    def test_constant_signal_stays_constant(self) -> None:
        r = PcmResampler(16000, 24000)
        out = _unpcm(r.process(_pcm([1000] * 100)))
        assert out  # produced some samples
        assert all(s == 1000 for s in out)

    def test_output_length_is_roughly_ratio(self) -> None:
        r = PcmResampler(16000, 24000)
        n = 1000
        out = _unpcm(r.process(_pcm(list(range(n)))))
        # ~1.5x samples; allow small rounding slack at the tail.
        assert abs(len(out) - math.floor(n * 1.5)) <= 2

    def test_interpolates_between_samples(self) -> None:
        # 2x upsample: outputs at input positions 0, 0.5, 1.0, 1.5, ...
        r = PcmResampler(1000, 2000)
        out = _unpcm(r.process(_pcm([0, 100])))
        # position 0 -> 0, position 0.5 -> 50, (position 1.0 needs sample 2, held back)
        assert out[0] == 0
        assert out[1] == 50

    def test_downsample_constant(self) -> None:
        r = PcmResampler(24000, 16000)
        out = _unpcm(r.process(_pcm([500] * 90)))
        assert out
        assert all(s == 500 for s in out)


class TestStatefulness:
    def test_chunked_equals_one_shot(self) -> None:
        signal = [int(1000 * math.sin(i / 5.0)) for i in range(300)]
        full = _pcm(signal)

        one_shot = PcmResampler(16000, 24000).process(full)

        streamed = PcmResampler(16000, 24000)
        pieces = b""
        for start in range(0, len(full), 40):  # 20-sample chunks
            pieces += streamed.process(full[start : start + 40])

        assert pieces == one_shot

    def test_sine_wave_smoothness(self) -> None:
        # Upsampling a smooth sine must not introduce large sample-to-sample jumps.
        signal = [int(8000 * math.sin(i / 8.0)) for i in range(200)]
        out = _unpcm(PcmResampler(16000, 24000).process(_pcm(signal)))
        max_input_delta = max(abs(signal[i + 1] - signal[i]) for i in range(len(signal) - 1))
        max_output_delta = max(abs(out[i + 1] - out[i]) for i in range(len(out) - 1))
        # Interpolated deltas are <= the largest input delta (plus rounding).
        assert max_output_delta <= max_input_delta + 1
