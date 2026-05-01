"""Unit tests for coach agent scorer module."""

from app.agents.coach.scorer import (
    GRADE_THRESHOLDS,
    STAGE_WEIGHTS,
    calculate_deviation_penalty,
    calculate_grade,
    calculate_objection_penalty,
    calculate_pbm_bonus,
    calculate_score,
    calculate_stage_score,
)
from app.agents.state import CoreStageProgress, SalesStage
from app.models.evaluation import Grade

# =============================================================================
# Stage Score Tests
# =============================================================================


class TestCalculateStageScore:
    """Tests for calculate_stage_score function."""

    def test_full_completion(self) -> None:
        """Should return 100 when all items completed."""
        items_total = ["item1", "item2", "item3"]
        items_completed = ["item1", "item2", "item3"]
        score = calculate_stage_score(items_completed, items_total)
        assert score == 100.0

    def test_partial_completion(self) -> None:
        """Should return proportional score for partial completion."""
        items_total = ["item1", "item2", "item3"]
        items_completed = ["item1"]
        score = calculate_stage_score(items_completed, items_total)
        assert abs(score - 33.33) < 0.1

    def test_no_completion(self) -> None:
        """Should return 0 when no items completed."""
        items_total = ["item1", "item2", "item3"]
        items_completed: list[str] = []
        score = calculate_stage_score(items_completed, items_total)
        assert score == 0.0

    def test_empty_total(self) -> None:
        """Should return 0 when no items in total."""
        items_total: list[str] = []
        items_completed: list[str] = []
        score = calculate_stage_score(items_completed, items_total)
        assert score == 0.0

    def test_ignores_invalid_completed_items(self) -> None:
        """Should ignore items not in total list."""
        items_total = ["item1", "item2"]
        items_completed = ["item1", "invalid_item"]
        score = calculate_stage_score(items_completed, items_total)
        assert score == 50.0


# =============================================================================
# PBM Bonus Tests
# =============================================================================


class TestCalculatePbmBonus:
    """Tests for calculate_pbm_bonus function."""

    def test_full_match_gives_full_bonus(self) -> None:
        """Should give full bonus when all motivators acknowledged."""
        pbms_expressed = ["value", "quality"]
        pbms_acknowledged = ["value", "quality"]
        bonus = calculate_pbm_bonus(pbms_expressed, pbms_acknowledged)
        assert bonus == 10.0

    def test_half_match_gives_proportional_bonus(self) -> None:
        """Should give proportional bonus for partial match."""
        pbms_expressed = ["value", "quality"]
        pbms_acknowledged = ["value"]
        bonus = calculate_pbm_bonus(pbms_expressed, pbms_acknowledged)
        assert bonus == 5.0  # 50% match = 50% of max bonus

    def test_no_match_gives_reduced_bonus(self) -> None:
        """Should give reduced bonus for low match rate."""
        pbms_expressed = ["value", "quality", "convenience", "security"]
        pbms_acknowledged = ["value"]
        bonus = calculate_pbm_bonus(pbms_expressed, pbms_acknowledged)
        assert bonus < 2.5  # 25% match = reduced bonus

    def test_no_pbms_expressed_gives_zero(self) -> None:
        """Should return 0 when no motivators expressed."""
        pbms_expressed: list[str] = []
        pbms_acknowledged = ["value"]
        bonus = calculate_pbm_bonus(pbms_expressed, pbms_acknowledged)
        assert bonus == 0.0

    def test_extra_acknowledged_pbms_ok(self) -> None:
        """Should handle extra acknowledged motivators gracefully."""
        pbms_expressed = ["value"]
        pbms_acknowledged = ["value", "quality", "convenience"]
        bonus = calculate_pbm_bonus(pbms_expressed, pbms_acknowledged)
        assert bonus == 10.0  # Full match on expressed


# =============================================================================
# Objection Penalty Tests
# =============================================================================


class TestCalculateObjectionPenalty:
    """Tests for calculate_objection_penalty function."""

    def test_all_resolved_no_penalty(self) -> None:
        """Should give no penalty when all objections resolved."""
        objections_raised = ["price", "timing"]
        objections_resolved = ["price", "timing"]
        penalty = calculate_objection_penalty(objections_raised, objections_resolved)
        assert penalty == 0.0

    def test_half_resolved_no_penalty(self) -> None:
        """Should give no penalty at 50% resolution threshold."""
        objections_raised = ["price", "timing"]
        objections_resolved = ["price"]
        penalty = calculate_objection_penalty(objections_raised, objections_resolved)
        assert penalty == 0.0

    def test_below_threshold_gives_penalty(self) -> None:
        """Should give penalty below 50% resolution."""
        objections_raised = ["price", "timing", "quality", "delivery"]
        objections_resolved = ["price"]  # 25% resolution
        penalty = calculate_objection_penalty(objections_raised, objections_resolved)
        assert penalty < 0.0
        assert penalty >= -10.0

    def test_no_objections_no_penalty(self) -> None:
        """Should give no penalty when no objections raised."""
        objections_raised: list[str] = []
        objections_resolved: list[str] = []
        penalty = calculate_objection_penalty(objections_raised, objections_resolved)
        assert penalty == 0.0


# =============================================================================
# Deviation Penalty Tests
# =============================================================================


