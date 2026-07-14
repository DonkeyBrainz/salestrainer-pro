"""Tests for per-provider persona voice casting and resolution."""

import pytest

from app.agents.personas import PERSONAS
from app.agents.state import (
    CustomerPersona,
    Difficulty,
    RegardLevel,
    Timeline,
)
from app.llm_providers.voices import DEFAULT_VOICES, resolve_voice

# Providers every persona must be cast for. Kept in sync with the live-provider
# registry (app/llm_providers registry, Phase 5); the coverage test below is the
# guard that no persona ships without a voice for a supported provider.
REQUIRED_PROVIDERS = {"gemini", "openai", "nova"}


def _make_persona(voices: dict[str, str]) -> CustomerPersona:
    """Build a minimal persona with a custom voices mapping."""
    return CustomerPersona(
        id="voice_test",
        name="Test",
        backstory="Test",
        looking_for="House",
        budget_range=(100000, 200000),
        timeline=Timeline.FLEXIBLE,
        difficulty=Difficulty.MEDIUM_REGARD,
        initial_regard=RegardLevel.LOW,
        primary_pbm="value",
        voices=voices,
    )


class TestPersonaVoiceCoverage:
    """Every shipped persona must have a voice for every supported provider."""

    @pytest.mark.parametrize("persona_id", sorted(PERSONAS))
    def test_persona_covers_all_providers(self, persona_id: str) -> None:
        persona = PERSONAS[persona_id]
        for provider in REQUIRED_PROVIDERS:
            voice = persona.voices.get(provider)
            assert voice, f"{persona_id} has no voice for provider {provider!r}"

    def test_required_providers_have_defaults(self) -> None:
        # Fallback must exist for every provider a persona can be cast for.
        assert REQUIRED_PROVIDERS.issubset(DEFAULT_VOICES.keys())


class TestResolveVoice:
    def test_returns_mapped_voice(self) -> None:
        persona = _make_persona({"gemini": "puck", "openai": "cedar", "nova": "matthew"})
        assert resolve_voice(persona, "gemini") == "puck"
        assert resolve_voice(persona, "openai") == "cedar"
        assert resolve_voice(persona, "nova") == "matthew"

    def test_falls_back_to_default_for_missing_provider(self) -> None:
        persona = _make_persona({"gemini": "puck"})  # no openai/nova cast
        assert resolve_voice(persona, "openai") == DEFAULT_VOICES["openai"]
        assert resolve_voice(persona, "nova") == DEFAULT_VOICES["nova"]

    def test_falls_back_when_voice_is_empty(self) -> None:
        persona = _make_persona({"gemini": "puck", "openai": ""})
        assert resolve_voice(persona, "openai") == DEFAULT_VOICES["openai"]

    def test_unknown_provider_raises(self) -> None:
        persona = _make_persona({"gemini": "puck"})
        with pytest.raises(KeyError):
            resolve_voice(persona, "does_not_exist")
