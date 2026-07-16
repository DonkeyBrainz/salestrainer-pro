"""Scenario schemas for the eval harness.

Scenarios are authored as YAML files (one per scenario) under
``evals/scenarios/customer/`` and ``evals/scenarios/coach/`` and validated
into these models at load time so schema errors fail fast.
"""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from app.agents.state import Mood
from app.models.coach import InterventionLevel

MoodDirection = Literal["improve", "worsen", "same", "same_or_worse"]


class CustomerTurnTrigger(BaseModel):
    """One scripted salesperson turn and the expectations after it."""

    salesperson_message: str
    inject_objection_expected: bool = False
    expected_mood_after: Mood | None = None
    expected_mood_direction: MoodDirection | None = None
    forbid_phrases: list[str] = Field(default_factory=list)


class CustomerScenario(BaseModel):
    """A scripted conversation driving the customer agent."""

    id: str
    tags: list[str] = Field(default_factory=list)
    persona_id: str
    initial_mood: Mood | None = None
    seed: int = 0
    turns: list[CustomerTurnTrigger]


class CoachTurnCase(BaseModel):
    """One salesperson message analyzed by the coach, with expectations."""

    salesperson_message: str
    conversation_so_far: list[dict[str, str]] = Field(
        default_factory=list, description='[{"role": "user"|"assistant", "content": ...}]'
    )
    stage_progress_before: dict[str, Any] = Field(
        default_factory=dict, description="Partial CoreStageProgress kwargs"
    )
    expect_techniques_any_of: list[str] = Field(default_factory=list)
    expect_deviation_flagged: bool | None = None
    expect_intervention_at_least: InterventionLevel | None = None
    expect_ready_for_next_stage: bool | None = None


class CoachScenario(BaseModel):
    """A set of scripted coach-analysis cases."""

    id: str
    tags: list[str] = Field(default_factory=list)
    persona_id: str
    cases: list[CoachTurnCase]


class VoiceTurnTrigger(BaseModel):
    """One scripted spoken salesperson turn and its audio-level expectations.

    ``salesperson_text`` is synthesized to speech (evals.audio.tts) and streamed
    to the live model as PCM16 audio — the checks then score the provider's
    audio front-end (ASR comprehension), spoken-reply text, and responsiveness.
    """

    salesperson_text: str
    forbid_phrases: list[str] = Field(default_factory=list)
    # Regex variant of forbid_phrases, for patterns that can't be a fixed string
    # (e.g. "any dollar figure" to catch unprompted budget disclosure).
    forbid_regex: list[str] = Field(default_factory=list)
    # Comprehension: word-error-rate between the script and the provider's ASR
    # of our synthesized audio (input_transcription). None = don't check.
    max_wer: float | None = 0.5
    # Responsiveness: time to first audio chunk after our audio finished
    # sending. Note we stream faster than realtime, so the model still has to
    # "listen through" the whole utterance + silence tail before replying —
    # budgets are calibrated from observed provider baselines, not UX targets.
    max_first_audio_ms: float | None = 25000
    # The model actually spoke (output audio duration floor).
    min_output_audio_ms: float | None = 300


class VoiceScenario(BaseModel):
    """A scripted spoken conversation driving a live speech-to-speech session."""

    id: str
    tags: list[str] = Field(default_factory=list)
    persona_id: str
    turns: list[VoiceTurnTrigger]


SCENARIOS_DIR = Path(__file__).parent


def _load_yaml_files(subdir: str) -> list[dict[str, Any]]:
    """Load all YAML files under a scenarios subdirectory, sorted by name."""
    docs: list[dict[str, Any]] = []
    for path in sorted((SCENARIOS_DIR / subdir).glob("*.yaml")):
        with path.open() as f:
            doc = yaml.safe_load(f)
        if not isinstance(doc, dict):
            raise ValueError(f"Scenario file {path} must contain a YAML mapping")
        docs.append(doc)
    return docs


def load_customer_scenarios(tags: list[str] | None = None) -> list[CustomerScenario]:
    """Load and validate customer scenarios, optionally filtered by tags."""
    scenarios = [CustomerScenario.model_validate(d) for d in _load_yaml_files("customer")]
    return _filter_by_tags(scenarios, tags)


def load_coach_scenarios(tags: list[str] | None = None) -> list[CoachScenario]:
    """Load and validate coach scenarios, optionally filtered by tags."""
    scenarios = [CoachScenario.model_validate(d) for d in _load_yaml_files("coach")]
    return _filter_by_tags(scenarios, tags)


def load_voice_scenarios(tags: list[str] | None = None) -> list[VoiceScenario]:
    """Load and validate voice scenarios, optionally filtered by tags."""
    scenarios = [VoiceScenario.model_validate(d) for d in _load_yaml_files("voice")]
    return _filter_by_tags(scenarios, tags)


def _filter_by_tags[S: (CustomerScenario, CoachScenario, VoiceScenario)](
    scenarios: list[S], tags: list[str] | None
) -> list[S]:
    """Keep scenarios matching ALL requested tags (no filter if tags empty)."""
    if not tags:
        return scenarios
    wanted = set(tags)
    return [s for s in scenarios if wanted.issubset(set(s.tags))]