class TestCalculateDeviationPenalty:
    """Tests for calculate_deviation_penalty function."""

    def test_no_deviations_no_penalty(self) -> None:
        """Should give no penalty when no deviations."""
        deviations: list[str] = []
        penalty = calculate_deviation_penalty(deviations)
        assert penalty == 0.0

    def test_one_deviation_gives_penalty(self) -> None:
        """Should give -5 penalty for one deviation."""
        deviations = ["skipped_observe"]
        penalty = calculate_deviation_penalty(deviations)
        assert penalty == -5.0

    def test_multiple_deviations_capped(self) -> None:
        """Should cap penalty at -15."""
        deviations = ["skipped_connect", "skipped_observe", "recommended_too_early", "no_motivator_connection"]
        penalty = calculate_deviation_penalty(deviations)
        assert penalty == -15.0


# =============================================================================
# Grade Tests
# =============================================================================


class TestCalculateGrade:
    """Tests for calculate_grade function."""

    def test_grade_a(self) -> None:
        """Should return A for 90+."""
        assert calculate_grade(95.0) == Grade.A
        assert calculate_grade(90.0) == Grade.A

    def test_grade_b(self) -> None:
        """Should return B for 80-89."""
        assert calculate_grade(89.0) == Grade.B
        assert calculate_grade(80.0) == Grade.B

    def test_grade_c(self) -> None:
        """Should return C for 70-79."""
        assert calculate_grade(79.0) == Grade.C
        assert calculate_grade(70.0) == Grade.C

    def test_grade_d(self) -> None:
        """Should return D for 60-69."""
        assert calculate_grade(69.0) == Grade.D
        assert calculate_grade(60.0) == Grade.D

    def test_grade_f(self) -> None:
        """Should return F for below 60."""
        assert calculate_grade(59.0) == Grade.F
        assert calculate_grade(0.0) == Grade.F


# =============================================================================
# Full Score Calculation Tests
# =============================================================================


class TestCalculateScore:
    """Tests for calculate_score function."""

    def test_perfect_score(self) -> None:
        """Should calculate perfect score with all items complete."""
        progress = CoreStageProgress(
            current_stage=SalesStage.COMPLETE,
            connect={
                "warm_greeting": True,
                "establish_credibility": True,
                "create_comfort": True,
            },
            observe={
                "needs_discovery": True,
                "goal_identification": True,
                "motivator_mapping": True,
            },
            recommend={
                "solution_presentation": True,
                "value_connection": True,
                "risk_mitigation": True,
            },
            execute={
                "commitment_request": True,
                "objection_handling": True,
                "finalize_agreement": True,
            },
            pbms_expressed=["value", "quality"],
            pbms_acknowledged=["value", "quality"],
        )

        raw_score, final_score, grade = calculate_score(progress)

        assert raw_score == 100.0
        assert final_score >= 100.0  # Could be higher with motivator bonus, clamped
        assert grade == Grade.A

    def test_zero_score(self) -> None:
        """Should calculate zero score with no items complete."""
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

        raw_score, final_score, grade = calculate_score(progress)

        assert raw_score == 0.0
        assert final_score == 0.0
        assert grade == Grade.F

    def test_score_with_deviations(self) -> None:
        """Should apply deviation penalties."""
        progress = CoreStageProgress(
            current_stage=SalesStage.RECOMMEND,
            connect={
                "warm_greeting": True,
                "establish_credibility": True,
                "create_comfort": True,
            },
            observe={
                "needs_discovery": False,
                "goal_identification": False,
                "motivator_mapping": False,
            },
            recommend={
                "solution_presentation": True,
                "value_connection": False,
                "risk_mitigation": False,
            },
            execute={
                "commitment_request": False,
                "objection_handling": False,
                "finalize_agreement": False,
            },
        )

        deviations = ["skipped_observe"]
        raw_score, final_score, grade = calculate_score(progress, deviations=deviations)

        # Raw score should be positive (CONNECT complete = 15%)
        assert raw_score > 0
        # Final score should be lower due to penalty
        assert final_score < raw_score

    def test_score_clamped_to_bounds(self) -> None:
        """Should clamp final score to 0-100."""
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

        # Many deviations should not go below 0
        deviations = ["d1", "d2", "d3", "d4", "d5"]
        raw_score, final_score, grade = calculate_score(progress, deviations=deviations)

        assert final_score >= 0.0
        assert final_score <= 100.0


# =============================================================================
# Constants Tests
# =============================================================================


class TestScorerConstants:
    """Tests for scorer constants."""

    def test_stage_weights_sum_to_one(self) -> None:
        """Stage weights should sum to 1.0."""
        total = sum(STAGE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_grade_thresholds_ordered(self) -> None:
        """Grade thresholds should be in descending order."""
        assert GRADE_THRESHOLDS[Grade.A] > GRADE_THRESHOLDS[Grade.B]
        assert GRADE_THRESHOLDS[Grade.B] > GRADE_THRESHOLDS[Grade.C]
        assert GRADE_THRESHOLDS[Grade.C] > GRADE_THRESHOLDS[Grade.D]
        assert GRADE_THRESHOLDS[Grade.D] > GRADE_THRESHOLDS[Grade.F]
