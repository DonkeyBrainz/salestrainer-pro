"""Unit tests for coach agent service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.state import CustomerAgentState, CoreStageProgress, SalesStage
from app.config import Settings
from app.models.coach import CoachAnalysis, CoachHint, InterventionLevel, StageItemUpdate
from app.models.evaluation import Evaluation, Grade
from app.models.session import SessionType
from app.repositories.evaluation_repository import EvaluationRepository
from app.services.coach_agent_service import CoachAgentService

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.coach_model = "gemini-2.0-flash"
    return settings


@pytest.fixture
def mock_evaluation_repository() -> MagicMock:
    """Create mock evaluation repository."""
    return MagicMock(spec=EvaluationRepository)


@pytest.fixture
def service(
    mock_settings: Settings,
    mock_evaluation_repository: MagicMock,
) -> CoachAgentService:
    """Create CoachAgentService instance with mocked dependencies."""
    return CoachAgentService(
        settings=mock_settings,
        evaluation_repository=mock_evaluation_repository,
    )


@pytest.fixture
def sample_state() -> CustomerAgentState:
    """Create sample customer agent state."""
    from langchain_core.messages import AIMessage, HumanMessage

    from app.agents.personas import ANXIOUS_FIRST_TIMER

    return CustomerAgentState(
        messages=[
            HumanMessage(content="Hi there!"),
            AIMessage(content="Hello! How can I help you today?"),
        ],
        persona=ANXIOUS_FIRST_TIMER,
        stage_progress=CoreStageProgress(
            current_stage=SalesStage.OBSERVE,
            connect={
                "warm_greeting": True,
                "establish_credibility": True,
                "create_comfort": False,
            },
            observe={
                "needs_discovery": False,
                "goal_identification": False,
                "motivator_mapping": False,
            },
            recommend={
                "solution_presentation": False,
                "value_connection": False,
                "risk_mitigation": False,
            },
            execute={
                "commitment_request": False,
                "objection_handling": False,
                "finalize_agreement": False,
            },
        ),
    )


@pytest.fixture
def sample_analysis() -> CoachAnalysis:
    """Create sample coach analysis."""
    return CoachAnalysis(
        techniques_detected=["needs_discovery"],
        stage_items_completed=[
            StageItemUpdate(stage="OBSERVE", item="needs_discovery", completed=True),
        ],
        pbms_acknowledged=[],
        deviations=[],
        intervention_level=InterventionLevel.INFO,
        hint="Good discovery question!",
        suggested_stage=None,
        confidence=0.85,
    )


# =============================================================================
# Initialization Tests
# =============================================================================


class TestCoachAgentServiceInit:
    """Tests for CoachAgentService initialization."""

    def test_init_with_settings(self, mock_settings: Settings) -> None:
        """Should initialize with settings."""
        service = CoachAgentService(settings=mock_settings)
        assert service.settings == mock_settings
        assert service.analyzer is not None
        assert service.evaluation_repository is not None

    def test_init_with_custom_repository(
        self,
        mock_settings: Settings,
        mock_evaluation_repository: MagicMock,
    ) -> None:
        """Should accept custom evaluation repository."""
        service = CoachAgentService(
            settings=mock_settings,
            evaluation_repository=mock_evaluation_repository,
        )
        assert service.evaluation_repository == mock_evaluation_repository


# =============================================================================
# Analyze Turn Tests
# =============================================================================


class TestAnalyzeTurn:
    """Tests for analyze_turn method."""

    @pytest.mark.asyncio
    async def test_analyze_turn_returns_tuple(
        self,
        service: CoachAgentService,
        sample_state: CustomerAgentState,
        sample_analysis: CoachAnalysis,
    ) -> None:
        """Should return tuple of analysis, progress, and optional hint."""
        with patch.object(service.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = sample_analysis

            result = await service.analyze_turn(
                salesperson_message="What brings you in today?",
                state=sample_state,
            )

            assert len(result) == 3
            analysis, updated_progress, hint = result
            assert isinstance(analysis, CoachAnalysis)
            assert isinstance(updated_progress, CoreStageProgress)
            mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_turn_updates_stage_progress(
        self,
        service: CoachAgentService,
        sample_state: CustomerAgentState,
        sample_analysis: CoachAnalysis,
    ) -> None:
        """Should update stage progress based on analysis."""
        with patch.object(service.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = sample_analysis

            _, updated_progress, _ = await service.analyze_turn(
                salesperson_message="What brings you in today?",
                state=sample_state,
            )

            # critical_questions should now be True
            assert updated_progress.observe["needs_discovery"] is True

    @pytest.mark.asyncio
    async def test_analyze_turn_generates_hint_in_training_mode(
        self,
        service: CoachAgentService,
        sample_state: CustomerAgentState,
    ) -> None:
        """Should generate hint in training mode for non-NONE interventions."""
        analysis_with_hint = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=["missed_needs_discovery"],
            intervention_level=InterventionLevel.WARNING,
            hint="Try asking discovery questions first.",
            suggested_stage=None,
            confidence=0.8,
        )

        with patch.object(service.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = analysis_with_hint

            _, _, hint = await service.analyze_turn(
                salesperson_message="Let me show you this sofa!",
                state=sample_state,
                session_mode=SessionType.TRAINING,
            )

            assert hint is not None
            assert isinstance(hint, CoachHint)
            assert hint.level == InterventionLevel.WARNING

    @pytest.mark.asyncio
    async def test_analyze_turn_no_hint_in_evaluation_mode(
        self,
        service: CoachAgentService,
        sample_state: CustomerAgentState,
    ) -> None:
        """Should not generate hint in evaluation mode."""
        analysis_with_warning = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=["missed_needs_discovery"],
            intervention_level=InterventionLevel.WARNING,
            hint="Try asking discovery questions first.",
            suggested_stage=None,
            confidence=0.8,
        )

        with patch.object(service.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = analysis_with_warning

            _, _, hint = await service.analyze_turn(
                salesperson_message="Let me show you this sofa!",
                state=sample_state,
                session_mode=SessionType.EVALUATION,
            )

            assert hint is None

    @pytest.mark.asyncio
    async def test_analyze_turn_no_hint_for_none_intervention(
        self,
        service: CoachAgentService,
        sample_state: CustomerAgentState,
    ) -> None:
        """Should not generate hint when intervention level is NONE."""
        analysis_none = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        with patch.object(service.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = analysis_none

            _, _, hint = await service.analyze_turn(
                salesperson_message="How can I help?",
                state=sample_state,
                session_mode=SessionType.TRAINING,
            )

            assert hint is None


# =============================================================================
# Stage Update Tests
# =============================================================================


class TestApplyStageUpdates:
    """Tests for _apply_stage_updates method."""

    def test_updates_engage_items(self, service: CoachAgentService) -> None:
        """Should update ENGAGE stage items."""
        progress = CoreStageProgress(
            current_stage=SalesStage.CONNECT,
            connect={
                "warm_greeting": False,
                "establish_credibility": False,
                "create_comfort": False,
            },
        )
        analysis = CoachAnalysis(
            techniques_detected=["warm_greeting"],
            stage_items_completed=[
                StageItemUpdate(stage="CONNECT", item="warm_greeting", completed=True),
            ],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.INFO,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        updated = service._apply_stage_updates(progress, analysis)

        assert updated.connect["warm_greeting"] is True
        assert updated.connect["establish_credibility"] is False

    def test_updates_ask_items(self, service: CoachAgentService) -> None:
        """Should update ASK stage items."""
        progress = CoreStageProgress(
            current_stage=SalesStage.OBSERVE,
            observe={
                "needs_discovery": False,
                "goal_identification": False,
                "motivator_mapping": False,
            },
        )
        analysis = CoachAnalysis(
            techniques_detected=["needs_discovery", "goal_identification"],
            stage_items_completed=[
                StageItemUpdate(stage="OBSERVE", item="needs_discovery", completed=True),
                StageItemUpdate(stage="OBSERVE", item="goal_identification", completed=True),
            ],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.INFO,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        updated = service._apply_stage_updates(progress, analysis)

        assert updated.observe["needs_discovery"] is True
        assert updated.observe["goal_identification"] is True
        assert updated.observe["motivator_mapping"] is False

    def test_adds_acknowledged_pbms(self, service: CoachAgentService) -> None:
        """Should add acknowledged PBMs."""
        progress = CoreStageProgress(
            current_stage=SalesStage.RECOMMEND,
            pbms_expressed=["durability", "style"],
            pbms_acknowledged=[],
        )
        analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=["durability"],
            deviations=[],
            intervention_level=InterventionLevel.INFO,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        updated = service._apply_stage_updates(progress, analysis)

        assert "durability" in updated.pbms_acknowledged
        assert "style" not in updated.pbms_acknowledged

    def test_does_not_duplicate_pbms(self, service: CoachAgentService) -> None:
        """Should not duplicate already acknowledged PBMs."""
        progress = CoreStageProgress(
            current_stage=SalesStage.RECOMMEND,
            pbms_expressed=["durability", "style"],
            pbms_acknowledged=["durability"],
        )
        analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=["durability"],
            deviations=[],
            intervention_level=InterventionLevel.INFO,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        updated = service._apply_stage_updates(progress, analysis)

        assert updated.pbms_acknowledged.count("durability") == 1

    def test_updates_current_stage(self, service: CoachAgentService) -> None:
        """Should update current stage from suggestion."""
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)
        analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage="OBSERVE",
            confidence=0.9,
        )

        updated = service._apply_stage_updates(progress, analysis)

        assert updated.current_stage == SalesStage.OBSERVE

    def test_techniques_detected_marks_items_complete(self, service: CoachAgentService) -> None:
        """Items in techniques_detected should be marked complete even without stage_items_completed."""
        progress = CoreStageProgress(
            current_stage=SalesStage.CONNECT,
            connect={
                "warm_greeting": False,
                "establish_credibility": False,
                "create_comfort": False,
            },
        )
        # LLM detected techniques but did NOT include them in stage_items_completed
        analysis = CoachAnalysis(
            techniques_detected=["warm_greeting", "establish_credibility"],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.INFO,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        updated = service._apply_stage_updates(progress, analysis)

        assert updated.connect["warm_greeting"] is True
        assert updated.connect["establish_credibility"] is True
        assert updated.connect["create_comfort"] is False

    def test_techniques_detected_works_across_stages(self, service: CoachAgentService) -> None:
        """techniques_detected should mark items in any stage, not just current."""
        progress = CoreStageProgress(
            current_stage=SalesStage.OBSERVE,
            connect={
                "warm_greeting": False,
                "establish_credibility": False,
                "create_comfort": False,
            },
            observe={
                "needs_discovery": False,
                "goal_identification": False,
                "motivator_mapping": False,
            },
            recommend={
                "solution_presentation": False,
                "value_connection": False,
                "risk_mitigation": False,
            },
        )
        analysis = CoachAnalysis(
            techniques_detected=["warm_greeting", "needs_discovery", "solution_presentation"],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        updated = service._apply_stage_updates(progress, analysis)

        assert updated.connect["warm_greeting"] is True
        assert updated.observe["needs_discovery"] is True
        assert updated.recommend["solution_presentation"] is True

    def test_ignores_invalid_stage_suggestion(self, service: CoachAgentService) -> None:
        """Should ignore invalid stage suggestion."""
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)
        analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage="INVALID_STAGE",
            confidence=0.9,
        )

        updated = service._apply_stage_updates(progress, analysis)

        assert updated.current_stage == SalesStage.CONNECT


# =============================================================================
# Get Stage Dict Tests
# =============================================================================


class TestGetStageDict:
    """Tests for _get_stage_dict method."""

    def test_returns_engage_dict(self, service: CoachAgentService) -> None:
        """Should return engage dict for ENGAGE stage."""
        progress = CoreStageProgress(
            current_stage=SalesStage.CONNECT,
            connect={"test": True},
        )
        result = service._get_stage_dict(progress, "CONNECT")
        assert result == {"test": True}

    def test_returns_ask_dict(self, service: CoachAgentService) -> None:
        """Should return ask dict for ASK stage."""
        progress = CoreStageProgress(current_stage=SalesStage.OBSERVE)
        result = service._get_stage_dict(progress, "OBSERVE")
        assert result is not None

    def test_returns_show_dict(self, service: CoachAgentService) -> None:
        """Should return show dict for SHOW stage."""
        progress = CoreStageProgress(current_stage=SalesStage.RECOMMEND)
        result = service._get_stage_dict(progress, "RECOMMEND")
        assert result is not None

    def test_returns_yes_dict(self, service: CoachAgentService) -> None:
        """Should return yes dict for YES stage."""
        progress = CoreStageProgress(current_stage=SalesStage.EXECUTE)
        result = service._get_stage_dict(progress, "EXECUTE")
        assert result is not None

    def test_handles_lowercase(self, service: CoachAgentService) -> None:
        """Should handle lowercase stage names."""
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)
        result = service._get_stage_dict(progress, "connect")
        assert result is not None

    def test_returns_none_for_invalid(self, service: CoachAgentService) -> None:
        """Should return None for invalid stage."""
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)
        result = service._get_stage_dict(progress, "INVALID")
        assert result is None


# =============================================================================
# Generate Hint Tests
# =============================================================================


class TestGenerateHint:
    """Tests for _generate_hint method."""

    def test_generates_coach_hint(self, service: CoachAgentService) -> None:
        """Should generate CoachHint from analysis."""
        analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=["missed_needs_discovery"],
            intervention_level=InterventionLevel.WARNING,
            hint="Ask more questions",
            example_phrase="What brings you in today?",
            ready_for_next_stage=False,
            suggested_stage=None,
            confidence=0.8,
        )
        progress = CoreStageProgress(
            current_stage=SalesStage.OBSERVE,
            observe={
                "needs_discovery": True,
                "goal_identification": False,
                "motivator_mapping": False,
            },
        )

        hint = service._generate_hint(analysis, progress)

        assert hint.level == InterventionLevel.WARNING
        assert hint.hint == "Ask more questions"
        assert hint.stage == "OBSERVE"
        assert hint.example_phrase == "What brings you in today?"
        assert hint.ready_for_next_stage is False

    def test_passes_example_phrase_from_analysis(self, service: CoachAgentService) -> None:
        """Should pass example_phrase from analysis to hint."""
        analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.SUGGESTION,
            hint="Try a deeper question.",
            example_phrase="Why is that important to you?",
            ready_for_next_stage=False,
            suggested_stage=None,
            confidence=0.9,
        )
        progress = CoreStageProgress(current_stage=SalesStage.OBSERVE)

        hint = service._generate_hint(analysis, progress)

        assert hint.example_phrase == "Why is that important to you?"

    def test_uses_fallback_example_phrase_for_warning(self, service: CoachAgentService) -> None:
        """Should use fallback example phrase when LLM doesn't provide one for warning."""
        analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=["missed_needs_discovery"],
            intervention_level=InterventionLevel.WARNING,
            hint="You skipped discovery.",
            example_phrase=None,
            ready_for_next_stage=False,
            suggested_stage=None,
            confidence=0.8,
        )
        progress = CoreStageProgress(current_stage=SalesStage.OBSERVE)

        hint = service._generate_hint(analysis, progress)

        assert hint.example_phrase is not None
        assert len(hint.example_phrase) > 0

    def test_no_example_phrase_for_info(self, service: CoachAgentService) -> None:
        """Should not generate example phrase for info level."""
        analysis = CoachAnalysis(
            techniques_detected=["warm_greeting"],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.INFO,
            hint="Nice greeting!",
            example_phrase=None,
            ready_for_next_stage=False,
            suggested_stage=None,
            confidence=0.9,
        )
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

        hint = service._generate_hint(analysis, progress)

        assert hint.example_phrase is None

    def test_passes_ready_for_next_stage(self, service: CoachAgentService) -> None:
        """Should pass ready_for_next_stage from analysis to hint."""
        analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.INFO,
            hint="ENGAGE stage complete!",
            example_phrase=None,
            ready_for_next_stage=True,
            suggested_stage="OBSERVE",
            confidence=0.9,
        )
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

        hint = service._generate_hint(analysis, progress)

        assert hint.ready_for_next_stage is True

    def test_uses_fallback_hint_when_none(self, service: CoachAgentService) -> None:
        """Should use fallback hint when analysis hint is None."""
        analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.SUGGESTION,
            hint=None,
            example_phrase=None,
            ready_for_next_stage=False,
            suggested_stage=None,
            confidence=0.9,
        )
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

        hint = service._generate_hint(analysis, progress)

        assert hint.hint is not None
        assert "C.O.R.E." in hint.hint


