"""Tests for the voice-suite deterministic checks and WER metric."""

from evals.checks.voice_checks import (
    check_asr_comprehension,
    check_first_audio_latency,
    check_no_forbidden_phrases,
    check_no_forbidden_regex,
    check_spoke_audibly,
    run_voice_checks,
    word_error_rate,
)
from evals.report.models import ScenarioResult, VoiceTurnRecord
from evals.scenarios.types import VoiceScenario, VoiceTurnTrigger


def _turn(**kwargs) -> VoiceTurnRecord:
    defaults = {
        "turn_index": 0,
        "salesperson_text": "hello there",
        "input_transcription": "hello there",
        "response_text": "Hi, nice to meet you.",
        "first_audio_ms": 1500.0,
        "output_audio_ms": 2000.0,
        "peak_amplitude": 5000,
    }
    defaults.update(kwargs)
    return VoiceTurnRecord(**defaults)


def _trigger(**kwargs) -> VoiceTurnTrigger:
    defaults = {"salesperson_text": "hello there"}
    defaults.update(kwargs)
    return VoiceTurnTrigger(**defaults)


class TestWordErrorRate:
    def test_perfect_match(self) -> None:
        assert word_error_rate("Hello there, friend!", "hello there friend") == 0.0

    def test_case_and_punctuation_insensitive(self) -> None:
        assert word_error_rate("It's $485,000 right?", "its 485 000 right") > 0.0
        assert word_error_rate("Hello, World.", "hello world") == 0.0

    def test_one_substitution(self) -> None:
        assert word_error_rate("the red house", "the blue house") == 1 / 3

    def test_deletion_and_insertion(self) -> None:
        assert word_error_rate("a b c d", "a c d") == 0.25  # one deletion
        assert word_error_rate("a b", "a x b") == 0.5  # one insertion

    def test_empty_reference(self) -> None:
        assert word_error_rate("", "") == 0.0
        assert word_error_rate("", "something") == 1.0

    def test_totally_wrong(self) -> None:
        assert word_error_rate("one two three", "four five six") == 1.0


class TestAsrComprehension:
    def test_pass_within_threshold(self) -> None:
        result = check_asr_comprehension(_trigger(max_wer=0.5), _turn())
        assert result is not None and result.passed

    def test_fail_over_threshold(self) -> None:
        turn = _turn(input_transcription="completely different words entirely spoken")
        result = check_asr_comprehension(_trigger(max_wer=0.3), turn)
        assert result is not None and not result.passed
        assert "WER" in result.reason

    def test_missing_transcription_fails(self) -> None:
        result = check_asr_comprehension(_trigger(), _turn(input_transcription=""))
        assert result is not None and not result.passed

    def test_disabled_when_none(self) -> None:
        assert check_asr_comprehension(_trigger(max_wer=None), _turn()) is None

    def test_uses_precomputed_wer_when_set(self) -> None:
        turn = _turn(wer=0.9)  # stored value wins over recomputation
        result = check_asr_comprehension(_trigger(max_wer=0.5), turn)
        assert result is not None and not result.passed


class TestForbidPhrases:
    def test_flags_forbidden(self) -> None:
        turn = _turn(response_text="Well, as an AI, I cannot say.")
        result = check_no_forbidden_phrases(_trigger(forbid_phrases=["as an AI"]), turn)
        assert result is not None and not result.passed

    def test_passes_clean(self) -> None:
        result = check_no_forbidden_phrases(_trigger(forbid_phrases=["as an AI"]), _turn())
        assert result is not None and result.passed

    def test_disabled_without_phrases(self) -> None:
        assert check_no_forbidden_phrases(_trigger(), _turn()) is None


class TestForbidRegex:
    def test_flags_forbidden(self) -> None:
        turn = _turn(response_text="Well, I'm looking at around $350,000 for this.")
        result = check_no_forbidden_regex(
            _trigger(forbid_regex=[r"\$\s?\d{2,3}[,]?\d{3}"]), turn
        )
        assert result is not None and not result.passed

    def test_passes_clean(self) -> None:
        result = check_no_forbidden_regex(_trigger(forbid_regex=[r"\$\s?\d{2,3}[,]?\d{3}"]), _turn())
        assert result is not None and result.passed

    def test_disabled_without_patterns(self) -> None:
        assert check_no_forbidden_regex(_trigger(), _turn()) is None


class TestFirstAudioLatency:
    def test_pass(self) -> None:
        result = check_first_audio_latency(_trigger(max_first_audio_ms=2000), _turn())
        assert result is not None and result.passed

    def test_fail_slow(self) -> None:
        result = check_first_audio_latency(
            _trigger(max_first_audio_ms=1000), _turn(first_audio_ms=5000.0)
        )
        assert result is not None and not result.passed

    def test_fail_no_audio(self) -> None:
        result = check_first_audio_latency(_trigger(), _turn(first_audio_ms=None))
        assert result is not None and not result.passed


class TestSpokeAudibly:
    def test_pass(self) -> None:
        result = check_spoke_audibly(_trigger(), _turn())
        assert result is not None and result.passed

    def test_fail_too_short(self) -> None:
        result = check_spoke_audibly(
            _trigger(min_output_audio_ms=1000), _turn(output_audio_ms=100.0)
        )
        assert result is not None and not result.passed

    def test_fail_silent(self) -> None:
        result = check_spoke_audibly(_trigger(), _turn(peak_amplitude=3))
        assert result is not None and not result.passed
        assert "silent" in result.reason


class TestRunVoiceChecks:
    def _scenario(self) -> VoiceScenario:
        return VoiceScenario(
            id="s",
            persona_id="practical_family",
            turns=[VoiceTurnTrigger(salesperson_text="hello there", forbid_phrases=["as an AI"])],
        )

    def test_error_short_circuits(self) -> None:
        result = ScenarioResult(scenario_id="s", passed=False, error="TimeoutError: boom")
        checks = run_voice_checks(self._scenario(), result)
        assert len(checks) == 1
        assert checks[0].name == "scenario_completed" and not checks[0].passed

    def test_all_checks_run_per_turn(self) -> None:
        result = ScenarioResult(scenario_id="s", passed=True, voice_turns=[_turn()])
        checks = run_voice_checks(self._scenario(), result)
        names = {c.name for c in checks}
        assert names == {
            "scenario_completed",
            "turn0_asr_comprehension",
            "turn0_forbid_phrases",
            "turn0_first_audio_latency",
            "turn0_spoke_audibly",
        }
        assert all(c.passed for c in checks)
