"""Evaluation models for coach agent scoring and feedback.

This module defines the data structures for post-session evaluations,
including scorecards that break down performance by C.O.R.E. stage
and provide actionable feedback.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Grade(str, Enum):
    """Letter grade for evaluation."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class StageScore(BaseModel):
    """Score breakdown for a single C.O.R.E. stage.

    Each stage has checklist items that are tracked during the session.
    The score is calculated as (completed items / total items) * 100.
    """

    stage: str = Field(..., description="Stage name (CONNECT, OBSERVE, RECOMMEND, EXECUTE)")
    items_completed: list[str] = Field(
        default_factory=list, description="Checklist items completed"
    )
    items_total: list[str] = Field(
        default_factory=list, description="All checklist items for this stage"
    )
    score: float = Field(0.0, ge=0.0, le=100.0, description="Stage score (0-100)")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight for overall score")
    feedback: str | None = Field(None, description="Stage-specific feedback")


class EvaluationScorecard(BaseModel):
    """Complete scorecard with breakdown by stage.

    The overall score is a weighted sum of stage scores plus bonuses/penalties:
    - PBM bonus: up to +10 for high match rate
    - Objection penalty: up to -10 for poor handling
    - Deviation penalty: up to -15 for skipping stages (Evaluation mode only)
    """

    stage_scores: dict[str, StageScore] = Field(
        default_factory=dict, description="Score breakdown per stage"
    )

    # PBM tracking
    pbms_expressed: list[str] = Field(
        default_factory=list, description="PBMs the customer mentioned"
    )
    pbms_acknowledged: list[str] = Field(
        default_factory=list, description="PBMs the salesperson acknowledged"
    )
    pbm_match_rate: float = Field(
        0.0, ge=0.0, le=1.0, description="Ratio of acknowledged to expressed PBMs"
    )
    pbm_bonus: float = Field(0.0, description="Bonus points for PBM handling (0-10)")

    # Objection tracking
    objections_raised: list[str] = Field(
        default_factory=list, description="Objections raised by customer"
    )
    objections_resolved: list[str] = Field(
        default_factory=list, description="Objections successfully handled"
    )
    objection_resolution_rate: float = Field(
        0.0, ge=0.0, le=1.0, description="Ratio of resolved to raised objections"
    )
    objection_penalty: float = Field(
        0.0, le=0.0, description="Penalty for poor objection handling (0 to -10)"
    )

    # Deviation tracking (Evaluation mode)
    deviations: list[str] = Field(default_factory=list, description="C.O.R.E. deviations detected")
    deviation_penalty: float = Field(
        0.0, le=0.0, description="Penalty for stage skipping (0 to -15)"
    )

    # Final scores
    raw_score: float = Field(0.0, ge=0.0, le=100.0, description="Weighted sum of stage scores")
    final_score: float = Field(0.0, description="Raw score + bonuses - penalties (0-100, clamped)")
    grade: Grade = Field(Grade.F, description="Letter grade")


class EvaluationCreate(BaseModel):
    """Input for creating a new evaluation."""

    session_id: str = Field(..., description="Associated session ID")
    user_id: str = Field(..., description="User who was evaluated")
    scorecard: EvaluationScorecard = Field(..., description="Full scorecard")
    summary: str | None = Field(None, description="Natural language summary")
    strengths: list[str] = Field(default_factory=list, description="Things done well")
    improvements: list[str] = Field(default_factory=list, description="Areas for improvement")
    techniques_detected: list[str] = Field(
        default_factory=list, description="C.O.R.E. techniques used"
    )


class Evaluation(BaseModel):
    """Full evaluation document stored in Firestore.

    Created at the end of a session by the coach agent.
    """

    evaluation_id: str = Field(..., description="Unique evaluation ID")
    session_id: str = Field(..., description="Associated session ID")
    user_id: str = Field(..., description="User who was evaluated")

    # Scoring
    scorecard: EvaluationScorecard = Field(..., description="Full scorecard")
    final_score: float = Field(0.0, ge=0.0, le=100.0, description="Final score (0-100)")
    grade: Grade = Field(Grade.F, description="Letter grade")

    # Feedback
    summary: str | None = Field(None, description="Natural language summary")
    strengths: list[str] = Field(default_factory=list, description="Things done well")
    improvements: list[str] = Field(default_factory=list, description="Areas for improvement")
    techniques_detected: list[str] = Field(
        default_factory=list, description="C.O.R.E. techniques used"
    )

    # Timestamps
    created_at: datetime = Field(..., description="When evaluation was created")
    updated_at: datetime = Field(..., description="When evaluation was last updated")


class EvaluationResponse(BaseModel):
    """API response for evaluation data."""

    evaluation_id: str
    session_id: str
    user_id: str
    final_score: float
    grade: Grade
    summary: str | None
    strengths: list[str]
    improvements: list[str]
    created_at: datetime
