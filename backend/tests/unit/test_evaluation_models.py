"""Unit tests for evaluation models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.evaluation import (
    Evaluation,
    EvaluationCreate,
    EvaluationResponse,
    EvaluationScorecard,
    Grade,
    StageScore,
)

# =============================================================================
# StageScore Tests
# =============================================================================


class TestStageScore:
    """Tests for StageScore model."""

    def test_create_valid_stage_score(self) -> None:
        """Should create stage score with valid data."""
        score = StageScore(
            stage="ENGAGE",
            items_completed=["non_business_greet", "established_rapport"],
            items_total=["non_business_greet", "established_rapport", "manager_mention"],
            score=66.67,
            weight=0.15,
            feedback="Good rapport building.",
        )
        assert score.stage == "ENGAGE"
        assert len(score.items_completed) == 2
        assert score.score == 66.67
        assert score.weight == 0.15

    def test_stage_score_defaults(self) -> None:
        """Should use default values when not provided."""
        score = StageScore(stage="ASK", weight=0.30)
        assert score.items_completed == []
        assert score.items_total == []
        assert score.score == 0.0
        assert score.feedback is None

    def test_stage_score_score_bounds(self) -> None:
        """Should enforce score bounds 0-100."""
        with pytest.raises(ValidationError):
            StageScore(stage="SHOW", weight=0.30, score=101.0)

        with pytest.raises(ValidationError):
            StageScore(stage="SHOW", weight=0.30, score=-1.0)

    def test_stage_score_weight_bounds(self) -> None:
        """Should enforce weight bounds 0-1."""
        with pytest.raises(ValidationError):
            StageScore(stage="YES", weight=1.5, score=50.0)

        with pytest.raises(ValidationError):
            StageScore(stage="YES", weight=-0.1, score=50.0)


# =============================================================================
# EvaluationScorecard Tests
# =============================================================================


class TestEvaluationScorecard:
    """Tests for EvaluationScorecard model."""

    def test_create_empty_scorecard(self) -> None:
        """Should create scorecard with defaults."""
        scorecard = EvaluationScorecard()
        assert scorecard.stage_scores == {}
        assert scorecard.pbms_expressed == []
        assert scorecard.pbms_acknowledged == []
        assert scorecard.pbm_match_rate == 0.0
        assert scorecard.final_score == 0.0
        assert scorecard.grade == Grade.F

    def test_create_full_scorecard(self) -> None:
        """Should create scorecard with all fields."""
        engage_score = StageScore(
            stage="ENGAGE",
            items_completed=["non_business_greet"],
            items_total=["non_business_greet", "established_rapport", "manager_mention"],
            score=33.33,
            weight=0.15,
        )
        scorecard = EvaluationScorecard(
            stage_scores={"ENGAGE": engage_score},
            pbms_expressed=["durability", "style"],
            pbms_acknowledged=["durability"],
            pbm_match_rate=0.5,
            pbm_bonus=5.0,
            objections_raised=["need to think about it"],
            objections_resolved=["need to think about it"],
            objection_resolution_rate=1.0,
            objection_penalty=0.0,
            deviations=[],
            deviation_penalty=0.0,
            raw_score=75.0,
            final_score=80.0,
            grade=Grade.B,
        )
        assert "ENGAGE" in scorecard.stage_scores
        assert scorecard.pbm_bonus == 5.0
        assert scorecard.grade == Grade.B

    def test_scorecard_penalty_constraints(self) -> None:
        """Should enforce penalties are <= 0."""
        with pytest.raises(ValidationError):
            EvaluationScorecard(objection_penalty=5.0)

        with pytest.raises(ValidationError):
            EvaluationScorecard(deviation_penalty=10.0)

    def test_scorecard_with_deviations(self) -> None:
        """Should track deviations and penalties."""
        scorecard = EvaluationScorecard(
            deviations=["skipped_critical_questions", "pushed_product_too_early"],
            deviation_penalty=-10.0,
            raw_score=70.0,
            final_score=60.0,
            grade=Grade.D,
        )
        assert len(scorecard.deviations) == 2
        assert scorecard.deviation_penalty == -10.0


# =============================================================================
# Grade Tests
# =============================================================================


class TestGrade:
    """Tests for Grade enum."""

    def test_grade_values(self) -> None:
        """Should have correct grade values."""
        assert Grade.A.value == "A"
        assert Grade.B.value == "B"
        assert Grade.C.value == "C"
        assert Grade.D.value == "D"
        assert Grade.F.value == "F"

    def test_grade_from_string(self) -> None:
        """Should create grade from string."""
        assert Grade("A") == Grade.A
        assert Grade("F") == Grade.F


# =============================================================================
# EvaluationCreate Tests
# =============================================================================


class TestEvaluationCreate:
    """Tests for EvaluationCreate model."""

    def test_create_minimal_evaluation(self) -> None:
        """Should create evaluation with required fields only."""
        scorecard = EvaluationScorecard()
        create = EvaluationCreate(
            session_id="session-123",
            user_id="user-456",
            scorecard=scorecard,
        )
        assert create.session_id == "session-123"
        assert create.user_id == "user-456"
        assert create.summary is None
        assert create.strengths == []
        assert create.improvements == []

    def test_create_full_evaluation(self) -> None:
        """Should create evaluation with all fields."""
        scorecard = EvaluationScorecard(
            raw_score=85.0,
            final_score=90.0,
            grade=Grade.A,
        )
        create = EvaluationCreate(
            session_id="session-123",
            user_id="user-456",
            scorecard=scorecard,
            summary="Excellent performance with strong rapport building.",
            strengths=["Great greeting", "Good discovery questions"],
            improvements=["Could mention protection plan earlier"],
            techniques_detected=["non_business_greet", "layer2_discovery"],
        )
        assert create.summary is not None
        assert len(create.strengths) == 2
        assert len(create.techniques_detected) == 2


# =============================================================================
# Evaluation Tests
# =============================================================================


class TestEvaluation:
    """Tests for Evaluation model."""

    def test_create_full_evaluation(self) -> None:
        """Should create full evaluation model."""
        now = datetime.now(UTC)
        scorecard = EvaluationScorecard(
            raw_score=75.0,
            final_score=78.0,
            grade=Grade.C,
        )
        evaluation = Evaluation(
            evaluation_id="eval-001",
            session_id="session-123",
            user_id="user-456",
            scorecard=scorecard,
            final_score=78.0,
            grade=Grade.C,
            summary="Solid performance with room for improvement.",
            strengths=["Good questions"],
            improvements=["Work on closing"],
            techniques_detected=["critical_questions"],
            created_at=now,
            updated_at=now,
        )
        assert evaluation.evaluation_id == "eval-001"
        assert evaluation.final_score == 78.0
        assert evaluation.grade == Grade.C

    def test_evaluation_defaults(self) -> None:
        """Should use defaults for optional fields."""
        now = datetime.now(UTC)
        scorecard = EvaluationScorecard()
        evaluation = Evaluation(
            evaluation_id="eval-002",
            session_id="session-456",
            user_id="user-789",
            scorecard=scorecard,
            created_at=now,
            updated_at=now,
        )
        assert evaluation.final_score == 0.0
        assert evaluation.grade == Grade.F
        assert evaluation.summary is None
        assert evaluation.strengths == []


# =============================================================================
# EvaluationResponse Tests
# =============================================================================


class TestEvaluationResponse:
    """Tests for EvaluationResponse model."""

    def test_create_response(self) -> None:
        """Should create API response model."""
        now = datetime.now(UTC)
        response = EvaluationResponse(
            evaluation_id="eval-001",
            session_id="session-123",
            user_id="user-456",
            final_score=85.0,
            grade=Grade.B,
            summary="Good session.",
            strengths=["Strong opening"],
            improvements=["Close faster"],
            created_at=now,
        )
        assert response.evaluation_id == "eval-001"
        assert response.final_score == 85.0
        assert response.grade == Grade.B
