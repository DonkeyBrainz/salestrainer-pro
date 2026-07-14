"""Report models for eval-harness runs.

These are the harness's own report shapes — distinct from the end-user
session-grading models in app.models.evaluation.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class CheckResult(BaseModel):
    """Outcome of one deterministic check."""

    name: str
    passed: bool
    reason: str = ""


class JudgeDimensionScore(BaseModel):
    """One rubric dimension scored by the LLM judge."""

    dimension: str
    score: int = Field(ge=1, le=5)
    rationale: str


class TurnRecord(BaseModel):
    """Captured state around one scripted turn (customer suite)."""

    turn_index: int
    salesperson_message: str
    response_text: str = ""
    mood_before: str | None = None
    mood_after: str | None = None
    regard_before: str | None = None
    regard_after: str | None = None
    objections_raised_before: list[str] = Field(default_factory=list)
    objections_raised_after: list[str] = Field(default_factory=list)
    latency_ms: float | None = None
    usage: dict[str, int] | None = None


class CoachCaseRecord(BaseModel):
    """Captured output for one coach-analysis case (coach suite)."""

    case_index: int
    salesperson_message: str
    analysis: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float | None = None
    usage: dict[str, int] | None = None


class VoiceTurnRecord(BaseModel):
    """Captured audio-level data for one spoken turn (voice suite)."""

    turn_index: int
    salesperson_text: str
    # Provider's ASR of the audio we sent (comprehension ground truth).
    input_transcription: str = ""
    # Model's spoken reply, from output_transcription events.
    response_text: str = ""
    # Word error rate: salesperson_text vs input_transcription (None = no ASR).
    wer: float | None = None
    # ms from end of our audio send to the first output audio chunk.
    first_audio_ms: float | None = None
    # Duration of received output audio (bytes / 2 / 24000 * 1000).
    output_audio_ms: float | None = None
    audio_bytes: int = 0
    # Max |sample| in the output audio (0 = silent/empty).
    peak_amplitude: int = 0
    latency_ms: float | None = None
    usage: dict[str, int] | None = None
    # Saved WAV artifact path (relative to backend/), for human listening.
    audio_path: str | None = None


class ScenarioResult(BaseModel):
    """Result of running one scenario: transcript + checks + judge scores."""

    scenario_id: str
    tags: list[str] = Field(default_factory=list)
    passed: bool
    checks: list[CheckResult] = Field(default_factory=list)
    judge: list[JudgeDimensionScore] | None = None
    turns: list[TurnRecord] = Field(default_factory=list)
    cases: list[CoachCaseRecord] = Field(default_factory=list)
    voice_turns: list[VoiceTurnRecord] = Field(default_factory=list)
    total_latency_ms: float = 0.0
    usage: dict[str, int] = Field(default_factory=dict)
    error: str | None = None


class RunSummary(BaseModel):
    """Aggregate stats for a run."""

    scenario_count: int = 0
    passed_count: int = 0
    pass_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_usage: dict[str, int] = Field(default_factory=dict)
    pass_rate_by_tag: dict[str, float] = Field(default_factory=dict)
    judge_avg_by_dimension: dict[str, float] = Field(default_factory=dict)


class RunReport(BaseModel):
    """Full report for one harness run — serialized to JSON for diffing."""

    harness_version: str
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provider_name: str
    model: str
    suite: str
    judge_model: str | None = None
    scenario_results: list[ScenarioResult] = Field(default_factory=list)
    summary: RunSummary = Field(default_factory=RunSummary)


class ScenarioDiff(BaseModel):
    """Per-scenario comparison between two runs."""

    scenario_id: str
    baseline_passed: bool | None
    current_passed: bool | None
    regressed_checks: list[str] = Field(default_factory=list)
    fixed_checks: list[str] = Field(default_factory=list)


class ComparisonReport(BaseModel):
    """Diff of two RunReports (e.g. same suite, different model/provider)."""

    baseline_run_id: str
    current_run_id: str
    baseline_model: str
    current_model: str
    baseline_pass_rate: float
    current_pass_rate: float
    regressions: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    diffs: list[ScenarioDiff] = Field(default_factory=list)
