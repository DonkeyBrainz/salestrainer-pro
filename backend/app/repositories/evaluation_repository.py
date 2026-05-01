"""Repository for evaluation data access."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.models.evaluation import (
    Evaluation,
    EvaluationCreate,
    EvaluationScorecard,
    Grade,
    StageScore,
)
from app.repositories.base import BaseRepository


class EvaluationRepository(BaseRepository):
    """Repository for evaluation data access."""

    _collection_name = "evaluations"

    async def create(self, evaluation_create: EvaluationCreate) -> Evaluation:
        """Create new evaluation."""
        evaluation_id = str(uuid4())
        now = datetime.now(UTC)

        evaluation_data = {
            "evaluation_id": evaluation_id,
            "session_id": evaluation_create.session_id,
            "user_id": evaluation_create.user_id,
            "scorecard": self._scorecard_to_dict(evaluation_create.scorecard),
            "final_score": evaluation_create.scorecard.final_score,
            "grade": evaluation_create.scorecard.grade.value,
            "summary": evaluation_create.summary,
            "strengths": evaluation_create.strengths,
            "improvements": evaluation_create.improvements,
            "techniques_detected": evaluation_create.techniques_detected,
            "created_at": now,
            "updated_at": now,
        }

        await self.collection.document(evaluation_id).set(evaluation_data)
        return self._doc_to_evaluation(evaluation_id, evaluation_data)

    async def get_by_id(self, evaluation_id: str) -> Evaluation | None:
        """Get evaluation by ID."""
        doc = await self.collection.document(evaluation_id).get()
        if not doc.exists:
            return None

        return self._doc_to_evaluation(evaluation_id, doc.to_dict())

    async def get_by_session_id(self, session_id: str) -> Evaluation | None:
        """Get evaluation for a specific session."""
        query = self.collection.where("session_id", "==", session_id).limit(1)
        docs = await query.get()

        if not docs:
            return None

        doc = docs[0]
        return self._doc_to_evaluation(doc.id, doc.to_dict())

    async def list_by_user(self, user_id: str, limit: int = 50) -> list[Evaluation]:
        """List evaluations for user."""
        query = (
            self.collection.where("user_id", "==", user_id)
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
        )

        docs = await query.get()
        return [self._doc_to_evaluation(doc.id, doc.to_dict()) for doc in docs]

    def _scorecard_to_dict(self, scorecard: EvaluationScorecard) -> dict[str, Any]:
        """Convert scorecard to Firestore-compatible dict."""
        stage_scores_dict = {}
        for stage_name, stage_score in scorecard.stage_scores.items():
            stage_scores_dict[stage_name] = {
                "stage": stage_score.stage,
                "items_completed": stage_score.items_completed,
                "items_total": stage_score.items_total,
                "score": stage_score.score,
                "weight": stage_score.weight,
                "feedback": stage_score.feedback,
            }

        return {
            "stage_scores": stage_scores_dict,
            "pbms_expressed": scorecard.pbms_expressed,
            "pbms_acknowledged": scorecard.pbms_acknowledged,
            "pbm_match_rate": scorecard.pbm_match_rate,
            "pbm_bonus": scorecard.pbm_bonus,
            "objections_raised": scorecard.objections_raised,
            "objections_resolved": scorecard.objections_resolved,
            "objection_resolution_rate": scorecard.objection_resolution_rate,
            "objection_penalty": scorecard.objection_penalty,
            "deviations": scorecard.deviations,
            "deviation_penalty": scorecard.deviation_penalty,
            "raw_score": scorecard.raw_score,
            "final_score": scorecard.final_score,
            "grade": scorecard.grade.value,
        }

    def _dict_to_scorecard(self, data: dict[str, Any]) -> EvaluationScorecard:
        """Convert Firestore dict to scorecard model."""
        stage_scores = {}
        for stage_name, stage_data in data.get("stage_scores", {}).items():
            stage_scores[stage_name] = StageScore(
                stage=stage_data["stage"],
                items_completed=stage_data.get("items_completed", []),
                items_total=stage_data.get("items_total", []),
                score=stage_data.get("score", 0.0),
                weight=stage_data.get("weight", 0.25),
                feedback=stage_data.get("feedback"),
            )

        return EvaluationScorecard(
            stage_scores=stage_scores,
            pbms_expressed=data.get("pbms_expressed", []),
            pbms_acknowledged=data.get("pbms_acknowledged", []),
            pbm_match_rate=data.get("pbm_match_rate", 0.0),
            pbm_bonus=data.get("pbm_bonus", 0.0),
            objections_raised=data.get("objections_raised", []),
            objections_resolved=data.get("objections_resolved", []),
            objection_resolution_rate=data.get("objection_resolution_rate", 0.0),
            objection_penalty=data.get("objection_penalty", 0.0),
            deviations=data.get("deviations", []),
            deviation_penalty=data.get("deviation_penalty", 0.0),
            raw_score=data.get("raw_score", 0.0),
            final_score=data.get("final_score", 0.0),
            grade=Grade(data.get("grade", "F")),
        )

    def _doc_to_evaluation(self, doc_id: str, data: dict[str, Any]) -> Evaluation:
        """Convert Firestore document to Evaluation model."""
        scorecard = self._dict_to_scorecard(data.get("scorecard", {}))

        return Evaluation(
            evaluation_id=doc_id,
            session_id=data["session_id"],
            user_id=data["user_id"],
            scorecard=scorecard,
            final_score=data.get("final_score", 0.0),
            grade=Grade(data.get("grade", "F")),
            summary=data.get("summary"),
            strengths=data.get("strengths", []),
            improvements=data.get("improvements", []),
            techniques_detected=data.get("techniques_detected", []),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