# =============================================================================
# Generate Evaluation Tests
# =============================================================================


class TestGenerateEvaluation:
    """Tests for generate_evaluation method."""

    @pytest.mark.asyncio
    async def test_creates_evaluation(
        self,
        service: CoachAgentService,
        mock_evaluation_repository: MagicMock,
        sample_state: CustomerAgentState,
    ) -> None:
        """Should create and save evaluation."""
        mock_evaluation = MagicMock(spec=Evaluation)
        mock_evaluation_repository.create = AsyncMock(return_value=mock_evaluation)

        result = await service.generate_evaluation(
            session_id="session-123",
            user_id="user-456",
            state=sample_state,
        )

        assert result == mock_evaluation
        mock_evaluation_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluation_includes_scorecard(
        self,
        service: CoachAgentService,
        mock_evaluation_repository: MagicMock,
        sample_state: CustomerAgentState,
    ) -> None:
        """Should include scorecard in evaluation."""
        mock_evaluation_repository.create = AsyncMock(
            side_effect=lambda create_obj: MagicMock(
                scorecard=create_obj.scorecard,
                summary=create_obj.summary,
            )
        )

        result = await service.generate_evaluation(
            session_id="session-123",
            user_id="user-456",
            state=sample_state,
        )

        assert result.scorecard is not None

    @pytest.mark.asyncio
    async def test_evaluation_with_full_progress(
        self,
        service: CoachAgentService,
        mock_evaluation_repository: MagicMock,
    ) -> None:
        """Should calculate high score for complete progress."""
        from langchain_core.messages import AIMessage, HumanMessage

        from app.agents.personas import ANXIOUS_FIRST_TIMER

        complete_state = CustomerAgentState(
            messages=[
                HumanMessage(content="Hi"),
                AIMessage(content="Hello"),
            ],
            persona=ANXIOUS_FIRST_TIMER,
            stage_progress=CoreStageProgress(
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
                pbms_expressed=["durability", "style"],
                pbms_acknowledged=["durability", "style"],
            ),
            objections_raised=["price"],
            objections_resolved=["price"],
        )

        captured_create = None

        async def capture_create(create_obj):
            nonlocal captured_create
            captured_create = create_obj
            return MagicMock(
                scorecard=create_obj.scorecard,
                summary=create_obj.summary,
                grade=create_obj.scorecard.grade,
            )

        mock_evaluation_repository.create = AsyncMock(side_effect=capture_create)

        await service.generate_evaluation(
            session_id="session-123",
            user_id="user-456",
            state=complete_state,
        )

        assert captured_create is not None
        assert captured_create.scorecard.grade == Grade.A
        assert captured_create.scorecard.final_score >= 90


