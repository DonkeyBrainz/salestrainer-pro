"""Unit tests for coach agent analyzer module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.coach.analyzer import CoachAnalyzer
from app.agents.personas import ANXIOUS_FIRST_TIMER, OPTIMISTIC_RENOVATOR
from app.agents.state import CoreStageProgress, SalesStage
from app.models.coach import InterventionLevel

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def analyzer() -> CoachAnalyzer:
    """Create a CoachAnalyzer instance."""
    return CoachAnalyzer(model="gemini-2.0-flash")


@pytest.fixture
def sample_messages() -> list[HumanMessage | AIMessage]:
    """Sample conversation messages."""
    return [
        HumanMessage(content="Hi there!"),
        AIMessage(content="Hello! How can I help you today?"),
        HumanMessage(content="I'm looking for a sofa."),
    ]


@pytest.fixture
def sample_progress() -> CoreStageProgress:
    """Sample stage progress."""
    return CoreStageProgress(
        current_stage=SalesStage.OBSERVE,
        connect={
            "warm_greeting": True,
            "establish_credibility": True,
            "create_comfort": False,
        },
    )


# =============================================================================
# Initialization Tests
# =============================================================================


class TestCoachAnalyzerInit:
    """Tests for CoachAnalyzer initialization."""

    def test_default_model(self) -> None:
        """Should use default model when not specified."""
        analyzer = CoachAnalyzer()
        assert analyzer._model is not None

    def test_custom_model(self) -> None:
        """Should use custom model when specified."""
        analyzer = CoachAnalyzer(model="custom-model")
        assert analyzer._model == "custom-model"


# =============================================================================
# Message Conversion Tests
# =============================================================================


class TestMessagesToTuples:
    """Tests for _messages_to_tuples method."""

    def test_converts_human_messages(self, analyzer: CoachAnalyzer) -> None:
        """Should convert HumanMessage to user tuple."""
        messages = [HumanMessage(content="Hello")]
        tuples = analyzer._messages_to_tuples(messages)

        assert len(tuples) == 1
        assert tuples[0] == ("user", "Hello")

    def test_converts_ai_messages(self, analyzer: CoachAnalyzer) -> None:
        """Should convert AIMessage to assistant tuple."""
        messages = [AIMessage(content="Hi there")]
        tuples = analyzer._messages_to_tuples(messages)

        assert len(tuples) == 1
        assert tuples[0] == ("assistant", "Hi there")

    def test_converts_mixed_messages(self, analyzer: CoachAnalyzer, sample_messages: list) -> None:
        """Should convert mixed message list."""
        tuples = analyzer._messages_to_tuples(sample_messages)

        assert len(tuples) == 3
        assert tuples[0][0] == "user"
        assert tuples[1][0] == "assistant"
        assert tuples[2][0] == "user"


# =============================================================================
# Response Parsing Tests
# =============================================================================


class TestParseResponse:
    """Tests for _parse_response method."""

    def test_parses_valid_json(self, analyzer: CoachAnalyzer) -> None:
        """Should parse valid JSON response."""
        response = """{
            "techniques_detected": ["warm_greeting"],
            "stage_items_completed": {"CONNECT": ["warm_greeting"]},
            "pbms_acknowledged": ["value"],
            "deviations": [],
            "intervention_level": "info",
            "hint": "Great rapport building!",
            "suggested_stage": null
        }"""

        result = analyzer._parse_response(response, "CONNECT")

        assert "warm_greeting" in result.techniques_detected
        assert len(result.stage_items_completed) == 1
        assert result.stage_items_completed[0].stage == "CONNECT"
        assert "value" in result.pbms_acknowledged
        assert result.intervention_level == InterventionLevel.INFO
        assert result.hint == "Great rapport building!"

    def test_parses_json_with_code_block(self, analyzer: CoachAnalyzer) -> None:
        """Should parse JSON wrapped in code block."""
        response = """```json
{
    "techniques_detected": ["needs_discovery"],
    "stage_items_completed": {},
    "pbms_acknowledged": [],
    "deviations": [],
    "intervention_level": "none",
    "hint": null,
    "suggested_stage": null
}
```"""

        result = analyzer._parse_response(response, "OBSERVE")

        assert "needs_discovery" in result.techniques_detected
        assert result.intervention_level == InterventionLevel.NONE

    def test_handles_invalid_json(self, analyzer: CoachAnalyzer) -> None:
        """Should return safe default for invalid JSON."""
        response = "This is not valid JSON"

        result = analyzer._parse_response(response, "CONNECT")

        assert result.techniques_detected == []
        assert result.intervention_level == InterventionLevel.NONE
        assert result.confidence == 0.0

    def test_handles_invalid_intervention_level(self, analyzer: CoachAnalyzer) -> None:
        """Should default to NONE for invalid intervention level."""
        response = """{
            "techniques_detected": [],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "invalid_level",
            "hint": null,
            "suggested_stage": null
        }"""

        result = analyzer._parse_response(response, "CONNECT")

        assert result.intervention_level == InterventionLevel.NONE

    def test_generates_hint_from_template(self, analyzer: CoachAnalyzer) -> None:
        """Should generate hint from template when not in response."""
        response = """{
            "techniques_detected": [],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": ["missed_needs_discovery"],
            "intervention_level": "warning",
            "hint": null,
            "example_phrase": null,
            "ready_for_next_stage": false,
            "suggested_stage": null
        }"""

        result = analyzer._parse_response(response, "OBSERVE")

        assert result.intervention_level == InterventionLevel.WARNING
        assert result.hint is not None
        assert len(result.hint) > 0

    def test_parses_example_phrase(self, analyzer: CoachAnalyzer) -> None:
        """Should parse example_phrase from response."""
        response = """{
            "techniques_detected": [],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": ["skipped_observe"],
            "intervention_level": "suggestion",
            "hint": "Try asking about their needs.",
            "example_phrase": "What brings you in today?",
            "ready_for_next_stage": false,
            "suggested_stage": null
        }"""

        result = analyzer._parse_response(response, "OBSERVE")

        assert result.example_phrase == "What brings you in today?"
        assert result.ready_for_next_stage is False

    def test_parses_ready_for_next_stage(self, analyzer: CoachAnalyzer) -> None:
        """Should parse ready_for_next_stage from response."""
        response = """{
            "techniques_detected": ["warm_greeting", "establish_credibility", "create_comfort"],
            "stage_items_completed": {
                "CONNECT": ["warm_greeting", "establish_credibility", "create_comfort"]
            },
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "info",
            "hint": "Great CONNECT stage!",
            "example_phrase": null,
            "ready_for_next_stage": true,
            "suggested_stage": "OBSERVE"
        }"""

        result = analyzer._parse_response(response, "CONNECT")

        assert result.ready_for_next_stage is True
        assert result.example_phrase is None

    def test_defaults_new_fields_when_missing(self, analyzer: CoachAnalyzer) -> None:
        """Should default example_phrase to None and ready_for_next_stage to False when missing."""
        response = """{
            "techniques_detected": [],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "none",
            "hint": null,
            "suggested_stage": null
        }"""

        result = analyzer._parse_response(response, "CONNECT")

        assert result.example_phrase is None
        assert result.ready_for_next_stage is False


# =============================================================================
# Analyze Tests (with mocked LLM)
# =============================================================================


class TestAnalyze:
    """Tests for analyze method with mocked LLM."""

    @pytest.mark.asyncio
    async def test_analyze_returns_coach_analysis(
        self,
        analyzer: CoachAnalyzer,
        sample_messages: list,
        sample_progress: CoreStageProgress,
    ) -> None:
        """Should return CoachAnalysis from analyze."""
        mock_response = """{
            "techniques_detected": ["motivator_mapping"],
            "stage_items_completed": {"OBSERVE": ["motivator_mapping"]},
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "info",
            "hint": "Good motivator identification!",
            "suggested_stage": null
        }"""

        with patch.object(analyzer, "_call_gemini", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            result = await analyzer.analyze(
                salesperson_message="What would success look like for you?",
                messages=sample_messages,
                persona=ANXIOUS_FIRST_TIMER,
                stage_progress=sample_progress,
            )

            assert "motivator_mapping" in result.techniques_detected
            assert result.intervention_level == InterventionLevel.INFO
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_handles_exception(
        self,
        analyzer: CoachAnalyzer,
        sample_messages: list,
        sample_progress: CoreStageProgress,
    ) -> None:
        """Should return safe default on exception."""
        with patch.object(analyzer, "_call_gemini", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("API error")

            result = await analyzer.analyze(
                salesperson_message="Hello",
                messages=sample_messages,
                persona=ANXIOUS_FIRST_TIMER,
                stage_progress=sample_progress,
            )

            assert result.techniques_detected == []
            assert result.intervention_level == InterventionLevel.NONE
            assert result.confidence == 0.0


# =============================================================================
# Integration-style Tests (still mocked, but fuller flow)
# =============================================================================


class TestAnalyzerIntegration:
    """Integration-style tests for analyzer."""

    @pytest.mark.asyncio
    async def test_detects_good_greeting(self) -> None:
        """Should detect good greeting technique."""
        analyzer = CoachAnalyzer()
        mock_response = """{
            "techniques_detected": ["warm_greeting", "establish_credibility"],
            "stage_items_completed": {
                "CONNECT": ["warm_greeting", "establish_credibility"]
            },
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "info",
            "hint": "Great rapport building!",
            "suggested_stage": "OBSERVE"
        }"""

        with patch.object(analyzer, "_call_gemini", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            result = await analyzer.analyze(
                salesperson_message="I'd love to understand your situation better - what brings you here today?",
                messages=[],
                persona=OPTIMISTIC_RENOVATOR,
                stage_progress=CoreStageProgress(current_stage=SalesStage.CONNECT),
            )

            assert "warm_greeting" in result.techniques_detected
            assert "establish_credibility" in result.techniques_detected
            assert result.intervention_level == InterventionLevel.INFO
            assert result.suggested_stage == "OBSERVE"

    @pytest.mark.asyncio
    async def test_detects_deviation(self) -> None:
        """Should detect deviation when skipping stages."""
        analyzer = CoachAnalyzer()
        mock_response = """{
            "techniques_detected": [],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": ["recommended_too_early", "skipped_observe"],
            "intervention_level": "warning",
            "hint": "You're presenting solutions before understanding their needs.",
            "suggested_stage": "OBSERVE"
        }"""

        with patch.object(analyzer, "_call_gemini", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            result = await analyzer.analyze(
                salesperson_message="Let me show you this solution - it's on sale!",
                messages=[HumanMessage(content="Hi")],
                persona=ANXIOUS_FIRST_TIMER,
                stage_progress=CoreStageProgress(current_stage=SalesStage.CONNECT),
            )

            assert "recommended_too_early" in result.deviations
            assert result.intervention_level == InterventionLevel.WARNING


# =============================================================================
# RAG Integration Tests
# =============================================================================


class TestAnalyzerRAGIntegration:
    """Tests for RAG integration in coach analyzer."""

    @pytest.mark.asyncio
    async def test_rag_enabled_passes_product_context(
        self,
        analyzer: CoachAnalyzer,
        sample_messages: list,
        sample_progress: CoreStageProgress,
    ) -> None:
        """Should pass RAG context to prompt when enabled."""
        mock_response = """{
            "techniques_detected": [],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "none",
            "hint": null,
            "suggested_stage": null
        }"""

        mock_settings = MagicMock()
        mock_settings.rag_enabled = True
        mock_settings.rag_use_reranking = False
        mock_settings.rag_use_conversation_context = False
        mock_settings.rag_use_hybrid_search = False
        mock_settings.rag_use_objection_lookup = False

        with (
            patch.object(analyzer, "_call_gemini", new_callable=AsyncMock) as mock_call,
            patch("app.agents.coach.analyzer.get_settings", return_value=mock_settings),
            patch(
                "app.agents.coach.analyzer.CoachAnalyzer._get_product_context",
                new_callable=AsyncMock,
                return_value="Sectional is stain-resistant.",
            ),
        ):
            mock_call.return_value = mock_response

            await analyzer.analyze(
                salesperson_message="Tell me about durability",
                messages=sample_messages,
                persona=ANXIOUS_FIRST_TIMER,
                stage_progress=sample_progress,
            )

            # Verify the prompt includes product context
            prompt_arg = mock_call.call_args[0][0]
            assert "Sectional is stain-resistant." in prompt_arg
            assert "Product Knowledge" in prompt_arg

    @pytest.mark.asyncio
    async def test_rag_disabled_no_product_context(
        self,
        analyzer: CoachAnalyzer,
        sample_messages: list,
        sample_progress: CoreStageProgress,
    ) -> None:
        """Should not include product context when RAG disabled."""
        mock_response = """{
            "techniques_detected": [],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "none",
            "hint": null,
            "suggested_stage": null
        }"""

        mock_settings = MagicMock()
        mock_settings.rag_enabled = False
        mock_settings.rag_use_objection_lookup = False

        with (
            patch.object(analyzer, "_call_gemini", new_callable=AsyncMock) as mock_call,
            patch("app.agents.coach.analyzer.get_settings", return_value=mock_settings),
        ):
            mock_call.return_value = mock_response

            await analyzer.analyze(
                salesperson_message="Tell me about durability",
                messages=sample_messages,
                persona=ANXIOUS_FIRST_TIMER,
                stage_progress=sample_progress,
            )

            prompt_arg = mock_call.call_args[0][0]
            assert "Product Knowledge" not in prompt_arg

    @pytest.mark.asyncio
    async def test_rag_failure_degrades_gracefully(
        self,
        analyzer: CoachAnalyzer,
        sample_messages: list,
        sample_progress: CoreStageProgress,
    ) -> None:
        """Should still produce analysis when RAG fails."""
        mock_response = """{
            "techniques_detected": ["goal_identification"],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "info",
            "hint": "Good question!",
            "suggested_stage": null
        }"""

        mock_settings = MagicMock()
        mock_settings.rag_enabled = True
        mock_settings.rag_use_reranking = False
        mock_settings.rag_use_conversation_context = False
        mock_settings.rag_use_hybrid_search = False
        mock_settings.rag_use_objection_lookup = False

        with (
            patch.object(analyzer, "_call_gemini", new_callable=AsyncMock) as mock_call,
            patch("app.agents.coach.analyzer.get_settings", return_value=mock_settings),
            patch(
                "app.agents.coach.analyzer.CoachAnalyzer._get_product_context",
                new_callable=AsyncMock,
                return_value="",
            ),
        ):
            mock_call.return_value = mock_response

            result = await analyzer.analyze(
                salesperson_message="Why is that important?",
                messages=sample_messages,
                persona=ANXIOUS_FIRST_TIMER,
                stage_progress=sample_progress,
            )

            assert "goal_identification" in result.techniques_detected
            assert result.intervention_level == InterventionLevel.INFO

    @pytest.mark.asyncio
    async def test_rag_receives_product_filters_from_persona(
        self,
        analyzer: CoachAnalyzer,
        sample_messages: list,
        sample_progress: CoreStageProgress,
    ) -> None:
        """Should forward persona property_id to RAG retrieval with property_listing doc type."""
        mock_response = """{
            "techniques_detected": [],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "none",
            "hint": null,
            "suggested_stage": null
        }"""

        # Persona with explicit property_id for RAG filtering
        persona_with_product = ANXIOUS_FIRST_TIMER.model_copy(
            update={"property_id": "property_1"}
        )

        mock_settings = MagicMock()
        mock_settings.rag_enabled = True
        mock_settings.rag_use_reranking = False
        mock_settings.rag_use_conversation_context = False
        mock_settings.rag_use_hybrid_search = False
        mock_settings.rag_use_objection_lookup = False

        with (
            patch.object(analyzer, "_call_gemini", new_callable=AsyncMock) as mock_call,
            patch("app.agents.coach.analyzer.get_settings", return_value=mock_settings),
            patch(
                "app.agents.coach.analyzer.CoachAnalyzer._get_product_context",
                new_callable=AsyncMock,
                return_value="Filtered product info.",
            ) as mock_retrieve,
        ):
            mock_call.return_value = mock_response

            await analyzer.analyze(
                salesperson_message="Tell me about this property",
                messages=sample_messages,
                persona=persona_with_product,
                stage_progress=sample_progress,
            )

            # CONNECT stage → section_type=None (broad context)
            mock_retrieve.assert_called_once_with(
                "Tell me about this property", "property_1", "property_listing", None
            )

    @pytest.mark.asyncio
    async def test_rag_hybrid_receives_product_filters(
        self,
        analyzer: CoachAnalyzer,
        sample_messages: list,
        sample_progress: CoreStageProgress,
    ) -> None:
        """Should forward property_id to hybrid RAG retrieval."""
        mock_response = """{
            "techniques_detected": [],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "none",
            "hint": null,
            "suggested_stage": null
        }"""

        persona_with_product = ANXIOUS_FIRST_TIMER.model_copy(
            update={"property_id": "property_6"}
        )

        mock_settings = MagicMock()
        mock_settings.rag_enabled = True
        mock_settings.rag_use_reranking = False
        mock_settings.rag_use_conversation_context = False
        mock_settings.rag_use_hybrid_search = True
        mock_settings.rag_use_objection_lookup = False

        with (
            patch.object(analyzer, "_call_gemini", new_callable=AsyncMock) as mock_call,
            patch("app.agents.coach.analyzer.get_settings", return_value=mock_settings),
            patch(
                "app.agents.coach.analyzer.CoachAnalyzer._get_hybrid_product_context",
                new_callable=AsyncMock,
                return_value="Hybrid product info.",
            ) as mock_hybrid,
        ):
            mock_call.return_value = mock_response

            await analyzer.analyze(
                salesperson_message="Show me this condo",
                messages=sample_messages,
                persona=persona_with_product,
                stage_progress=sample_progress,
            )

            # CONNECT stage → section_type=None
            mock_hybrid.assert_called_once_with("Show me this condo", "property_6", "property_listing", None)

    @pytest.mark.asyncio
    async def test_rag_forwards_persona_product_fields(
        self,
        analyzer: CoachAnalyzer,
        sample_messages: list,
        sample_progress: CoreStageProgress,
    ) -> None:
        """Should forward existing persona product fields to RAG retrieval."""
        mock_response = """{
            "techniques_detected": [],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "none",
            "hint": null,
            "suggested_stage": null
        }"""

        mock_settings = MagicMock()
        mock_settings.rag_enabled = True
        mock_settings.rag_use_reranking = False
        mock_settings.rag_use_conversation_context = False
        mock_settings.rag_use_hybrid_search = False
        mock_settings.rag_use_objection_lookup = False

        with (
            patch.object(analyzer, "_call_gemini", new_callable=AsyncMock) as mock_call,
            patch("app.agents.coach.analyzer.get_settings", return_value=mock_settings),
            patch(
                "app.agents.coach.analyzer.CoachAnalyzer._get_product_context",
                new_callable=AsyncMock,
                return_value="",
            ) as mock_retrieve,
        ):
            mock_call.return_value = mock_response

            await analyzer.analyze(
                salesperson_message="Hello",
                messages=sample_messages,
                persona=ANXIOUS_FIRST_TIMER,
                stage_progress=sample_progress,
            )

            # ANXIOUS_FIRST_TIMER has property_id="property_1"; CONNECT stage → section_type=None
            mock_retrieve.assert_called_once_with("Hello", "property_1", "property_listing", None)

    @pytest.mark.asyncio
    async def test_conversation_aware_retrieval(
        self,
        analyzer: CoachAnalyzer,
        sample_messages: list,
        sample_progress: CoreStageProgress,
    ) -> None:
        """Should use conversation-aware retrieval when enabled."""
        mock_response = """{
            "techniques_detected": [],
            "stage_items_completed": {},
            "pbms_acknowledged": [],
            "deviations": [],
            "intervention_level": "none",
            "hint": null,
            "suggested_stage": null
        }"""

        mock_settings = MagicMock()
        mock_settings.rag_enabled = True
        mock_settings.rag_use_reranking = False
        mock_settings.rag_use_conversation_context = True
        mock_settings.rag_use_objection_lookup = False

        with (
            patch.object(analyzer, "_call_gemini", new_callable=AsyncMock) as mock_call,
            patch("app.agents.coach.analyzer.get_settings", return_value=mock_settings),
            patch(
                "app.agents.coach.analyzer.CoachAnalyzer._get_product_context_with_history",
                new_callable=AsyncMock,
                return_value="Context-enhanced product info.",
            ) as mock_ctx_retrieve,
        ):
            mock_call.return_value = mock_response

            await analyzer.analyze(
                salesperson_message="Is it durable?",
                messages=sample_messages,
                persona=ANXIOUS_FIRST_TIMER,
                stage_progress=sample_progress,
            )

            mock_ctx_retrieve.assert_called_once()
            prompt_arg = mock_call.call_args[0][0]
            assert "Context-enhanced product info." in prompt_arg
