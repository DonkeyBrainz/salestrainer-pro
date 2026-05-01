"""Unit tests for coach agent models."""

import pytest
from pydantic import ValidationError

from app.models.coach import (
    CoachAnalysis,
    CoachAudioIntervention,
    CoachHint,
    InterventionLevel,
    SessionMode,
    StageItemUpdate,
)

# =============================================================================
# SessionMode Tests
# =============================================================================


class TestSessionMode:
    """Tests for SessionMode enum."""

    def test_session_mode_values(self) -> None:
        """Should have correct mode values."""
        assert SessionMode.TRAINING.value == "training"
        assert SessionMode.EVALUATION.value == "evaluation"

    def test_session_mode_from_string(self) -> None:
        """Should create mode from string."""
        assert SessionMode("training") == SessionMode.TRAINING
        assert SessionMode("evaluation") == SessionMode.EVALUATION


# =============================================================================
# InterventionLevel Tests
# =============================================================================


class TestInterventionLevel:
    """Tests for InterventionLevel enum."""

    def test_intervention_level_values(self) -> None:
        """Should have correct level values."""
        assert InterventionLevel.NONE.value == "none"
        assert InterventionLevel.INFO.value == "info"
        assert InterventionLevel.SUGGESTION.value == "suggestion"
        assert InterventionLevel.WARNING.value == "warning"
        assert InterventionLevel.CRITICAL.value == "critical"

    def test_intervention_level_ordering(self) -> None:
        """Levels should represent increasing severity."""
        levels = [
            InterventionLevel.NONE,
            InterventionLevel.INFO,
            InterventionLevel.SUGGESTION,
            InterventionLevel.WARNING,
            InterventionLevel.CRITICAL,
        ]
        # Verify all levels are distinct
        assert len(set(levels)) == 5


# =============================================================================
# StageItemUpdate Tests
# =============================================================================


class TestStageItemUpdate:
    """Tests for StageItemUpdate model."""

    def test_create_stage_item_update(self) -> None:
        """Should create update with all fields."""
        update = StageItemUpdate(
            stage="ENGAGE",
            item="non_business_greet",
            completed=True,
        )
        assert update.stage == "ENGAGE"
        assert update.item == "non_business_greet"
        assert update.completed is True

    def test_stage_item_update_incomplete(self) -> None:
        """Should handle incomplete items."""
        update = StageItemUpdate(
            stage="ASK",
            item="layer2_discovery",
            completed=False,
        )
        assert update.completed is False

    def test_stage_item_update_requires_all_fields(self) -> None:
        """Should require all fields."""
        with pytest.raises(ValidationError):
            StageItemUpdate(stage="SHOW")  # type: ignore[call-arg]


# =============================================================================
# CoachAnalysis Tests
# =============================================================================


class TestCoachAnalysis:
    """Tests for CoachAnalysis model."""

    def test_create_empty_analysis(self) -> None:
        """Should create analysis with defaults."""
        analysis = CoachAnalysis()
        assert analysis.techniques_detected == []
        assert analysis.stage_items_completed == []
        assert analysis.pbms_acknowledged == []
        assert analysis.deviations == []
        assert analysis.intervention_level == InterventionLevel.NONE
        assert analysis.hint is None
        assert analysis.confidence == 1.0

    def test_create_full_analysis(self) -> None:
        """Should create analysis with all fields."""
        analysis = CoachAnalysis(
            techniques_detected=["non_business_greet", "established_rapport"],
            stage_items_completed=[
                StageItemUpdate(stage="ENGAGE", item="non_business_greet", completed=True),
            ],
            pbms_acknowledged=["durability"],
            deviations=[],
            intervention_level=InterventionLevel.INFO,
            hint="Nice rapport building!",
            suggested_stage="ASK",
            confidence=0.95,
        )
        assert len(analysis.techniques_detected) == 2
        assert len(analysis.stage_items_completed) == 1
        assert analysis.intervention_level == InterventionLevel.INFO
        assert analysis.hint is not None

    def test_analysis_with_deviations(self) -> None:
        """Should track deviations and warnings."""
        analysis = CoachAnalysis(
            techniques_detected=[],
            deviations=["skipped_critical_questions", "pushed_product_too_early"],
            intervention_level=InterventionLevel.WARNING,
            hint="You skipped ASK stage - go back to discovery",
        )
        assert len(analysis.deviations) == 2
        assert analysis.intervention_level == InterventionLevel.WARNING

    def test_analysis_critical_intervention(self) -> None:
        """Should handle critical interventions."""
        analysis = CoachAnalysis(
            deviations=["major_stage_skip"],
            intervention_level=InterventionLevel.CRITICAL,
            hint="Hold on - let's pause and refocus on their needs",
            confidence=0.9,
        )
        assert analysis.intervention_level == InterventionLevel.CRITICAL

    def test_analysis_confidence_bounds(self) -> None:
        """Should enforce confidence bounds 0-1."""
        with pytest.raises(ValidationError):
            CoachAnalysis(confidence=1.5)

        with pytest.raises(ValidationError):
            CoachAnalysis(confidence=-0.1)


# =============================================================================
# CoachHint Tests
# =============================================================================


class TestCoachHint:
    """Tests for CoachHint model."""

    def test_create_coach_hint(self) -> None:
        """Should create hint with required fields."""
        hint = CoachHint(
            level=InterventionLevel.SUGGESTION,
            hint="Try asking a Layer 2 question",
            stage="ASK",
            example_phrase="Why is that important to you?",
            ready_for_next_stage=False,
        )
        assert hint.level == InterventionLevel.SUGGESTION
        assert hint.stage == "ASK"
        assert hint.example_phrase == "Why is that important to you?"
        assert hint.ready_for_next_stage is False

    def test_coach_hint_defaults(self) -> None:
        """Should use defaults for optional fields."""
        hint = CoachHint(
            level=InterventionLevel.INFO,
            hint="Great job!",
            stage="ENGAGE",
        )
        assert hint.example_phrase is None
        assert hint.ready_for_next_stage is False

    def test_coach_hint_requires_fields(self) -> None:
        """Should require level, hint, and stage."""
        with pytest.raises(ValidationError):
            CoachHint(level=InterventionLevel.INFO)  # type: ignore[call-arg]


# =============================================================================
# CoachAudioIntervention Tests
# =============================================================================


class TestCoachAudioIntervention:
    """Tests for CoachAudioIntervention model."""

    def test_create_audio_intervention(self) -> None:
        """Should create intervention with transcript."""
        intervention = CoachAudioIntervention(
            transcript="Let's pause here and think about what the customer really needs.",
        )
        assert "pause" in intervention.transcript
        assert intervention.audio_base64 is None

    def test_audio_intervention_with_audio(self) -> None:
        """Should include audio data when provided."""
        intervention = CoachAudioIntervention(
            transcript="Hold on, let me help you refocus.",
            audio_base64="SGVsbG8gV29ybGQ=",  # Base64 encoded "Hello World"
        )
        assert intervention.audio_base64 is not None

    def test_audio_intervention_requires_transcript(self) -> None:
        """Should require transcript."""
        with pytest.raises(ValidationError):
            CoachAudioIntervention()  # type: ignore[call-arg]
