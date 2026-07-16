"""Runner that drives a live speech-to-speech session through a scripted scenario.

Mirrors the production relay sequence (app/api/ws/gemini_relay.py) minus the
browser WebSocket: one ``connect_live`` per scenario, then per scripted turn we
stream a TTS-synthesized salesperson utterance as PCM16 audio and consume the
session's LiveEvents until the model finishes its spoken reply.

What gets captured per turn (VoiceTurnRecord): the provider's own ASR of our
audio (input_transcription — comprehension ground truth), the model's spoken
words (output_transcription), time-to-first-audio, output audio duration and
peak amplitude, billed token usage, and a saved WAV artifact for human ears.
"""

import asyncio
import logging
import time
from array import array
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from app.agents.personas import get_persona
from app.agents.prompts import build_live_system_instruction
from app.agents.state import CoreStageProgress, CustomerAgentState, Mood, SalesStage
from app.config import Settings
from app.llm_providers.streaming import LiveSession, LLMStreamProvider
from app.llm_providers.voices import resolve_voice
from evals.audio.tts import synthesize_turn_audio, write_wav
from evals.checks.voice_checks import word_error_rate
from evals.report.models import ScenarioResult, VoiceTurnRecord
from evals.scenarios.types import VoiceScenario

logger = logging.getLogger(__name__)

OUTPUT_SAMPLE_RATE = 24000
SEND_CHUNK_BYTES = 3200  # 100ms of 16kHz PCM16
CONNECT_TIMEOUT_S = 30.0
TURN_TIMEOUT_S = 60.0
# After "end", keep draining briefly: OpenAI's input transcription can arrive
# after response.done.
GRACE_DRAIN_S = 2.0

RESULTS_AUDIO_DIR = Path(__file__).parent.parent / "results" / "audio"


def _connect_state(scenario: VoiceScenario) -> CustomerAgentState:
    """Minimal agent state for the one-shot system prompt (as at connect time)."""
    persona = get_persona(scenario.persona_id)
    if persona is None:
        raise ValueError(f"Unknown persona_id: {scenario.persona_id!r}")
    return {
        "messages": [],
        "turn_count": 0,
        "persona": persona,
        "mood": Mood.NEUTRAL,
        "regard_level": persona.initial_regard,
        "objections_available": list(persona.objections),
        "objections_raised": [],
        "objections_resolved": [],
        "stage_progress": CoreStageProgress(current_stage=SalesStage.CONNECT),
        "session_id": f"voice-eval-{scenario.id}",
        "user_id": "voice-eval-harness",
    }


class _TurnCapture:
    """Everything observed between sending our audio and the turn's end."""

    def __init__(self) -> None:
        self.audio = bytearray()
        self.input_transcription = ""
        self.response_text = ""
        self.first_audio_at: float | None = None
        self.usage: dict[str, int] | None = None
        self.ended = False

    def absorb(self, event: dict[str, Any]) -> None:
        etype = event.get("type")
        if etype == "audio" and event.get("audio_data"):
            if self.first_audio_at is None:
                self.first_audio_at = time.monotonic()
            self.audio.extend(event["audio_data"])
        elif etype == "input_transcription" and event.get("text"):
            self.input_transcription += event["text"]
        elif etype == "output_transcription" and event.get("text"):
            self.response_text += event["text"]
        elif etype == "usage" and event.get("usage"):
            # Keep the last usage report of the turn (cumulative reporters
            # overwrite; per-turn reporters emit once per response).
            self.usage = dict(event["usage"])
        elif etype == "end":
            self.ended = True


async def _send_pcm(session: LiveSession, pcm: bytes) -> None:
    """Stream PCM16 audio to the session in browser-sized chunks."""
    for offset in range(0, len(pcm), SEND_CHUNK_BYTES):
        await session.send_audio(pcm[offset : offset + SEND_CHUNK_BYTES])


class _EventPump:
    """Consumes ``session.receive()`` in one task, exposing a pollable queue.

    Timing out a read must not cancel the receive generator itself
    (``asyncio.wait_for(anext(gen), ...)`` kills the generator on timeout), so
    the generator is drained by a dedicated task and turn logic polls the queue.
    """

    def __init__(self, session: LiveSession) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._task = asyncio.create_task(self._pump(session))

    async def _pump(self, session: LiveSession) -> None:
        try:
            async for event in session.receive():
                await self._queue.put(event)
        except Exception as e:  # noqa: BLE001 - surfaced to the turn loop
            await self._queue.put({"type": "_pump_error", "error": e})
        else:
            await self._queue.put({"type": "_pump_closed"})

    async def next_event(self, timeout: float) -> dict[str, Any]:
        """Next LiveEvent, raising the pump's error/close/timeout states."""
        event = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        if event.get("type") == "_pump_error":
            raise event["error"]
        if event.get("type") == "_pump_closed":
            raise ConnectionError("provider stream ended before the turn completed")
        return event

    def stop(self) -> None:
        self._task.cancel()