# =============================================================================
# Build Scorecard Tests
# =============================================================================


class TestBuildScorecard:
    """Tests for _build_scorecard method."""

    def test_builds_complete_scorecard(self, service: CoachAgentService) -> None:
        """Should build complete scorecard with all fields."""
        progress = CoreStageProgress(
            current_stage=SalesStage.COMPLETE,
            connect={
                "warm_greeting": True,
                "establish_credibility": True,
                "create_comfort": False,
            },
            observe={
                "needs_discovery": True,
                "goal_identification": False,
                "motivator_mapping": False,
            },
            recommend={
                "solution_presentation": False,
                "value_connection": False,
                "risk_mitigation": False,
            },
            execute={
                "commitment_request": False,
                "objection_handling": False,
                "finalize_agreement": False,
            },
            pbms_expressed=["durability"],
            pbms_acknowledged=["durability"],
        )

        scorecard = service._build_scorecard(
            stage_progress=progress,
            objections_raised=["price"],
            objections_resolved=["price"],
            deviations=[],
            raw_score=40.0,
            final_score=50.0,
            grade=Grade.F,
        )

        assert "CONNECT" in scorecard.stage_scores
        assert "OBSERVE" in scorecard.stage_scores
        assert "RECOMMEND" in scorecard.stage_scores
        assert "EXECUTE" in scorecard.stage_scores
        assert scorecard.raw_score == 40.0
        assert scorecard.final_score == 50.0
        assert scorecard.grade == Grade.F

    def test_calculates_stage_scores(self, service: CoachAgentService) -> None:
        """Should calculate individual stage scores."""
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
                "solution_presentation": False,
                "value_connection": False,
                "risk_mitigation": False,
            },
            execute={
                "commitment_request": False,
                "objection_handling": False,
                "finalize_agreement": False,
            },
        )

        scorecard = service._build_scorecard(
            stage_progress=progress,
            objections_raised=[],
            objections_resolved=[],
            deviations=[],
            raw_score=45.0,
            final_score=45.0,
            grade=Grade.F,
        )

        assert scorecard.stage_scores["CONNECT"].score == 100.0
        assert scorecard.stage_scores["OBSERVE"].score == 100.0
        assert scorecard.stage_scores["RECOMMEND"].score == 0.0
        assert scorecard.stage_scores["EXECUTE"].score == 0.0


