"""Tests for voice scenario loading and schema validation."""

from app.agents.personas import get_persona
from evals.scenarios.types import VoiceScenario, load_voice_scenarios


class TestLoadVoiceScenarios:
    def test_loads_all_and_validates(self) -> None:
        scenarios = load_voice_scenarios()
        assert len(scenarios) >= 4
        assert all(isinstance(s, VoiceScenario) for s in scenarios)
        assert all(s.turns for s in scenarios)

    def test_all_persona_ids_exist(self) -> None:
        for scenario in load_voice_scenarios():
            assert get_persona(scenario.persona_id) is not None, scenario.persona_id

    def test_tag_filter_uses_and_semantics(self) -> None:
        comprehension = load_voice_scenarios(["voice:comprehension"])
        assert comprehension
        both = load_voice_scenarios(["voice:comprehension", "voice:numbers"])
        assert {s.id for s in both} <= {s.id for s in comprehension}
        assert all("voice:numbers" in s.tags for s in both)

    def test_turn_defaults(self) -> None:
        scenario = VoiceScenario.model_validate(
            {
                "id": "x",
                "persona_id": "practical_family",
                "turns": [{"salesperson_text": "hello"}],
            }
        )
        turn = scenario.turns[0]
        assert turn.max_wer == 0.5
        assert turn.max_first_audio_ms == 25000
        assert turn.min_output_audio_ms == 300
        assert turn.forbid_phrases == []