async def _drive_turn(
    session: LiveSession,
    pump: _EventPump,
    pcm: bytes,
    *,
    timeout_s: float | None = None,
    grace_s: float | None = None,
) -> tuple[_TurnCapture, float]:
    """Send one utterance and consume events until the model's turn completes.

    Returns the capture plus the send-complete timestamp (for latency math).
    """
    # Late-bound so tests can monkeypatch the module constants.
    timeout_s = TURN_TIMEOUT_S if timeout_s is None else timeout_s
    grace_s = GRACE_DRAIN_S if grace_s is None else grace_s

    capture = _TurnCapture()
    await _send_pcm(session, pcm)
    sent_at = time.monotonic()

    deadline = sent_at + timeout_s
    while not capture.ended:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"no turn completion within {timeout_s:.0f}s")
        try:
            event = await pump.next_event(timeout=remaining)
        except TimeoutError:
            raise TimeoutError(f"no turn completion within {timeout_s:.0f}s") from None
        capture.absorb(event)

    # Grace drain for stragglers (late input transcription, usage reports).
    while True:
        try:
            event = await pump.next_event(timeout=grace_s)
        except (TimeoutError, ConnectionError):
            break
        if event.get("type") == "end":
            continue
        capture.absorb(event)

    return capture, sent_at


def _accumulate_usage(totals: dict[str, int], turn_usages: list[dict[str, int] | None]) -> None:
    """Fold per-turn usage into scenario totals.

    Providers differ: OpenAI reports per-response usage (sum is correct);
    Nova reports cumulative session totals (monotone across turns — summing
    would overstate, so detect monotone growth and take deltas). Verify per
    provider on the live smoke run.
    """
    seen = [u for u in turn_usages if u]
    if not seen:
        return
    monotone = (
        all(seen[i]["total_tokens"] >= seen[i - 1]["total_tokens"] for i in range(1, len(seen)))
        and len(seen) > 1
    )
    prev: dict[str, int] = {}
    for usage in seen:
        for key, value in usage.items():
            delta = value - prev.get(key, 0) if monotone else value
            totals[key] = totals.get(key, 0) + max(delta, 0)
        if monotone:
            prev = usage


async def run_voice_scenario(
    scenario: VoiceScenario,
    provider: LLMStreamProvider,
    settings: Settings,
    *,
    run_id: str,
    tts_client: Any | None = None,
    artifacts_dir: Path | None = None,
) -> ScenarioResult:
    """Run one scripted voice scenario against a live provider session."""
    persona = get_persona(scenario.persona_id)
    if persona is None:
        raise ValueError(f"Unknown persona_id: {scenario.persona_id!r}")

    system_instruction = build_live_system_instruction(
        persona, _connect_state(scenario), provider.name
    )
    voice = resolve_voice(persona, provider.name)
    audio_dir = (artifacts_dir or RESULTS_AUDIO_DIR) / run_id / scenario.id

    # Synthesize (or load cached) fixtures up front so TTS failures surface
    # before we open a billed live session.
    fixtures = [
        await synthesize_turn_audio(turn.salesperson_text, settings=settings, client=tts_client)
        for turn in scenario.turns
    ]

    voice_turns: list[VoiceTurnRecord] = []
    total_latency = 0.0
    usage_totals: dict[str, int] = {}
    turn_usages: list[dict[str, int] | None] = []

    try:
        async with AsyncExitStack() as stack:
            # Opening the provider stream gets its own timeout — a hung
            # handshake (bad entitlement, network black hole) must fail the
            # scenario, not the whole suite run.
            async with asyncio.timeout(CONNECT_TIMEOUT_S):
                session = await stack.enter_async_context(
                    provider.connect_live(system_instruction=system_instruction, voice=voice)
                )
            pump = _EventPump(session)
            try:
                for i, (turn, pcm) in enumerate(zip(scenario.turns, fixtures, strict=True)):
                    started = time.monotonic()
                    capture, sent_at = await _drive_turn(session, pump, pcm)
                    latency_ms = (time.monotonic() - started) * 1000
                    total_latency += latency_ms

                    first_audio_ms = (
                        (capture.first_audio_at - sent_at) * 1000
                        if capture.first_audio_at is not None
                        else None
                    )
                    output_audio = bytes(capture.audio)
                    samples = array("h")
                    if len(output_audio) >= 2:
                        samples.frombytes(output_audio[: len(output_audio) // 2 * 2])
                    peak = max((abs(s) for s in samples), default=0)

                    audio_path: str | None = None
                    if output_audio:
                        wav_path = audio_dir / f"turn{i}.wav"
                        write_wav(wav_path, output_audio, OUTPUT_SAMPLE_RATE)
                        audio_path = str(wav_path)

                    turn_usages.append(capture.usage)
                    voice_turns.append(
                        VoiceTurnRecord(
                            turn_index=i,
                            salesperson_text=turn.salesperson_text,
                            input_transcription=capture.input_transcription.strip(),
                            response_text=capture.response_text.strip(),
                            wer=(
                                word_error_rate(turn.salesperson_text, capture.input_transcription)
                                if capture.input_transcription
                                else None
                            ),
                            first_audio_ms=first_audio_ms,
                            output_audio_ms=len(output_audio) / 2 / OUTPUT_SAMPLE_RATE * 1000,
                            audio_bytes=len(output_audio),
                            peak_amplitude=peak,
                            latency_ms=latency_ms,
                            usage=capture.usage,
                            audio_path=audio_path,
                        )
                    )
            finally:
                pump.stop()
    except Exception as e:  # noqa: BLE001 - a failing scenario must not kill the run
        _accumulate_usage(usage_totals, turn_usages)
        return ScenarioResult(
            scenario_id=scenario.id,
            tags=scenario.tags,
            passed=False,
            voice_turns=voice_turns,
            total_latency_ms=total_latency,
            usage=usage_totals,
            error=f"{type(e).__name__}: {e}",
        )

    _accumulate_usage(usage_totals, turn_usages)
    return ScenarioResult(
        scenario_id=scenario.id,
        tags=scenario.tags,
        passed=True,  # provisional; checks decide the final value
        voice_turns=voice_turns,
        total_latency_ms=total_latency,
        usage=usage_totals,
    )