# =============================================================================
# Generate Feedback Tests
# =============================================================================


class TestGenerateFeedback:
    """Tests for _generate_feedback method."""

    def test_identifies_strengths(self, service: CoachAgentService) -> None:
        """Should identify high-scoring stages as strengths."""
        progress = CoreStageProgress(
            current_stage=SalesStage.COMPLETE,
            connect={
                "warm_greeting": True,
                "establish_credibility": True,
                "create_comfort": True,
            },
        )

        scorecard = service._build_scorecard(
            stage_progress=progress,
            objections_raised=[],
            objections_resolved=[],
            deviations=[],
            raw_score=15.0,
            final_score=15.0,
            grade=Grade.F,
        )

        strengths, _ = service._generate_feedback(progress, scorecard)

        assert any("CONNECT" in s for s in strengths)

    def test_identifies_improvements(self, service: CoachAgentService) -> None:
        """Should identify low-scoring stages for improvement."""
        progress = CoreStageProgress(
            current_stage=SalesStage.COMPLETE,
            observe={
                "needs_discovery": False,
                "goal_identification": False,
                "motivator_mapping": False,
            },
        )

        scorecard = service._build_scorecard(
            stage_progress=progress,
            objections_raised=[],
            objections_resolved=[],
            deviations=[],
            raw_score=0.0,
            final_score=0.0,
            grade=Grade.F,
        )

        _, improvements = service._generate_feedback(progress, scorecard)

        assert any("OBSERVE" in i for i in improvements)

    def test_feedback_on_pbm_handling(self, service: CoachAgentService) -> None:
        """Should provide feedback on PBM handling."""
        progress = CoreStageProgress(
            current_stage=SalesStage.COMPLETE,
            pbms_expressed=["durability", "style"],
            pbms_acknowledged=["durability", "style"],
        )

        scorecard = service._build_scorecard(
            stage_progress=progress,
            objections_raised=[],
            objections_resolved=[],
            deviations=[],
            raw_score=0.0,
            final_score=10.0,
            grade=Grade.F,
        )

        strengths, _ = service._generate_feedback(progress, scorecard)

        assert any("motivator" in s for s in strengths)


