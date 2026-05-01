"""Unit tests for coach agent hints module."""

from app.agents.coach.hints import (
    DEVIATION_MESSAGES,
    HINT_TEMPLATES,
    TECHNIQUE_MESSAGES,
    get_hint_for_stage,
    get_intervention_message,
    get_stage_checklist_items,
)
from app.models.coach import InterventionLevel

# =============================================================================
# Hint Templates Tests
# =============================================================================


class TestHintTemplates:
    """Tests for hint template structure."""

    def test_all_stages_have_templates(self) -> None:
        """Should have templates for all C.O.R.E. stages."""
        assert "CONNECT" in HINT_TEMPLATES
        assert "OBSERVE" in HINT_TEMPLATES
        assert "RECOMMEND" in HINT_TEMPLATES
        assert "EXECUTE" in HINT_TEMPLATES

    def test_all_levels_have_hints(self) -> None:
        """Each stage should have hints for all intervention levels."""
        for stage in ["CONNECT", "OBSERVE", "RECOMMEND", "EXECUTE"]:
            stage_hints = HINT_TEMPLATES[stage]
            assert InterventionLevel.INFO in stage_hints
            assert InterventionLevel.SUGGESTION in stage_hints
            assert InterventionLevel.WARNING in stage_hints
            assert InterventionLevel.CRITICAL in stage_hints

    def test_hints_are_non_empty(self) -> None:
        """All hint lists should have at least one hint."""
        for stage, levels in HINT_TEMPLATES.items():
            for level, hints in levels.items():
                assert len(hints) > 0, f"No hints for {stage}/{level}"


# =============================================================================
# Get Hint For Stage Tests
# =============================================================================


class TestGetHintForStage:
    """Tests for get_hint_for_stage function."""

    def test_returns_hint_for_valid_stage(self) -> None:
        """Should return a hint for valid stage and level."""
        hint = get_hint_for_stage("CONNECT", InterventionLevel.INFO)
        assert hint is not None
        assert len(hint) > 0

    def test_handles_lowercase_stage(self) -> None:
        """Should handle lowercase stage names."""
        hint = get_hint_for_stage("connect", InterventionLevel.SUGGESTION)
        assert hint is not None

    def test_returns_fallback_for_invalid_stage(self) -> None:
        """Should return fallback hint for invalid stage."""
        hint = get_hint_for_stage("INVALID", InterventionLevel.INFO)
        assert "C.O.R.E." in hint

    def test_cycles_through_hints(self) -> None:
        """Should cycle through hints using index."""
        hint0 = get_hint_for_stage("OBSERVE", InterventionLevel.INFO, index=0)
        hint1 = get_hint_for_stage("OBSERVE", InterventionLevel.INFO, index=1)
        # May or may not be different depending on template count
        assert hint0 is not None
        assert hint1 is not None


# =============================================================================
# Get Intervention Message Tests
# =============================================================================


class TestGetInterventionMessage:
    """Tests for get_intervention_message function."""

    def test_uses_technique_message_for_info(self) -> None:
        """Should use technique message for INFO level with technique."""
        msg = get_intervention_message(
            level=InterventionLevel.INFO,
            stage="CONNECT",
            technique="warm_greeting",
        )
        assert msg == TECHNIQUE_MESSAGES["warm_greeting"]

    def test_uses_deviation_message_for_warning(self) -> None:
        """Should use deviation message for WARNING level."""
        msg = get_intervention_message(
            level=InterventionLevel.WARNING,
            stage="OBSERVE",
            deviation="missed_needs_discovery",
        )
        assert msg == DEVIATION_MESSAGES["missed_needs_discovery"]

    def test_falls_back_to_stage_hint(self) -> None:
        """Should fall back to stage hint when no specific message."""
        msg = get_intervention_message(
            level=InterventionLevel.SUGGESTION,
            stage="RECOMMEND",
        )
        assert msg is not None
        assert len(msg) > 0

    def test_handles_unknown_technique(self) -> None:
        """Should fall back when technique not in messages."""
        msg = get_intervention_message(
            level=InterventionLevel.INFO,
            stage="CONNECT",
            technique="unknown_technique",
        )
        # Should fall back to stage hint
        assert msg is not None


# =============================================================================
# Deviation Messages Tests
# =============================================================================


class TestDeviationMessages:
    """Tests for deviation message templates."""

    def test_all_deviations_have_messages(self) -> None:
        """Should have messages for all expected deviations."""
        expected_deviations = [
            "skipped_connect",
            "skipped_observe",
            "missed_needs_discovery",
            "recommended_too_early",
            "no_motivator_connection",
            "missed_objection",
            "no_commitment_ask",
            "no_next_steps",
        ]
        for deviation in expected_deviations:
            assert deviation in DEVIATION_MESSAGES


# =============================================================================
# Technique Messages Tests
# =============================================================================


class TestTechniqueMessages:
    """Tests for technique message templates."""

    def test_all_techniques_have_messages(self) -> None:
        """Should have messages for all stage techniques."""
        expected_techniques = [
            # CONNECT
            "warm_greeting",
            "establish_credibility",
            "create_comfort",
            # OBSERVE
            "needs_discovery",
            "goal_identification",
            "motivator_mapping",
            # RECOMMEND
            "solution_presentation",
            "value_connection",
            "risk_mitigation",
            # EXECUTE
            "commitment_request",
            "objection_handling",
            "finalize_agreement",
        ]
        for technique in expected_techniques:
            assert technique in TECHNIQUE_MESSAGES


# =============================================================================
# Stage Checklist Items Tests
# =============================================================================


class TestGetStageChecklistItems:
    """Tests for get_stage_checklist_items function."""

    def test_connect_items(self) -> None:
        """Should return correct CONNECT items."""
        items = get_stage_checklist_items("CONNECT")
        assert "warm_greeting" in items
        assert "establish_credibility" in items
        assert "create_comfort" in items
        assert len(items) == 3

    def test_observe_items(self) -> None:
        """Should return correct OBSERVE items."""
        items = get_stage_checklist_items("OBSERVE")
        assert "needs_discovery" in items
        assert "goal_identification" in items
        assert "motivator_mapping" in items
        assert len(items) == 3

    def test_recommend_items(self) -> None:
        """Should return correct RECOMMEND items."""
        items = get_stage_checklist_items("RECOMMEND")
        assert "solution_presentation" in items
        assert "value_connection" in items
        assert "risk_mitigation" in items
        assert len(items) == 3

    def test_execute_items(self) -> None:
        """Should return correct EXECUTE items."""
        items = get_stage_checklist_items("EXECUTE")
        assert "commitment_request" in items
        assert "objection_handling" in items
        assert "finalize_agreement" in items
        assert len(items) == 3

    def test_handles_lowercase(self) -> None:
        """Should handle lowercase stage names."""
        items = get_stage_checklist_items("connect")
        assert len(items) == 3

    def test_returns_empty_for_invalid(self) -> None:
        """Should return empty list for invalid stage."""
        items = get_stage_checklist_items("INVALID")
        assert items == []
