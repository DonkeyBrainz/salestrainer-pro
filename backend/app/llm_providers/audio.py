"""Dependency-free PCM audio resampling for provider adapters.

Some speech-to-speech providers expect a different input sample rate than the
browser captures (16 kHz). ``PcmResampler`` linearly resamples 16-bit mono PCM
and is stateful across chunks, so streaming a signal in pieces yields output
identical to resampling the whole signal at once.

Deliberately avoids ``audioop`` (removed in Python 3.13) and numpy (not a
dependency).
"""

import math
from array import array

from app.core.exceptions import InvalidRequestError


class PcmResampler:
    """Streaming linear resampler for 16-bit mono little-endian PCM.

    Example: ``PcmResampler(16000, 24000)`` for a 16 kHz -> 24 kHz upsample.
    Feed successive chunks to :meth:`process`; state (the previous input sample
    and a global fractional read position) carries across calls so chunk
    boundaries are seamless.
    """

    def __init__(self, src_rate: int, dst_rate: int) -> None:
        """Initialize the resampler.

        Args:
            src_rate: Source sample rate in Hz.
            dst_rate: Target sample rate in Hz.

        Raises:
            ValueError: If either rate is not positive.
        """
        if src_rate <= 0 or dst_rate <= 0:
            raise ValueError(f"Sample rates must be positive, got {src_rate}, {dst_rate}")
        self.src_rate = src_rate
        self.dst_rate = dst_rate
        # Input samples consumed per output sample.
        self._step = src_rate / dst_rate
        self._prev_sample = 0  # last input sample from the previous chunk
        self._have_prev = False
        self._next_index = 0  # global index of the next incoming input sample
        self._out_pos = 0.0  # global input position of the next output sample

    def process(self, chunk: bytes) -> bytes:
        """Resample a chunk of PCM and return the resampled bytes.

        Args:
            chunk: Raw little-endian int16 mono PCM (even byte length).

        Returns:
            Resampled little-endian int16 mono PCM (may be empty if no output
            samples land within this chunk).

        Raises:
            InvalidRequestError: If ``chunk`` has an odd byte length (not whole
                int16 samples).
        """
        if len(chunk) % 2 != 0:
            raise InvalidRequestError("PCM chunk length must be even (16-bit samples)")

        # Exact passthrough when no rate change is needed.
        if self.src_rate == self.dst_rate:
            return chunk

        samples = array("h")
        samples.frombytes(chunk)
        n = len(samples)
        if n == 0:
            return b""

        base = self._next_index
        last_available = base + n - 1  # global index of the last input sample we hold

        out = array("h")
        # Emit output samples whose interpolation window (i, i+1) is fully
        # covered by samples we currently hold: i+1 <= last_available. A sample
        # landing exactly on last_available waits for the next chunk (its i+1
        # neighbor has not arrived yet).
        while math.floor(self._out_pos) + 1 <= last_available:
            pos = self._out_pos
            i = math.floor(pos)
            frac = pos - i

            s0 = self._sample_at(i, samples, base)
            s1 = self._sample_at(i + 1, samples, base)
            out.append(round(s0 + (s1 - s0) * frac))

            self._out_pos += self._step

        self._prev_sample = samples[-1]
        self._have_prev = True
        self._next_index = base + n
        return out.tobytes()

    def _sample_at(self, index: int, samples: "array[int]", base: int) -> int:
        """Resolve a global input-sample index to a value.

        ``index`` is at most one behind ``base`` (the carried previous sample);
        earlier indices never occur because output never lags input by more than
        one sample.
        """
        if index < base:
            # index == base - 1 -> the previous chunk's last sample.
            return self._prev_sample if self._have_prev else int(samples[0])
        return int(samples[index - base])