# =============================================================================
# Generate Summary Tests
# =============================================================================


class TestGenerateSummary:
    """Tests for _generate_summary method."""

    def test_generates_grade_a_summary(self, service: CoachAgentService) -> None:
        """Should generate appropriate summary for Grade A."""
        summary = service._generate_summary(Grade.A, 95.0)
        assert "Excellent" in summary
        assert "95" in summary

    def test_generates_grade_b_summary(self, service: CoachAgentService) -> None:
        """Should generate appropriate summary for Grade B."""
        summary = service._generate_summary(Grade.B, 85.0)
        assert "Good" in summary
        assert "85" in summary

    def test_generates_grade_c_summary(self, service: CoachAgentService) -> None:
        """Should generate appropriate summary for Grade C."""
        summary = service._generate_summary(Grade.C, 75.0)
        assert "Satisfactory" in summary

    def test_generates_grade_d_summary(self, service: CoachAgentService) -> None:
        """Should generate appropriate summary for Grade D."""
        summary = service._generate_summary(Grade.D, 65.0)
        assert "Below average" in summary

    def test_generates_grade_f_summary(self, service: CoachAgentService) -> None:
        """Should generate appropriate summary for Grade F."""
        summary = service._generate_summary(Grade.F, 45.0)
        assert "Needs improvement" in summary


# =============================================================================
# Get Detected Techniques Tests
# =============================================================================


class TestGetDetectedTechniques:
    """Tests for _get_detected_techniques method."""

    def test_collects_all_completed_techniques(self, service: CoachAgentService) -> None:
        """Should collect completed techniques from all stages."""
        progress = CoreStageProgress(
            current_stage=SalesStage.COMPLETE,
            connect={
                "warm_greeting": True,
                "establish_credibility": True,
                "create_comfort": False,
            },
            observe={
                "needs_discovery": True,
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
                "finalize_agreement": True,
            },
        )

        techniques = service._get_detected_techniques(progress)

        assert "warm_greeting" in techniques
        assert "establish_credibility" in techniques
        assert "needs_discovery" in techniques
        assert "solution_presentation" in techniques
        assert "finalize_agreement" in techniques
        assert "create_comfort" not in techniques
        assert len(techniques) == 5

    def test_returns_empty_for_no_progress(self, service: CoachAgentService) -> None:
        """Should return empty list when no techniques completed."""
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

        techniques = service._get_detected_techniques(progress)

        assert techniques == []


# =============================================================================
# Multi-Turn Stage Progress Tracking Tests
# =============================================================================


