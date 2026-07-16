"""Deterministic checks for voice-suite scenario results.

These score the audio path itself: did the provider's ASR hear us correctly
(WER), did the model speak promptly and audibly, and did the spoken reply
avoid forbidden phrases. All are pure functions of the captured
``VoiceTurnRecord`` + the scenario's expectations.
"""

import re

from evals.report.models import CheckResult, ScenarioResult, VoiceTurnRecord
from evals.scenarios.types import VoiceScenario, VoiceTurnTrigger

_WORD_RE = re.compile(r"[a-z0-9']+")


def _normalize_words(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into words for WER comparison."""
    return _WORD_RE.findall(text.lower())


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Word error rate: Levenshtein distance over reference length.

    0.0 = perfect transcription; 1.0 = everything wrong (capped above 1.0 for
    hypotheses much longer than the reference).
    """
    ref = _normalize_words(reference)
    hyp = _normalize_words(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0

    # Standard dynamic-programming edit distance over words.
    prev = list(range(len(hyp) + 1))
    for i, ref_word in enumerate(ref, start=1):
        curr = [i] + [0] * len(hyp)
        for j, hyp_word in enumerate(hyp, start=1):
            cost = 0 if ref_word == hyp_word else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1] / len(ref)


def check_asr_comprehension(
    expected: VoiceTurnTrigger, turn: VoiceTurnRecord
) -> CheckResult | None:
    """Provider's ASR of our audio must be close enough to the script."""
    if expected.max_wer is None:
        return None
    name = f"turn{turn.turn_index}_asr_comprehension"
    if not turn.input_transcription:
        return CheckResult(
            name=name, passed=False, reason="no input_transcription received from provider"
        )
    wer = (
        turn.wer
        if turn.wer is not None
        else word_error_rate(expected.salesperson_text, turn.input_transcription)
    )
    if wer > expected.max_wer:
        return CheckResult(
            name=name,
            passed=False,
            reason=f"WER {wer:.2f} > {expected.max_wer:.2f} (heard: {turn.input_transcription!r})",
        )
    return CheckResult(name=name, passed=True, reason=f"WER {wer:.2f}")


def check_no_forbidden_phrases(
    expected: VoiceTurnTrigger, turn: VoiceTurnRecord
) -> CheckResult | None:
    """Spoken reply must not contain any forbidden phrase."""
    if not expected.forbid_phrases:
        return None
    name = f"turn{turn.turn_index}_forbid_phrases"
    lowered = turn.response_text.lower()
    hits = [p for p in expected.forbid_phrases if p.lower() in lowered]
    if hits:
        return CheckResult(name=name, passed=False, reason=f"said forbidden: {hits}")
    return CheckResult(name=name, passed=True)


def check_no_forbidden_regex(
    expected: VoiceTurnTrigger, turn: VoiceTurnRecord
) -> CheckResult | None:
    """Spoken reply must not match any forbidden pattern (e.g. any dollar figure)."""
    if not expected.forbid_regex:
        return None
    name = f"turn{turn.turn_index}_forbid_regex"
    hits = [p for p in expected.forbid_regex if re.search(p, turn.response_text, re.IGNORECASE)]
    if hits:
        return CheckResult(name=name, passed=False, reason=f"matched forbidden pattern: {hits}")
    return CheckResult(name=name, passed=True)


def check_first_audio_latency(
    expected: VoiceTurnTrigger, turn: VoiceTurnRecord
) -> CheckResult | None:
    """Model must start speaking within the latency budget."""
    if expected.max_first_audio_ms is None:
        return None
    name = f"turn{turn.turn_index}_first_audio_latency"
    if turn.first_audio_ms is None:
        return CheckResult(name=name, passed=False, reason="no audio received")
    if turn.first_audio_ms > expected.max_first_audio_ms:
        return CheckResult(
            name=name,
            passed=False,
            reason=f"first audio at {turn.first_audio_ms:.0f}ms "
            f"> {expected.max_first_audio_ms:.0f}ms",
        )
    return CheckResult(name=name, passed=True, reason=f"{turn.first_audio_ms:.0f}ms")


def check_spoke_audibly(expected: VoiceTurnTrigger, turn: VoiceTurnRecord) -> CheckResult | None:
    """Output audio must exist, be long enough, and not be silence."""
    if expected.min_output_audio_ms is None:
        return None
    name = f"turn{turn.turn_index}_spoke_audibly"
    duration = turn.output_audio_ms or 0.0
    if duration < expected.min_output_audio_ms:
        return CheckResult(
            name=name,
            passed=False,
            reason=f"output audio {duration:.0f}ms < {expected.min_output_audio_ms:.0f}ms",
        )
    # PCM16 speech peaks are typically thousands; < 100 is effectively silence.
    if turn.peak_amplitude < 100:
        return CheckResult(
            name=name, passed=False, reason=f"audio is silent (peak={turn.peak_amplitude})"
        )
    return CheckResult(name=name, passed=True, reason=f"{duration:.0f}ms audible audio")


def run_voice_checks(scenario: VoiceScenario, result: ScenarioResult) -> list[CheckResult]:
    """Run all deterministic voice checks for a completed scenario."""
    if result.error:
        return [CheckResult(name="scenario_completed", passed=False, reason=result.error)]

    checks: list[CheckResult] = [CheckResult(name="scenario_completed", passed=True)]
    for turn, expected in zip(result.voice_turns, scenario.turns, strict=False):
        for check_fn in (
            check_asr_comprehension,
            check_no_forbidden_phrases,
            check_no_forbidden_regex,
            check_first_audio_latency,
            check_spoke_audibly,
        ):
            outcome = check_fn(expected, turn)
            if outcome is not None:
                checks.append(outcome)
    return checks
