"""Coach analyzer using Gemini 2.0 Flash for LLM-based analysis.

This module provides the CoachAnalyzer class that analyzes salesperson
messages for E.A.S.Y. technique usage and provides coaching feedback.
"""

import json
import logging
from typing import Any

from google import genai
from google.genai import types
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agents.coach.hints import get_intervention_message
from app.agents.coach.prompts import build_coach_prompt, format_conversation_history
from app.agents.state import CoreStageProgress, CustomerPersona
from app.config import get_settings
from app.models.coach import CoachAnalysis, InterventionLevel, StageItemUpdate

logger = logging.getLogger(__name__)

# Default model for coach analysis
DEFAULT_COACH_MODEL = "gemini-2.0-flash"


class CoachAnalyzer:
    """LLM-based analyzer for salesperson messages.

    Uses Gemini 2.0 Flash to analyze salesperson messages and detect
    E.A.S.Y. selling techniques, deviations, and determine interventions.
    """

    def __init__(self, model: str | None = None) -> None:
        """Initialize the coach analyzer.

        Args:
            model: Gemini model to use. Defaults to gemini-2.0-flash.
        """
        settings = get_settings()
        self._model = model or settings.coach_model or DEFAULT_COACH_MODEL
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        """Get or create the Gemini client."""
        if self._client is None:
            settings = get_settings()
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    async def analyze(
        self,
        salesperson_message: str,
        messages: list[BaseMessage],
        persona: CustomerPersona,
        stage_progress: CoreStageProgress,
    ) -> CoachAnalysis:
        """Analyze a salesperson message for E.A.S.Y. technique usage.

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
            # Call Gemini for analysis
            response = await self._call_gemini(prompt)

            # Parse the response
            analysis = self._parse_response(response, stage_progress.current_stage.value)

            return analysis

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

    async def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API for analysis.

        Args:
            prompt: The analysis prompt

        Returns:
            Raw response text from Gemini
        """
        response = await self.client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for consistent analysis
                max_output_tokens=1024,
            ),
        )

        if response.text:
            return response.text
        return "{}"

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

    def _parse_response(self, response_text: str, current_stage: str) -> CoachAnalysis:
        """Parse Gemini response into CoachAnalysis.

        Args:
            response_text: Raw JSON response from Gemini
            current_stage: Current E.A.S.Y. stage for fallback hints

        Returns:
            Parsed CoachAnalysis object
        """
        try:
            # Clean the response (remove markdown code blocks if present)
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                # Remove markdown code block
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

            data: dict[str, Any] = json.loads(cleaned)

            # Parse techniques detected
            techniques = data.get("techniques_detected", [])

            # Parse stage items completed
            stage_items_raw = data.get("stage_items_completed", {})
            stage_items: list[StageItemUpdate] = []
            for stage, items in stage_items_raw.items():
                for item in items:
                    stage_items.append(StageItemUpdate(stage=stage, item=item, completed=True))

            # Parse PBMs acknowledged
            pbms = data.get("pbms_acknowledged", [])

            # Parse deviations
            deviations = data.get("deviations", [])

            # Parse intervention level
            level_str = data.get("intervention_level", "none").lower()
            try:
                intervention_level = InterventionLevel(level_str)
            except ValueError:
                intervention_level = InterventionLevel.NONE

            # Get hint (use LLM hint or generate from templates)
            hint = data.get("hint")
            if not hint and intervention_level != InterventionLevel.NONE:
                # Generate hint from templates
                deviation = deviations[0] if deviations else None
                technique = techniques[0] if techniques else None
                hint = get_intervention_message(
                    level=intervention_level,
                    stage=current_stage,
                    deviation=deviation,
                    technique=technique,
                )

            # Parse suggested stage
            suggested_stage = data.get("suggested_stage")

            # Parse example phrase
            example_phrase = data.get("example_phrase")

            # Parse ready for next stage
            ready_for_next_stage = bool(data.get("ready_for_next_stage", False))

            return CoachAnalysis(
                techniques_detected=techniques,
                stage_items_completed=stage_items,
                pbms_acknowledged=pbms,
                deviations=deviations,
                intervention_level=intervention_level,
                hint=hint,
                example_phrase=example_phrase,
                ready_for_next_stage=ready_for_next_stage,
                suggested_stage=suggested_stage,
                confidence=1.0,
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse coach response as JSON: {e}")
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