class TestMultiTurnProgressTracking:
    """Tests verifying stage_progress accumulates correctly across multiple turns."""

    @pytest.mark.asyncio
    async def test_progress_accumulates_across_turns(
        self,
        service: CoachAgentService,
        mock_settings: Settings,
        mock_evaluation_repository: MagicMock,
    ) -> None:
        """Items detected in separate turns should all be reflected in progress."""
        from langchain_core.messages import AIMessage, HumanMessage

        from app.agents.personas import ANXIOUS_FIRST_TIMER

        # Start with a fresh state where all ENGAGE items are False
        state = CustomerAgentState(
            messages=[
                HumanMessage(content="Hi there!"),
                AIMessage(content="Hello!"),
            ],
            persona=ANXIOUS_FIRST_TIMER,
            stage_progress=CoreStageProgress(
                current_stage=SalesStage.CONNECT,
                connect={
                    "warm_greeting": False,
                    "establish_credibility": False,
                    "create_comfort": False,
                },
            ),
        )

        svc = CoachAgentService(
            settings=mock_settings,
            evaluation_repository=mock_evaluation_repository,
        )

        # Turn 1: detect non_business_greet
        analysis_turn1 = CoachAnalysis(
            techniques_detected=["warm_greeting"],
            stage_items_completed=[
                StageItemUpdate(stage="CONNECT", item="warm_greeting", completed=True),
            ],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.INFO,
            hint="Good greeting!",
            suggested_stage=None,
            confidence=0.9,
        )

        with patch.object(svc.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = analysis_turn1

            _, progress_after_turn1, _ = await svc.analyze_turn(
                salesperson_message="Hey, how's your day going?",
                state=state,
            )

        assert progress_after_turn1.connect["warm_greeting"] is True
        assert progress_after_turn1.connect["establish_credibility"] is False

        # Update state with new progress (simulating relay loop)
        state["stage_progress"] = progress_after_turn1

        # Turn 2: detect established_rapport
        analysis_turn2 = CoachAnalysis(
            techniques_detected=["establish_credibility"],
            stage_items_completed=[
                StageItemUpdate(stage="CONNECT", item="establish_credibility", completed=True),
            ],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        with patch.object(svc.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = analysis_turn2

            _, progress_after_turn2, _ = await svc.analyze_turn(
                salesperson_message="I love your shirt, where'd you get it?",
                state=state,
            )

        # Both items from turn 1 and turn 2 should be True
        assert progress_after_turn2.connect["warm_greeting"] is True
        assert progress_after_turn2.connect["establish_credibility"] is True
        assert progress_after_turn2.connect["create_comfort"] is False

    @pytest.mark.asyncio
    async def test_completed_items_never_revert(
        self,
        service: CoachAgentService,
        sample_state: CustomerAgentState,
    ) -> None:
        """An item marked True should remain True even if not in later analyses."""
        # Turn 1: mark critical_questions
        analysis_turn1 = CoachAnalysis(
            techniques_detected=["needs_discovery"],
            stage_items_completed=[
                StageItemUpdate(stage="OBSERVE", item="needs_discovery", completed=True),
            ],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        with patch.object(service.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = analysis_turn1

            _, progress1, _ = await service.analyze_turn(
                salesperson_message="What are you looking for today?",
                state=sample_state,
            )

        assert progress1.observe["needs_discovery"] is True

        # Turn 2: analysis detects nothing (no stage_items_completed)
        sample_state["stage_progress"] = progress1
        analysis_turn2 = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        with patch.object(service.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = analysis_turn2

            _, progress2, _ = await service.analyze_turn(
                salesperson_message="Uh huh",
                state=sample_state,
            )

        # critical_questions should still be True
        assert progress2.observe["needs_discovery"] is True

    @pytest.mark.asyncio
    async def test_pbms_accumulate_across_turns(
        self,
        service: CoachAgentService,
        sample_state: CustomerAgentState,
    ) -> None:
        """PBMs acknowledged in different turns should all persist."""
        sample_state["stage_progress"].pbms_expressed = ["durability", "style", "comfort"]

        # Turn 1: acknowledge durability
        analysis1 = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=["durability"],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        with patch.object(service.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = analysis1

            _, progress1, _ = await service.analyze_turn(
                salesperson_message="This sofa is built to last.",
                state=sample_state,
            )

        assert progress1.pbms_acknowledged == ["durability"]

        # Turn 2: acknowledge style
        sample_state["stage_progress"] = progress1
        analysis2 = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=["style"],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        with patch.object(service.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = analysis2

            _, progress2, _ = await service.analyze_turn(
                salesperson_message="And it comes in a modern design.",
                state=sample_state,
            )

        assert "durability" in progress2.pbms_acknowledged
        assert "style" in progress2.pbms_acknowledged
        assert len(progress2.pbms_acknowledged) == 2

    @pytest.mark.asyncio
    async def test_cross_stage_progress_tracked(
        self,
        service: CoachAgentService,
        sample_state: CustomerAgentState,
    ) -> None:
        """Progress in different stages should be independently tracked."""
        # Analysis detects items in both ENGAGE and ASK stages
        analysis = CoachAnalysis(
            techniques_detected=["create_comfort", "needs_discovery"],
            stage_items_completed=[
                StageItemUpdate(stage="CONNECT", item="create_comfort", completed=True),
                StageItemUpdate(stage="OBSERVE", item="needs_discovery", completed=True),
            ],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage="OBSERVE",
            confidence=0.9,
        )

        with patch.object(service.analyzer, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = analysis

            _, progress, _ = await service.analyze_turn(
                salesperson_message="My manager said we have a great deal. What brings you in?",
                state=sample_state,
            )

        # sample_state already has non_business_greet and established_rapport True
        assert progress.connect["warm_greeting"] is True
        assert progress.connect["establish_credibility"] is True
        assert progress.connect["create_comfort"] is True
        assert progress.observe["needs_discovery"] is True
        assert progress.observe["goal_identification"] is False
        assert progress.current_stage == SalesStage.OBSERVE

    def test_apply_stage_updates_preserves_other_stages(
        self,
        service: CoachAgentService,
    ) -> None:
        """Updating one stage should not affect others."""
        progress = CoreStageProgress(
            current_stage=SalesStage.RECOMMEND,
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
                "solution_presentation": False,
                "value_connection": False,
                "risk_mitigation": False,
            },
            execute={
                "commitment_request": False,
                "objection_handling": False,
                "finalize_agreement": False,
            },
        )

        analysis = CoachAnalysis(
            techniques_detected=["solution_presentation"],
            stage_items_completed=[
                StageItemUpdate(stage="RECOMMEND", item="solution_presentation", completed=True),
            ],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )

        updated = service._apply_stage_updates(progress, analysis)

        # SHOW updated
        assert updated.recommend["solution_presentation"] is True
        # ENGAGE and ASK unchanged
        assert all(v for v in updated.connect.values())
        assert all(v for v in updated.observe.values())
        # YES unchanged
        assert not any(v for v in updated.execute.values())


# =============================================================================
# Evaluation Accuracy Tests
# =============================================================================


class TestEvaluationAccuracy:
    """Tests verifying evaluation scores match expected values for known states."""

    @pytest.mark.asyncio
    async def test_empty_progress_scores_zero(
        self,
        service: CoachAgentService,
        mock_evaluation_repository: MagicMock,
    ) -> None:
        """Empty stage progress should produce score 0 and grade F."""
        from langchain_core.messages import AIMessage, HumanMessage

        from app.agents.personas import ANXIOUS_FIRST_TIMER

        empty_state = CustomerAgentState(
            messages=[HumanMessage(content="Hi"), AIMessage(content="Hello")],
            persona=ANXIOUS_FIRST_TIMER,
            stage_progress=CoreStageProgress(current_stage=SalesStage.CONNECT),
        )

        captured = {}

        async def capture_create(create_obj):
            captured["obj"] = create_obj
            return MagicMock(
                scorecard=create_obj.scorecard,
                final_score=create_obj.scorecard.final_score,
                grade=create_obj.scorecard.grade,
                summary=create_obj.summary,
                strengths=create_obj.strengths,
                improvements=create_obj.improvements,
                techniques_detected=create_obj.techniques_detected,
            )

        mock_evaluation_repository.create = AsyncMock(side_effect=capture_create)

        await service.generate_evaluation(session_id="s1", user_id="u1", state=empty_state)

        sc = captured["obj"].scorecard
        assert sc.final_score == 0.0
        assert sc.grade == Grade.F
        assert sc.stage_scores["CONNECT"].score == 0.0
        assert sc.stage_scores["OBSERVE"].score == 0.0
        assert sc.stage_scores["RECOMMEND"].score == 0.0
        assert sc.stage_scores["EXECUTE"].score == 0.0

    @pytest.mark.asyncio
    async def test_half_complete_scores_correctly(
        self,
        service: CoachAgentService,
        mock_evaluation_repository: MagicMock,
    ) -> None:
        """Half-complete progress should produce predictable weighted score."""
        from langchain_core.messages import AIMessage, HumanMessage

        from app.agents.personas import ANXIOUS_FIRST_TIMER

        # ENGAGE: 2/3 = 66.67, ASK: 1/3 = 33.33, SHOW: 0/3, YES: 0/3
        half_state = CustomerAgentState(
            messages=[HumanMessage(content="Hi"), AIMessage(content="Hello")],
            persona=ANXIOUS_FIRST_TIMER,
            stage_progress=CoreStageProgress(
                current_stage=SalesStage.OBSERVE,
                connect={
                    "warm_greeting": True,
                    "establish_credibility": True,
                    "create_comfort": False,
                },
                observe={
                    "needs_discovery": True,
                    "goal_identification": False,
                    "motivator_mapping": False,
                },
            ),
        )

        captured = {}

        async def capture_create(create_obj):
            captured["obj"] = create_obj
            return MagicMock(
                scorecard=create_obj.scorecard,
                final_score=create_obj.scorecard.final_score,
                grade=create_obj.scorecard.grade,
            )

        mock_evaluation_repository.create = AsyncMock(side_effect=capture_create)

        await service.generate_evaluation(session_id="s1", user_id="u1", state=half_state)

        sc = captured["obj"].scorecard
        # ENGAGE: 66.67 * 0.15 = 10.0, ASK: 33.33 * 0.30 = 10.0
        # SHOW: 0, YES: 0 => raw = 20.0
        assert abs(sc.raw_score - 20.0) < 0.1
        assert sc.grade == Grade.F  # 20.0 < 60

    @pytest.mark.asyncio
    async def test_full_progress_with_pbms_gets_grade_a(
        self,
        service: CoachAgentService,
        mock_evaluation_repository: MagicMock,
    ) -> None:
        """Full stage progress with PBMs should achieve grade A."""
        from langchain_core.messages import AIMessage, HumanMessage

        from app.agents.personas import ANXIOUS_FIRST_TIMER

        full_state = CustomerAgentState(
            messages=[HumanMessage(content="Hi"), AIMessage(content="Hello")],
            persona=ANXIOUS_FIRST_TIMER,
            stage_progress=CoreStageProgress(
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
                pbms_expressed=["durability", "style"],
                pbms_acknowledged=["durability", "style"],
            ),
            objections_raised=["price"],
            objections_resolved=["price"],
        )

        captured = {}

        async def capture_create(create_obj):
            captured["obj"] = create_obj
            return MagicMock(
                scorecard=create_obj.scorecard,
                final_score=create_obj.scorecard.final_score,
                grade=create_obj.scorecard.grade,
            )

        mock_evaluation_repository.create = AsyncMock(side_effect=capture_create)

        await service.generate_evaluation(session_id="s1", user_id="u1", state=full_state)

        sc = captured["obj"].scorecard
        assert sc.raw_score == 100.0
        assert sc.pbm_bonus == 10.0
        assert sc.final_score == 100.0  # Clamped: 100 + 10 = 110 -> 100
        assert sc.grade == Grade.A

    @pytest.mark.asyncio
    async def test_scorecard_stage_scores_match_progress(
        self,
        service: CoachAgentService,
        mock_evaluation_repository: MagicMock,
    ) -> None:
        """Scorecard stage_scores items should match the stage_progress state."""
        from langchain_core.messages import AIMessage, HumanMessage

        from app.agents.personas import ANXIOUS_FIRST_TIMER

        state = CustomerAgentState(
            messages=[HumanMessage(content="Hi"), AIMessage(content="Hello")],
            persona=ANXIOUS_FIRST_TIMER,
            stage_progress=CoreStageProgress(
                current_stage=SalesStage.RECOMMEND,
                connect={
                    "warm_greeting": True,
                    "establish_credibility": True,
                    "create_comfort": False,
                },
                observe={
                    "needs_discovery": True,
                    "goal_identification": True,
                    "motivator_mapping": True,
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
            ),
        )

        captured = {}

        async def capture_create(create_obj):
            captured["obj"] = create_obj
            return MagicMock(scorecard=create_obj.scorecard)

        mock_evaluation_repository.create = AsyncMock(side_effect=capture_create)

        await service.generate_evaluation(session_id="s1", user_id="u1", state=state)

        sc = captured["obj"].scorecard
        # Verify items_completed lists match what was True in progress
        assert set(sc.stage_scores["CONNECT"].items_completed) == {
            "warm_greeting",
            "establish_credibility",
        }
        assert set(sc.stage_scores["OBSERVE"].items_completed) == {
            "needs_discovery",
            "goal_identification",
            "motivator_mapping",
        }
        assert sc.stage_scores["RECOMMEND"].items_completed == ["solution_presentation"]
        assert sc.stage_scores["EXECUTE"].items_completed == []

    @pytest.mark.asyncio
    async def test_feedback_aligns_with_scores(
        self,
        service: CoachAgentService,
        mock_evaluation_repository: MagicMock,
    ) -> None:
        """Strengths should list high-scoring stages, improvements low-scoring ones."""
        from langchain_core.messages import AIMessage, HumanMessage

        from app.agents.personas import ANXIOUS_FIRST_TIMER

        # ENGAGE and ASK complete (scores 100), SHOW and YES empty (scores 0)
        state = CustomerAgentState(
            messages=[HumanMessage(content="Hi"), AIMessage(content="Hello")],
            persona=ANXIOUS_FIRST_TIMER,
            stage_progress=CoreStageProgress(
                current_stage=SalesStage.RECOMMEND,
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
                    "solution_presentation": False,
                    "value_connection": False,
                    "risk_mitigation": False,
                },
                execute={
                    "commitment_request": False,
                    "objection_handling": False,
                    "finalize_agreement": False,
                },
            ),
        )

        captured = {}

        async def capture_create(create_obj):
            captured["obj"] = create_obj
            return MagicMock(
                strengths=create_obj.strengths,
                improvements=create_obj.improvements,
            )

        mock_evaluation_repository.create = AsyncMock(side_effect=capture_create)

        await service.generate_evaluation(session_id="s1", user_id="u1", state=state)

        obj = captured["obj"]
        # ENGAGE (100) and ASK (100) should be strengths (>= 66)
        assert any("CONNECT" in s for s in obj.strengths)
        assert any("OBSERVE" in s for s in obj.strengths)
        # SHOW (0) and YES (0) should be improvements (< 33)
        assert any("RECOMMEND" in i for i in obj.improvements)
        assert any("EXECUTE" in i for i in obj.improvements)

    @pytest.mark.asyncio
    async def test_objection_penalty_applied_correctly(
        self,
        service: CoachAgentService,
        mock_evaluation_repository: MagicMock,
    ) -> None:
        """Unresolved objections should reduce the final score."""
        from langchain_core.messages import AIMessage, HumanMessage

        from app.agents.personas import ANXIOUS_FIRST_TIMER

        state = CustomerAgentState(
            messages=[HumanMessage(content="Hi"), AIMessage(content="Hello")],
            persona=ANXIOUS_FIRST_TIMER,
            stage_progress=CoreStageProgress(
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
            ),
            objections_raised=["price", "timing", "quality", "delivery"],
            objections_resolved=[],  # 0% resolution -> max penalty
        )

        captured = {}

        async def capture_create(create_obj):
            captured["obj"] = create_obj
            return MagicMock(scorecard=create_obj.scorecard)

        mock_evaluation_repository.create = AsyncMock(side_effect=capture_create)

        await service.generate_evaluation(session_id="s1", user_id="u1", state=state)

        sc = captured["obj"].scorecard
        assert sc.raw_score == 100.0
        assert sc.objection_penalty == -10.0
        assert sc.final_score == 90.0  # 100 + 0 - 10 + 0
