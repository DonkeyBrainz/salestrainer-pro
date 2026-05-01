"""Unit tests for EvaluationRepository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.evaluation import (
    EvaluationCreate,
    EvaluationScorecard,
    Grade,
    StageScore,
)
from app.repositories.evaluation_repository import EvaluationRepository


@pytest.fixture
def mock_firestore_client() -> MagicMock:
    """Create a mock Firestore client.

    Uses MagicMock because collection() is synchronous.
    Only get/set/update calls are async.
    """
    return MagicMock()


@pytest.fixture
def evaluation_repository(mock_firestore_client: MagicMock) -> EvaluationRepository:
    """Create EvaluationRepository with mocked Firestore client."""
    return EvaluationRepository(db=mock_firestore_client)


@pytest.fixture
def sample_scorecard() -> EvaluationScorecard:
    """Sample scorecard for testing."""
    return EvaluationScorecard(
        stage_scores={
            "ENGAGE": StageScore(
                stage="ENGAGE",
                items_completed=["non_business_greet"],
                items_total=["non_business_greet", "established_rapport", "manager_mention"],
                score=33.33,
                weight=0.15,
                feedback="Good start.",
            ),
        },
        pbms_expressed=["durability"],
        pbms_acknowledged=["durability"],
        pbm_match_rate=1.0,
        pbm_bonus=10.0,
        objections_raised=["need to think about it"],
        objections_resolved=["need to think about it"],
        objection_resolution_rate=1.0,
        objection_penalty=0.0,
        deviations=[],
        deviation_penalty=0.0,
        raw_score=75.0,
        final_score=85.0,
        grade=Grade.B,
    )


@pytest.fixture
def sample_evaluation_data() -> dict:
    """Sample evaluation document data from Firestore."""
    return {
        "session_id": "session-123",
        "user_id": "user-456",
        "scorecard": {
            "stage_scores": {
                "ENGAGE": {
                    "stage": "ENGAGE",
                    "items_completed": ["non_business_greet"],
                    "items_total": [
                        "non_business_greet",
                        "established_rapport",
                        "manager_mention",
                    ],
                    "score": 33.33,
                    "weight": 0.15,
                    "feedback": "Good start.",
                },
            },
            "pbms_expressed": ["durability"],
            "pbms_acknowledged": ["durability"],
            "pbm_match_rate": 1.0,
            "pbm_bonus": 10.0,
            "objections_raised": ["need to think about it"],
            "objections_resolved": ["need to think about it"],
            "objection_resolution_rate": 1.0,
            "objection_penalty": 0.0,
            "deviations": [],
            "deviation_penalty": 0.0,
            "raw_score": 75.0,
            "final_score": 85.0,
            "grade": "B",
        },
        "final_score": 85.0,
        "grade": "B",
        "summary": "Good session with strong opening.",
        "strengths": ["Good greeting"],
        "improvements": ["Work on closing"],
        "techniques_detected": ["non_business_greet"],
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }


# =============================================================================
# Create Tests
# =============================================================================


class TestCreate:
    """Tests for create method."""

    async def test_creates_evaluation_with_id(
        self,
        evaluation_repository: EvaluationRepository,
        mock_firestore_client: MagicMock,
        sample_scorecard: EvaluationScorecard,
    ) -> None:
        """Should create evaluation with generated UUID."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        evaluation_create = EvaluationCreate(
            session_id="session-123",
            user_id="user-456",
            scorecard=sample_scorecard,
            summary="Good performance.",
            strengths=["Strong opening"],
            improvements=["Close faster"],
            techniques_detected=["non_business_greet"],
        )

        result = await evaluation_repository.create(evaluation_create)

        assert result.evaluation_id is not None
        assert result.session_id == "session-123"
        assert result.user_id == "user-456"
        assert result.final_score == 85.0
        assert result.grade == Grade.B
        mock_firestore_client.collection.assert_called_with("evaluations")

    async def test_sets_timestamps(
        self,
        evaluation_repository: EvaluationRepository,
        mock_firestore_client: MagicMock,
        sample_scorecard: EvaluationScorecard,
    ) -> None:
        """Should set created_at and updated_at to current time."""
        mock_firestore_client.collection.return_value.document.return_value.set = AsyncMock()

        evaluation_create = EvaluationCreate(
            session_id="session-123",
            user_id="user-456",
            scorecard=sample_scorecard,
        )

        result = await evaluation_repository.create(evaluation_create)

        assert result.created_at is not None
        assert result.updated_at is not None

    async def test_saves_scorecard_data(
        self,
        evaluation_repository: EvaluationRepository,
        mock_firestore_client: MagicMock,
        sample_scorecard: EvaluationScorecard,
    ) -> None:
        """Should save full scorecard data."""
        mock_set = AsyncMock()
        mock_firestore_client.collection.return_value.document.return_value.set = mock_set

        evaluation_create = EvaluationCreate(
            session_id="session-123",
            user_id="user-456",
            scorecard=sample_scorecard,
        )

        result = await evaluation_repository.create(evaluation_create)

        # Verify scorecard is properly converted
        assert result.scorecard.pbm_match_rate == 1.0
        assert result.scorecard.pbm_bonus == 10.0
        assert "ENGAGE" in result.scorecard.stage_scores


# =============================================================================
# GetById Tests
# =============================================================================


