"""Coach analyzer using Gemini 2.0 Flash for LLM-based analysis.

This module provides the CoachAnalyzer class that analyzes salesperson
messages for C.O.R.E. technique usage and provides coaching feedback.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langfuse import get_client

from app.agents.coach.hints import get_intervention_message
from app.agents.coach.prompts import build_coach_prompt, format_conversation_history
from app.agents.state import CoreStageProgress, CustomerPersona
from app.config import get_settings
from app.llm_providers import ChatMessage, ChatRole, GeminiProvider, LLMProvider
from app.models.coach import CoachAnalysis, CoachAnalysisResponse, InterventionLevel

logger = logging.getLogger(__name__)


class CoachAnalyzer:
    """LLM-based analyzer for salesperson messages.

    Uses Gemini 2.5 Flash to analyze salesperson messages and detect
    C.O.R.E. selling techniques, deviations, and determine interventions.
    """

    def __init__(self, model: str | None = None, provider: LLMProvider | None = None) -> None:
        """Initialize the coach analyzer.

        Args:
            model: Model to use. Defaults to settings.coach_model
                (model IDs are operational config, not code constants).
            provider: LLM provider for analysis calls. Defaults to Gemini;
                the eval harness injects alternatives here.
        """
        settings = get_settings()
        self._model = model or settings.coach_model
        self._provider: LLMProvider = provider or GeminiProvider(settings)

    async def analyze(
        self,
        salesperson_message: str,
        messages: list[BaseMessage],
        persona: CustomerPersona,
        stage_progress: CoreStageProgress,
    ) -> CoachAnalysis:
        """Analyze a salesperson message for C.O.R.E. technique usage.

        Args:
            salesperson_message: The message to analyze
            messages: Full conversation history
            persona: Customer persona for context
            stage_progress: Current progress through stages

        Returns:
            CoachAnalysis with techniques detected, deviations, and intervention
        """
        # Format conversation history for prompt
        history_tuples = self._messages_to_tuples(messages)
        conversation_history = format_conversation_history(history_tuples)

        settings = get_settings()

        # Detect objections in last customer message (non-blocking on failure)
        objection_context = ""
        if settings.rag_use_objection_lookup:
            objection_context = self._get_objection_context(messages)

        # Retrieve property context via RAG (non-blocking on failure)
        # Filter by property_id so we only retrieve chunks for this specific property.
        # section_type narrows retrieval by stage: objection handlers in EXECUTE,
        # talking points in RECOMMEND, broad context otherwise.
        product_context = ""
        if settings.rag_enabled and persona.property_id:
            p_category = persona.property_id
            p_type = "property_listing"
            current_stage = stage_progress.current_stage.value
            section_type: str | None = None
            if current_stage == "EXECUTE":
                section_type = "objection_handlers"
            elif current_stage == "RECOMMEND":
                section_type = "agent_talking_points"

            if settings.rag_use_reranking:
                product_context = await self._get_reranked_product_context(
                    salesperson_message, settings, p_category, p_type
                )
            elif settings.rag_use_conversation_context:
                product_context = await self._get_product_context_with_history(
                    salesperson_message, history_tuples, p_category, p_type, section_type
                )
            elif settings.rag_use_hybrid_search:
                product_context = await self._get_hybrid_product_context(
                    salesperson_message, p_category, p_type, section_type
                )
            else:
                product_context = await self._get_product_context(
                    salesperson_message, p_category, p_type, section_type
                )

        # Build the analysis prompt
        prompt = build_coach_prompt(
            salesperson_message=salesperson_message,
            persona=persona,
            stage_progress=stage_progress,
            conversation_history=conversation_history,
            product_context=product_context,
            objection_context=objection_context,
        )

        try:
            # Call Gemini for analysis (native structured output)
            parsed = await self._call_gemini(prompt)

            return self._finalize_analysis(parsed, stage_progress.current_stage.value)

        except Exception as e:
            logger.error(f"Coach analysis failed: {e}")
            # Return a safe default on error
            return CoachAnalysis(
                techniques_detected=[],
                stage_items_completed=[],
                pbms_acknowledged=[],
                deviations=[],
                intervention_level=InterventionLevel.NONE,
                hint=None,
                suggested_stage=None,
                confidence=0.0,
            )

    def _get_objection_context(self, messages: list[BaseMessage]) -> str:
        """Detect objections in the last customer message.

        Args:
            messages: Full conversation history

        Returns:
            Objection resolution context string, or empty string
        """
        try:
            from app.services.objection_service import get_objection_service

            # Find last customer message (AIMessage in this system)
            last_customer_msg = ""
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    last_customer_msg = str(msg.content)
                    break

            if not last_customer_msg:
                return ""

            service = get_objection_service()
            objection = service.detect_objection(last_customer_msg)
            if objection:
                return service.get_resolution_context(objection)
            return ""
        except Exception as e:
            logger.warning(f"Objection detection failed (non-blocking): {e}")
            return ""

    async def _get_reranked_product_context(
        self,
        query: str,
        settings: Any,
        product_category: str | None = None,
        product_type: str | None = None,
    ) -> str:
        """Retrieve product context with LLM re-ranking.

        Args:
            query: The salesperson message
            settings: Application settings for reranking config
            product_category: Optional category filter for RAG retrieval
            product_type: Optional type filter for RAG retrieval

        Returns:
            Product context string, or empty string on failure
        """
        try:
            from app.services.rag_service import get_rag_service

            rag_service = get_rag_service()
            return await rag_service.retrieve_with_reranking(
                query=query,
                product_category=product_category,
                product_type=product_type,
                initial_k=settings.rag_reranking_initial_k,
                final_k=settings.rag_reranking_final_k,
                use_hybrid=settings.rag_use_hybrid_search,
                reranking_model=settings.rag_reranking_model,
            )
        except Exception as e:
            logger.warning(f"Re-ranked RAG retrieval failed (non-blocking): {e}")
            return ""

    async def _get_product_context_with_history(
        self,
        query: str,
        conversation_history: list[tuple[str, str]],
        product_category: str | None = None,
        product_type: str | None = None,
        section_type: str | None = None,
    ) -> str:
        """Retrieve product context using conversation-aware query enhancement."""
        try:
            from app.services.rag_service import get_rag_service

            rag_service = get_rag_service()
            return await rag_service.retrieve_with_context(
                query=query,
                conversation_history=conversation_history,
                product_category=product_category,
                product_type=product_type,
                section_type=section_type,
            )
        except Exception as e:
            logger.warning(f"Conversation-aware RAG retrieval failed (non-blocking): {e}")
            return ""

    async def _get_hybrid_product_context(
        self,
        query: str,
        product_category: str | None = None,
        product_type: str | None = None,
        section_type: str | None = None,
    ) -> str:
        """Retrieve product context using hybrid search (semantic + keyword)."""
        try:
            from app.services.rag_service import get_rag_service

            rag_service = get_rag_service()
            return await rag_service.hybrid_retrieve(
                query=query,
                product_category=product_category,
                product_type=product_type,
                section_type=section_type,
            )
        except Exception as e:
            logger.warning(f"Hybrid RAG retrieval failed (non-blocking): {e}")
            return ""

    async def _get_product_context(
        self,
        query: str,
        product_category: str | None = None,
        product_type: str | None = None,
        section_type: str | None = None,
    ) -> str:
        """Retrieve product context via RAG service."""
        try:
            from app.services.rag_service import get_rag_service

            rag_service = get_rag_service()
            return await rag_service.retrieve(
                query=query,
                product_category=product_category,
                product_type=product_type,
                section_type=section_type,
            )
        except Exception as e:
            logger.warning(f"RAG retrieval failed (non-blocking): {e}")
            return ""

    async def _call_gemini(self, prompt: str) -> CoachAnalysisResponse | None:
        """Call the LLM provider for analysis with native structured output.

        Args:
            prompt: The analysis prompt

        Returns:
            Parsed CoachAnalysisResponse, or None if the provider produced no
            structured output (treated as a failed analysis upstream).
        """
        langfuse = get_client()
        with langfuse.start_as_current_observation(as_type="span", name="coach-analysis"):
            result = await self._provider.complete_structured(
                [ChatMessage(ChatRole.USER, prompt)],
                response_schema=CoachAnalysisResponse,
                model=self._model,
                temperature=0.1,  # Low temperature for consistent analysis
                max_output_tokens=1024,
                # Thinking tokens come out of max_output_tokens before any JSON is
                # emitted; on this prompt they alone exceed 1024, truncating every
                # response into an unparseable one. Disabled rather than budgeted
                # around: hints must land inside the live turn, and thinking costs
                # ~9s here versus ~1s without, for no better analysis.
                thinking_budget=0,
            )

        if isinstance(result.parsed, CoachAnalysisResponse):
            return result.parsed
        return None

    def _messages_to_tuples(self, messages: list[BaseMessage]) -> list[tuple[str, str]]:
        """Convert LangChain messages to (role, content) tuples.

        Args:
            messages: List of BaseMessage objects

        Returns:
            List of (role, content) tuples
        """
        result: list[tuple[str, str]] = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                result.append(("user", str(msg.content)))
            elif isinstance(msg, AIMessage):
                result.append(("assistant", str(msg.content)))
        return result

    def _finalize_analysis(
        self, parsed: CoachAnalysisResponse | None, current_stage: str
    ) -> CoachAnalysis:
        """Finalize the LLM's structured output into a CoachAnalysis.

        The SDK guarantees shape and enum validity; this step keeps only the
        semantic fallbacks: no structured output at all -> safe default, and
        intervention flagged without a hint -> template hint.

        Args:
            parsed: Structured output from Gemini, or None on parse failure
            current_stage: Current C.O.R.E. stage for fallback hints

        Returns:
            Finalized CoachAnalysis object
        """
        if parsed is None:
            logger.warning("Coach response had no structured output; using safe default")
            return CoachAnalysis(
                techniques_detected=[],
                stage_items_completed=[],
                pbms_acknowledged=[],
                deviations=[],
                intervention_level=InterventionLevel.NONE,
                hint=None,
                suggested_stage=None,
                confidence=0.0,
            )

        # Use LLM hint or generate from templates
        hint = parsed.hint
        if not hint and parsed.intervention_level != InterventionLevel.NONE:
            deviation = parsed.deviations[0] if parsed.deviations else None
            technique = parsed.techniques_detected[0] if parsed.techniques_detected else None
            hint = get_intervention_message(
                level=parsed.intervention_level,
                stage=current_stage,
                deviation=deviation,
                technique=technique,
            )

        return CoachAnalysis(
            techniques_detected=parsed.techniques_detected,
            stage_items_completed=parsed.stage_items_completed,
            pbms_acknowledged=parsed.pbms_acknowledged,
            deviations=parsed.deviations,
            intervention_level=parsed.intervention_level,
            hint=hint,
            example_phrase=parsed.example_phrase,
            ready_for_next_stage=parsed.ready_for_next_stage,
            suggested_stage=parsed.suggested_stage,
            confidence=1.0,
        )

    def analyze_sync(
        self,
        salesperson_message: str,
        messages: list[BaseMessage],
        persona: CustomerPersona,
        stage_progress: CoreStageProgress,
    ) -> CoachAnalysis:
        """Synchronous version of analyze for testing.

        Args:
            salesperson_message: The message to analyze
            messages: Full conversation history
            persona: Customer persona for context
            stage_progress: Current progress through stages

        Returns:
            CoachAnalysis with techniques detected, deviations, and intervention
        """
        import asyncio

        return asyncio.run(self.analyze(salesperson_message, messages, persona, stage_progress))
