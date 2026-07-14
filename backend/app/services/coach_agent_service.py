"""Service for coach agent orchestration.

This module provides the main service layer for the coach agent,
coordinating analysis, scoring, and intervention generation.
"""

import asyncio
import logging

from langchain_core.messages import BaseMessage

from app.agents.coach.analyzer import CoachAnalyzer
from app.agents.coach.hints import get_example_phrase_fallback
from app.agents.coach.scorer import calculate_score
from app.agents.state import CoreStageProgress, CustomerAgentState, CustomerPersona, SalesStage
from app.config import Settings
from app.llm_providers import ChatMessage, ChatRole, GeminiProvider, LLMProvider
from app.models.coach import CoachAnalysis, CoachHint, FeedbackResponse, InterventionLevel
from app.models.evaluation import (
    Evaluation,
    EvaluationCreate,
    EvaluationScorecard,
    Grade,
    StageScore,
)
from app.models.session import SessionType
from app.repositories.evaluation_repository import EvaluationRepository

logger = logging.getLogger(__name__)


class CoachAgentService:
    """Service for coach agent operations.

    This service handles:
    - Analyzing salesperson messages for C.O.R.E. technique usage
    - Updating stage progress based on analysis
    - Generating coaching hints (Training mode)
    - Creating post-session evaluations
    """

    def __init__(
        self,
        settings: Settings,
        evaluation_repository: EvaluationRepository | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            settings: Application settings.
            evaluation_repository: Repository for storing evaluations.
            provider: LLM provider shared by the analyzer and feedback
                generation. Defaults to Gemini; the eval harness injects
                alternatives here.
        """
        self.settings = settings
        self.provider: LLMProvider = provider or GeminiProvider(settings)
        self.analyzer = CoachAnalyzer(model=settings.coach_model, provider=self.provider)
        self.evaluation_repository = evaluation_repository or EvaluationRepository()

    async def analyze_turn(
        self,
        salesperson_message: str,
        state: CustomerAgentState,
        session_mode: SessionType = SessionType.TRAINING,
    ) -> tuple[CoachAnalysis, CoreStageProgress, CoachHint | None]:
        """Analyze a salesperson turn and optionally generate coaching hint.

        Args:
            salesperson_message: The salesperson's message to analyze.
            state: Current customer agent state.
            session_mode: Training (hints) or Evaluation (silent).

        Returns:
            Tuple of (analysis, updated_progress, optional_hint).
        """
        # Get analysis from LLM
        analysis = await self.analyzer.analyze(
            salesperson_message=salesperson_message,
            messages=state["messages"],
            persona=state["persona"],
            stage_progress=state["stage_progress"],
        )

        # Update stage progress based on analysis
        updated_progress = self._apply_stage_updates(
            stage_progress=state["stage_progress"],
            analysis=analysis,
        )

        # Generate hint only for Training mode and non-NONE interventions
        hint: CoachHint | None = None
        if (
            session_mode == SessionType.TRAINING
            and analysis.intervention_level != InterventionLevel.NONE
        ):
            hint = self._generate_hint(
                analysis=analysis,
                stage_progress=updated_progress,
            )

        return analysis, updated_progress, hint

    def _apply_stage_updates(
        self,
        stage_progress: CoreStageProgress,
        analysis: CoachAnalysis,
    ) -> CoreStageProgress:
        """Apply analysis results to stage progress.

        Args:
            stage_progress: Current stage progress.
            analysis: Coach analysis with completed items.

        Returns:
            Updated stage progress.
        """
        # Create a mutable copy of stage progress
        updated = CoreStageProgress(
            current_stage=stage_progress.current_stage,
            connect=dict(stage_progress.connect),
            observe=dict(stage_progress.observe),
            recommend=dict(stage_progress.recommend),
            execute=dict(stage_progress.execute),
            pbms_expressed=list(stage_progress.pbms_expressed),
            pbms_acknowledged=list(stage_progress.pbms_acknowledged),
        )

        # Apply completed items from analysis
        for item_update in analysis.stage_items_completed:
            stage_dict = self._get_stage_dict(updated, item_update.stage)
            if stage_dict and item_update.item in stage_dict:
                stage_dict[item_update.item] = item_update.completed

        # Also mark items from techniques_detected (LLM often puts technique IDs
        # here without duplicating them into stage_items_completed)
        for technique in analysis.techniques_detected:
            for stage_dict in [
                updated.connect,
                updated.observe,
                updated.recommend,
                updated.execute,
            ]:
                if technique in stage_dict:
                    stage_dict[technique] = True

        # Add acknowledged motivators
        for pbm in analysis.pbms_acknowledged:
            if pbm not in updated.pbms_acknowledged:
                updated.pbms_acknowledged.append(pbm)

        # Update current stage if suggested
        if analysis.suggested_stage:
            try:
                updated.current_stage = SalesStage(analysis.suggested_stage)
            except ValueError:
                pass  # Keep current stage if invalid

        return updated

    def _get_stage_dict(
        self,
        progress: CoreStageProgress,
        stage: str,
    ) -> dict[str, bool] | None:
        """Get the checklist dict for a stage.

        Args:
            progress: Stage progress object.
            stage: Stage name (CONNECT, OBSERVE, RECOMMEND, EXECUTE).

        Returns:
            Stage checklist dict or None.
        """
        stage_upper = stage.upper()
        if stage_upper == "CONNECT":
            return progress.connect
        elif stage_upper == "OBSERVE":
            return progress.observe
        elif stage_upper == "RECOMMEND":
            return progress.recommend
        elif stage_upper == "EXECUTE":
            return progress.execute
        return None

    def _generate_hint(
        self,
        analysis: CoachAnalysis,
        stage_progress: CoreStageProgress,
    ) -> CoachHint:
        """Generate a coaching hint from analysis.

        Args:
            analysis: Coach analysis result.
            stage_progress: Current stage progress.

        Returns:
            CoachHint for the frontend.
        """
        current_stage = stage_progress.current_stage.value

        # Use LLM example phrase, or fall back to template for non-info levels
        example_phrase = analysis.example_phrase
        if not example_phrase and analysis.intervention_level not in (
            InterventionLevel.NONE,
            InterventionLevel.INFO,
        ):
            deviation = analysis.deviations[0] if analysis.deviations else None
            example_phrase = get_example_phrase_fallback(current_stage, deviation)

        return CoachHint(
            level=analysis.intervention_level,
            hint=analysis.hint or "Continue with C.O.R.E. technique.",
            stage=current_stage,
            example_phrase=example_phrase,
            ready_for_next_stage=analysis.ready_for_next_stage,
        )

    async def generate_evaluation(
        self,
        session_id: str,
        user_id: str,
        state: CustomerAgentState,
        session_mode: SessionType = SessionType.EVALUATION,
    ) -> Evaluation:
        """Generate and save a post-session evaluation.

        Args:
            session_id: Session ID for the evaluation.
            user_id: User ID of the salesperson.
            state: Final customer agent state.
            session_mode: Session mode (affects deviation penalties).

        Returns:
            Created Evaluation.
        """
        stage_progress = state["stage_progress"]
        objections_raised = state.get("objections_raised", [])
        objections_resolved = state.get("objections_resolved", [])

        # Calculate scores
        deviations: list[str] = []  # Could be tracked from analysis history
        raw_score, final_score, grade = calculate_score(
            stage_progress=stage_progress,
            objections_raised=objections_raised,
            objections_resolved=objections_resolved,
            deviations=deviations if session_mode == SessionType.EVALUATION else [],
        )

        # Build scorecard
        scorecard = self._build_scorecard(
            stage_progress=stage_progress,
            objections_raised=objections_raised,
            objections_resolved=objections_resolved,
            deviations=deviations,
            raw_score=raw_score,
            final_score=final_score,
            grade=grade,
        )

        # Generate feedback — RAG-enhanced LLM feedback when enabled, else templates
        persona = state["persona"]
        if self.settings.rag_enabled and persona.property_id:
            strengths, improvements = await self._generate_llm_feedback(
                persona=persona,
                stage_progress=stage_progress,
                scorecard=scorecard,
                messages=list(state.get("messages", [])),
            )
        else:
            strengths, improvements = self._generate_feedback(stage_progress, scorecard)

        # Create evaluation
        evaluation_create = EvaluationCreate(
            session_id=session_id,
            user_id=user_id,
            scorecard=scorecard,
            summary=self._generate_summary(grade, final_score),
            strengths=strengths,
            improvements=improvements,
            techniques_detected=self._get_detected_techniques(stage_progress),
        )

        # Save to repository
        evaluation = await self.evaluation_repository.create(evaluation_create)

        return evaluation

    def _build_scorecard(
        self,
        stage_progress: CoreStageProgress,
        objections_raised: list[str],
        objections_resolved: list[str],
        deviations: list[str],
        raw_score: float,
        final_score: float,
        grade: Grade,
    ) -> EvaluationScorecard:
        """Build a complete scorecard from stage progress.

        Args:
            stage_progress: Progress through stages.
            objections_raised: Customer objections.
            objections_resolved: Resolved objections.
            deviations: C.O.R.E. deviations.
            raw_score: Calculated raw score.
            final_score: Final score with bonuses/penalties.
            grade: Letter grade.

        Returns:
            EvaluationScorecard.
        """
        from app.agents.coach.scorer import (
            calculate_deviation_penalty,
            calculate_objection_penalty,
            calculate_pbm_bonus,
            calculate_stage_score,
        )

        # Build stage scores
        stage_scores: dict[str, StageScore] = {}

        # CONNECT
        connect_completed = [k for k, v in stage_progress.connect.items() if v]
        connect_total = list(stage_progress.connect.keys())
        stage_scores["CONNECT"] = StageScore(
            stage="CONNECT",
            items_completed=connect_completed,
            items_total=connect_total,
            score=calculate_stage_score(connect_completed, connect_total),
            weight=0.15,
            feedback=None,
        )

        # OBSERVE
        observe_completed = [k for k, v in stage_progress.observe.items() if v]
        observe_total = list(stage_progress.observe.keys())
        stage_scores["OBSERVE"] = StageScore(
            stage="OBSERVE",
            items_completed=observe_completed,
            items_total=observe_total,
            score=calculate_stage_score(observe_completed, observe_total),
            weight=0.30,
            feedback=None,
        )

        # RECOMMEND
        recommend_completed = [k for k, v in stage_progress.recommend.items() if v]
        recommend_total = list(stage_progress.recommend.keys())
        stage_scores["RECOMMEND"] = StageScore(
            stage="RECOMMEND",
            items_completed=recommend_completed,
            items_total=recommend_total,
            score=calculate_stage_score(recommend_completed, recommend_total),
            weight=0.30,
            feedback=None,
        )

        # EXECUTE
        execute_completed = [k for k, v in stage_progress.execute.items() if v]
        execute_total = list(stage_progress.execute.keys())
        stage_scores["EXECUTE"] = StageScore(
            stage="EXECUTE",
            items_completed=execute_completed,
            items_total=execute_total,
            score=calculate_stage_score(execute_completed, execute_total),
            weight=0.25,
            feedback=None,
        )

        # Calculate bonuses/penalties
        pbm_match_rate = (
            len(stage_progress.pbms_acknowledged) / len(stage_progress.pbms_expressed)
            if stage_progress.pbms_expressed
            else 0.0
        )
        pbm_bonus = calculate_pbm_bonus(
            stage_progress.pbms_expressed, stage_progress.pbms_acknowledged
        )
        objection_penalty = calculate_objection_penalty(objections_raised, objections_resolved)
        objection_rate = (
            len(objections_resolved) / len(objections_raised) if objections_raised else 0.0
        )
        deviation_penalty = calculate_deviation_penalty(deviations)

        return EvaluationScorecard(
            stage_scores=stage_scores,
            pbms_expressed=stage_progress.pbms_expressed,
            pbms_acknowledged=stage_progress.pbms_acknowledged,
            pbm_match_rate=pbm_match_rate,
            pbm_bonus=pbm_bonus,
            objections_raised=objections_raised,
            objections_resolved=objections_resolved,
            objection_resolution_rate=objection_rate,
            objection_penalty=objection_penalty,
            deviations=deviations,
            deviation_penalty=deviation_penalty,
            raw_score=raw_score,
            final_score=final_score,
            grade=grade,
        )

    async def _generate_llm_feedback(
        self,
        persona: CustomerPersona,
        stage_progress: CoreStageProgress,
        scorecard: EvaluationScorecard,
        messages: list[BaseMessage],
    ) -> tuple[list[str], list[str]]:
        """Generate specific, property-aware feedback using RAG context + Gemini.

        Fetches the property's objection handlers and agent talking points from
        Firestore, then asks Gemini to produce targeted strengths and improvement
        areas that reference the actual property scripts.

        Falls back to template feedback on any failure.
        """
        from app.services.rag_service import get_rag_service

        try:
            rag = get_rag_service()
            objection_context, talking_points_context = await asyncio.gather(
                rag.retrieve(
                    query="objection handling scripts and responses",
                    product_category=persona.property_id,
                    product_type="property_listing",
                    section_type="objection_handlers",
                    top_k=1,
                ),
                rag.retrieve(
                    query="agent talking points and memorizable scripts",
                    product_category=persona.property_id,
                    product_type="property_listing",
                    section_type="agent_talking_points",
                    top_k=1,
                ),
            )
        except Exception as e:
            logger.warning(f"RAG fetch for evaluation feedback failed: {e}")
            return self._generate_feedback(stage_progress, scorecard)

        if not objection_context and not talking_points_context:
            return self._generate_feedback(stage_progress, scorecard)

        property_context = ""
        if objection_context:
            property_context += f"OBJECTION HANDLERS:\n{objection_context}\n\n"
        if talking_points_context:
            property_context += f"AGENT TALKING POINTS:\n{talking_points_context}"

        # Summarise conversation for context (last 10 salesperson turns)
        from langchain_core.messages import HumanMessage

        sp_turns = [str(m.content) for m in messages if isinstance(m, HumanMessage)][-10:]
        conversation_summary = "\n".join(f"- {t}" for t in sp_turns) or "(no messages recorded)"

        prompt = f"""You are evaluating a real estate sales training session.
The trainee was practicing selling {persona.name}'s property scenario.

## Session Scorecard
- CONNECT:    {scorecard.stage_scores["CONNECT"].score:.0f}%  (items: {", ".join(scorecard.stage_scores["CONNECT"].items_completed) or "none"})
- OBSERVE:    {scorecard.stage_scores["OBSERVE"].score:.0f}%  (items: {", ".join(scorecard.stage_scores["OBSERVE"].items_completed) or "none"})
- RECOMMEND:  {scorecard.stage_scores["RECOMMEND"].score:.0f}%  (items: {", ".join(scorecard.stage_scores["RECOMMEND"].items_completed) or "none"})
- EXECUTE:    {scorecard.stage_scores["EXECUTE"].score:.0f}%  (items: {", ".join(scorecard.stage_scores["EXECUTE"].items_completed) or "none"})
- Objections raised: {len(scorecard.objections_raised)}, resolved: {len(scorecard.objections_resolved)}
- Customer motivators expressed: {", ".join(scorecard.pbms_expressed) or "none"}
- Customer motivators acknowledged: {", ".join(scorecard.pbms_acknowledged) or "none"}
- Final score: {scorecard.final_score:.0f} / 100  (grade: {scorecard.grade})

## What the Trainee Said (salesperson turns)
{conversation_summary}

## Property Reference Material
{property_context}

## Your Task
Generate 3-4 specific strengths and 3-4 specific improvement areas.
Reference specific property details where relevant (e.g. "You correctly addressed the roof objection" or "You missed the opportunity to mention the 2020 HVAC replacement").
Be direct, concrete, and actionable — avoid generic coaching clichés.

Respond with ONLY valid JSON:
{{"strengths": ["...", "..."], "improvements": ["...", "..."]}}"""

        try:
            result = await self.provider.complete_structured(
                [ChatMessage(ChatRole.USER, prompt)],
                response_schema=FeedbackResponse,
                model=self.settings.coach_model,
                temperature=0.3,
                max_output_tokens=1024,
            )
            if isinstance(result.parsed, FeedbackResponse) and (
                result.parsed.strengths or result.parsed.improvements
            ):
                return result.parsed.strengths, result.parsed.improvements
        except Exception as e:
            logger.warning(f"LLM feedback generation failed, using templates: {e}")

        return self._generate_feedback(stage_progress, scorecard)

    def _generate_feedback(
        self,
        stage_progress: CoreStageProgress,
        scorecard: EvaluationScorecard,
    ) -> tuple[list[str], list[str]]:
        """Generate strengths and improvement areas.

        Args:
            stage_progress: Progress through stages.
            scorecard: Evaluation scorecard.

        Returns:
            Tuple of (strengths, improvements).
        """
        strengths: list[str] = []
        improvements: list[str] = []

        # Check each stage
        for stage_name, stage_score in scorecard.stage_scores.items():
            if stage_score.score >= 66.0:
                strengths.append(f"Strong {stage_name} stage performance")
            elif stage_score.score < 33.0:
                improvements.append(f"Focus on {stage_name} stage techniques")

        # Customer Motivator handling
        if scorecard.pbm_match_rate >= 0.8:
            strengths.append("Excellent customer motivator acknowledgment")
        elif scorecard.pbm_match_rate < 0.5:
            improvements.append("Work on acknowledging customer motivators")

        # Objection handling
        if scorecard.objection_resolution_rate >= 0.8:
            strengths.append("Good objection handling")
        elif scorecard.objection_resolution_rate < 0.5 and scorecard.objections_raised:
            improvements.append("Improve objection resolution techniques")

        return strengths, improvements

    def _generate_summary(self, grade: Grade, score: float) -> str:
        """Generate a natural language summary.

        Args:
            grade: Letter grade.
            score: Final score.

        Returns:
            Summary string.
        """
        summaries = {
            Grade.A: f"Excellent performance (Score: {score:.0f}). Demonstrated strong C.O.R.E. technique execution.",
            Grade.B: f"Good performance (Score: {score:.0f}). Solid fundamentals with room for refinement.",
            Grade.C: f"Satisfactory performance (Score: {score:.0f}). Core techniques need strengthening.",
            Grade.D: f"Below average performance (Score: {score:.0f}). Review C.O.R.E. fundamentals.",
            Grade.F: f"Needs improvement (Score: {score:.0f}). Focus on building basic selling skills.",
        }
        return summaries.get(grade, f"Score: {score:.0f}")

    def _get_detected_techniques(
        self,
        stage_progress: CoreStageProgress,
    ) -> list[str]:
        """Get list of detected techniques from stage progress.

        Args:
            stage_progress: Progress through stages.

        Returns:
            List of completed technique IDs.
        """
        techniques: list[str] = []

        for item, done in stage_progress.connect.items():
            if done:
                techniques.append(item)
        for item, done in stage_progress.observe.items():
            if done:
                techniques.append(item)
        for item, done in stage_progress.recommend.items():
            if done:
                techniques.append(item)
        for item, done in stage_progress.execute.items():
            if done:
                techniques.append(item)

        return techniques