class TestGetById:
    """Tests for get_by_id method."""

    async def test_returns_evaluation_when_exists(
        self,
        evaluation_repository: EvaluationRepository,
        mock_firestore_client: MagicMock,
        sample_evaluation_data: dict,
    ) -> None:
        """Should return Evaluation when document exists."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "eval-123"
        mock_doc.to_dict.return_value = sample_evaluation_data

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await evaluation_repository.get_by_id("eval-123")

        assert result is not None
        assert result.evaluation_id == "eval-123"
        assert result.session_id == "session-123"
        assert result.grade == Grade.B

    async def test_returns_none_when_not_exists(
        self,
        evaluation_repository: EvaluationRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return None when document doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_firestore_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=mock_doc
        )

        result = await evaluation_repository.get_by_id("nonexistent-id")

        assert result is None


# =============================================================================
# GetBySessionId Tests
# =============================================================================


class TestGetBySessionId:
    """Tests for get_by_session_id method."""

    async def test_returns_evaluation_for_session(
        self,
        evaluation_repository: EvaluationRepository,
        mock_firestore_client: MagicMock,
        sample_evaluation_data: dict,
    ) -> None:
        """Should return evaluation for session."""
        mock_doc = MagicMock()
        mock_doc.id = "eval-123"
        mock_doc.to_dict.return_value = sample_evaluation_data

        mock_query = MagicMock()
        mock_query.get = AsyncMock(return_value=[mock_doc])
        mock_firestore_client.collection.return_value.where.return_value.limit.return_value = (
            mock_query
        )

        result = await evaluation_repository.get_by_session_id("session-123")

        assert result is not None
        assert result.session_id == "session-123"

    async def test_returns_none_when_no_evaluation(
        self,
        evaluation_repository: EvaluationRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return None when session has no evaluation."""
        mock_query = MagicMock()
        mock_query.get = AsyncMock(return_value=[])
        mock_firestore_client.collection.return_value.where.return_value.limit.return_value = (
            mock_query
        )

        result = await evaluation_repository.get_by_session_id("no-eval-session")

        assert result is None


# =============================================================================
# ListByUser Tests
# =============================================================================


class TestListByUser:
    """Tests for list_by_user method."""

    async def test_returns_user_evaluations(
        self,
        evaluation_repository: EvaluationRepository,
        mock_firestore_client: MagicMock,
        sample_evaluation_data: dict,
    ) -> None:
        """Should return list of user's evaluations."""
        mock_doc = MagicMock()
        mock_doc.id = "eval-123"
        mock_doc.to_dict.return_value = sample_evaluation_data

        mock_query = MagicMock()
        mock_query.get = AsyncMock(return_value=[mock_doc])
        (
            mock_firestore_client.collection.return_value.where.return_value.order_by.return_value.limit.return_value
        ) = mock_query

        result = await evaluation_repository.list_by_user("user-456")

        assert len(result) == 1
        assert result[0].user_id == "user-456"

    async def test_returns_empty_list_when_no_evaluations(
        self,
        evaluation_repository: EvaluationRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return empty list when user has no evaluations."""
        mock_query = MagicMock()
        mock_query.get = AsyncMock(return_value=[])
        (
            mock_firestore_client.collection.return_value.where.return_value.order_by.return_value.limit.return_value
        ) = mock_query

        result = await evaluation_repository.list_by_user("user-no-evals")

        assert result == []

    async def test_respects_limit_parameter(
        self,
        evaluation_repository: EvaluationRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should apply limit to query."""
        mock_query = MagicMock()
        mock_query.get = AsyncMock(return_value=[])
        mock_limit = MagicMock(return_value=mock_query)
        (
            mock_firestore_client.collection.return_value.where.return_value.order_by.return_value.limit
        ) = mock_limit

        await evaluation_repository.list_by_user("user-456", limit=10)

        mock_limit.assert_called_with(10)


# =============================================================================
# Serialization Tests
# =============================================================================


class TestScorecardSerialization:
    """Tests for scorecard serialization/deserialization."""

    def test_scorecard_to_dict(
        self,
        evaluation_repository: EvaluationRepository,
        sample_scorecard: EvaluationScorecard,
    ) -> None:
        """Should serialize scorecard to dict."""
        result = evaluation_repository._scorecard_to_dict(sample_scorecard)

        assert "stage_scores" in result
        assert "ENGAGE" in result["stage_scores"]
        assert result["pbms_expressed"] == ["durability"]
        assert result["final_score"] == 85.0
        assert result["grade"] == "B"

    def test_dict_to_scorecard(
        self,
        evaluation_repository: EvaluationRepository,
        sample_evaluation_data: dict,
    ) -> None:
        """Should deserialize dict to scorecard."""
        result = evaluation_repository._dict_to_scorecard(sample_evaluation_data["scorecard"])

        assert "ENGAGE" in result.stage_scores
        assert result.stage_scores["ENGAGE"].score == 33.33
        assert result.pbm_match_rate == 1.0
        assert result.grade == Grade.B

    def test_dict_to_scorecard_handles_missing_fields(
        self,
        evaluation_repository: EvaluationRepository,
    ) -> None:
        """Should handle missing optional fields."""
        minimal_data = {
            "final_score": 50.0,
            "grade": "C",
        }

        result = evaluation_repository._dict_to_scorecard(minimal_data)

        assert result.stage_scores == {}
        assert result.pbms_expressed == []
        assert result.final_score == 50.0
        assert result.grade == Grade.C
