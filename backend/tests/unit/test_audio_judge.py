"""Tests for the audio-level judge (mocked multimodal client)."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.agents.personas import get_persona
from evals.judge.audio_judge import AUDIO_DIMENSIONS, judge_scenario_audio
from evals.judge.judge import DimensionScore, JudgeVerdict
from evals.report.models import ScenarioResult, VoiceTurnRecord


def _result_with_audio(tmp_path: Path) -> ScenarioResult:
    wav = tmp_path / "turn0.wav"
    wav.write_bytes(b"RIFFfakewav")
    return ScenarioResult(
        scenario_id="s",
        passed=True,
        voice_turns=[VoiceTurnRecord(turn_index=0, salesperson_text="hi", audio_path=str(wav))],
    )


def _client_returning(verdict: JudgeVerdict | None) -> MagicMock:
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=SimpleNamespace(parsed=verdict))
    return client


class TestJudgeScenarioAudio:
    async def test_scores_valid_dimensions(self, tmp_path: Path) -> None:
        verdict = JudgeVerdict(
            dimension_scores=[
                DimensionScore(dimension="vocal_naturalness", score=4, rationale="smooth"),
                DimensionScore(dimension="not_a_dimension", score=1, rationale="ignored"),
            ]
        )
        client = _client_returning(verdict)
        persona = get_persona("practical_family")
        assert persona is not None

        scores = await judge_scenario_audio(
            _result_with_audio(tmp_path), persona, MagicMock(), client=client
        )

        assert scores is not None
        assert [s.dimension for s in scores] == ["vocal_naturalness"]
        # The WAV bytes and the persona made it into the call.
        call = client.aio.models.generate_content.await_args
        contents = call.kwargs["contents"]
        assert persona.name in contents[0]
        assert len(contents) == 2  # prompt + one audio part

    async def test_no_audio_returns_none(self) -> None:
        result = ScenarioResult(scenario_id="s", passed=True, voice_turns=[])
        scores = await judge_scenario_audio(result, MagicMock(), MagicMock(), client=MagicMock())
        assert scores is None

    async def test_judge_failure_returns_none(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.aio.models.generate_content = AsyncMock(side_effect=RuntimeError("boom"))
        persona = get_persona("practical_family")
        assert persona is not None
        scores = await judge_scenario_audio(
            _result_with_audio(tmp_path), persona, MagicMock(), client=client
        )
        assert scores is None

    async def test_unstructured_output_returns_none(self, tmp_path: Path) -> None:
        client = _client_returning(None)
        persona = get_persona("practical_family")
        assert persona is not None
        scores = await judge_scenario_audio(
            _result_with_audio(tmp_path), persona, MagicMock(), client=client
        )
        assert scores is None

    def test_dimension_names_unique(self) -> None:
        names = [d.name for d in AUDIO_DIMENSIONS]
        assert len(names) == len(set(names))
