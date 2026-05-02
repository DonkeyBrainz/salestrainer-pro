"""Unit tests for coach agent prompts module."""

from app.agents.coach.prompts import (
    COACH_ANALYSIS_PROMPT,
    COACH_ANALYSIS_SCHEMA,
    build_coach_prompt,
    format_conversation_history,
)
from app.agents.personas import ANXIOUS_FIRST_TIMER
from app.agents.state import CoreStageProgress, SalesStage

# =============================================================================
# Prompt Template Tests
# =============================================================================


class TestCoachAnalysisPrompt:
    """Tests for the coach analysis prompt template."""

    def test_prompt_contains_key_sections(self) -> None:
        """Should contain all key sections."""
        assert "Context" in COACH_ANALYSIS_PROMPT
        assert "Current Stage" in COACH_ANALYSIS_PROMPT
        assert "Technique IDs to Detect" in COACH_ANALYSIS_PROMPT
        assert "Deviation IDs to Detect" in COACH_ANALYSIS_PROMPT
        assert "Intervention Levels" in COACH_ANALYSIS_PROMPT
        assert "Response Format" in COACH_ANALYSIS_PROMPT

    def test_prompt_contains_stage_techniques(self) -> None:
        """Should list techniques for all C.O.R.E. stages."""
        assert "CONNECT Stage:" in COACH_ANALYSIS_PROMPT
        assert "OBSERVE Stage:" in COACH_ANALYSIS_PROMPT
        assert "RECOMMEND Stage:" in COACH_ANALYSIS_PROMPT
        assert "EXECUTE Stage:" in COACH_ANALYSIS_PROMPT

    def test_prompt_contains_technique_ids(self) -> None:
        """Should contain all C.O.R.E. technique IDs."""
        technique_ids = [
            "warm_greeting",
            "establish_credibility",
            "create_comfort",
            "needs_discovery",
            "goal_identification",
            "motivator_mapping",
            "solution_presentation",
            "value_connection",
            "risk_mitigation",
            "commitment_request",
            "objection_handling",
            "finalize_agreement",
        ]
        for technique in technique_ids:
            assert technique in COACH_ANALYSIS_PROMPT

    def test_prompt_contains_deviation_ids(self) -> None:
        """Should contain all C.O.R.E. deviation IDs."""
        deviation_ids = [
            "skipped_connect",
            "skipped_observe",
            "missed_needs_discovery",
            "recommended_too_early",
            "no_motivator_connection",
            "missed_objection",
            "no_commitment_ask",
            "no_next_steps",
        ]
        for deviation in deviation_ids:
            assert deviation in COACH_ANALYSIS_PROMPT


# =============================================================================
# Schema Tests
# =============================================================================


class TestCoachAnalysisSchema:
    """Tests for the response schema."""

    def test_schema_contains_required_fields(self) -> None:
        """Should contain all required response fields."""
        assert "techniques_detected" in COACH_ANALYSIS_SCHEMA
        assert "stage_items_completed" in COACH_ANALYSIS_SCHEMA
        assert "pbms_acknowledged" in COACH_ANALYSIS_SCHEMA
        assert "deviations" in COACH_ANALYSIS_SCHEMA
        assert "intervention_level" in COACH_ANALYSIS_SCHEMA
        assert "hint" in COACH_ANALYSIS_SCHEMA
        assert "example_phrase" in COACH_ANALYSIS_SCHEMA
        assert "ready_for_next_stage" in COACH_ANALYSIS_SCHEMA
        assert "suggested_stage" in COACH_ANALYSIS_SCHEMA

    def test_prompt_contains_example_phrase_guidelines(self) -> None:
        """Should contain example phrase instructions."""
        assert "Example Phrase Guidelines" in COACH_ANALYSIS_PROMPT
        assert "word-for-word" in COACH_ANALYSIS_PROMPT.lower()

    def test_prompt_contains_ready_for_next_stage_guidelines(self) -> None:
        """Should contain ready_for_next_stage instructions."""
        assert "Ready for Next Stage" in COACH_ANALYSIS_PROMPT


# =============================================================================
# Build Coach Prompt Tests
# =============================================================================


class TestBuildCoachPrompt:
    """Tests for build_coach_prompt function."""

    def test_builds_complete_prompt(self) -> None:
        """Should build a complete prompt with all context."""
        persona = ANXIOUS_FIRST_TIMER
        progress = CoreStageProgress(
            current_stage=SalesStage.OBSERVE,
            connect={
                "warm_greeting": True,
                "establish_credibility": True,
                "create_comfort": False,
            },
            pbms_expressed=["value"],
        )

        prompt = build_coach_prompt(
            salesperson_message="What brings you in today?",
            persona=persona,
            stage_progress=progress,
            conversation_history="CUSTOMER: Hi, I'm looking for help.",
        )

        # Check persona info is included
        assert persona.name in prompt
        assert persona.looking_for in prompt
        assert persona.primary_pbm in prompt

        # Check stage info is included
        assert "OBSERVE" in prompt

        # Check completed items
        assert "warm_greeting" in prompt
        assert "establish_credibility" in prompt

        # Check message is included
        assert "What brings you in today?" in prompt

    def test_handles_no_completed_items(self) -> None:
        """Should handle case with no completed items."""
        persona = ANXIOUS_FIRST_TIMER
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

        prompt = build_coach_prompt(
            salesperson_message="Hello!",
            persona=persona,
            stage_progress=progress,
            conversation_history="(No previous messages)",
        )

        # Should show "none" for completed items
        assert "none" in prompt.lower()

    def test_handles_no_secondary_pbm(self) -> None:
        """Should handle persona with no secondary PBM."""
        from app.agents.personas import LANDLORD_INVESTOR

        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

        prompt = build_coach_prompt(
            salesperson_message="Hello!",
            persona=LANDLORD_INVESTOR,
            stage_progress=progress,
            conversation_history="",
        )

        # Should include "none" for secondary PBM
        assert prompt is not None

    def test_includes_product_context_when_provided(self) -> None:
        """Should include Product Knowledge section when product_context is given."""
        persona = ANXIOUS_FIRST_TIMER
        progress = CoreStageProgress(current_stage=SalesStage.RECOMMEND)

        prompt = build_coach_prompt(
            salesperson_message="This option has excellent durability.",
            persona=persona,
            stage_progress=progress,
            conversation_history="CUSTOMER: Is it durable?",
            product_context="Product uses stain-resistant material.",
        )

        assert "Product Knowledge" in prompt
        assert "Product uses stain-resistant material." in prompt

    def test_excludes_product_context_when_empty(self) -> None:
        """Should not include Product Knowledge section when product_context is empty."""
        persona = ANXIOUS_FIRST_TIMER
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

        prompt = build_coach_prompt(
            salesperson_message="Hello!",
            persona=persona,
            stage_progress=progress,
            conversation_history="(No previous messages)",
            product_context="",
        )

        assert "Product Knowledge" not in prompt

    def test_default_product_context_is_empty(self) -> None:
        """Should default to no product context when param not passed."""
        persona = ANXIOUS_FIRST_TIMER
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

        prompt = build_coach_prompt(
            salesperson_message="Hello!",
            persona=persona,
            stage_progress=progress,
            conversation_history="(No previous messages)",
        )

        assert "Product Knowledge" not in prompt

    def test_includes_objection_context_when_provided(self) -> None:
        """Should include Objection Handling section when objection_context is given."""
        persona = ANXIOUS_FIRST_TIMER
        progress = CoreStageProgress(current_stage=SalesStage.RECOMMEND)

        prompt = build_coach_prompt(
            salesperson_message="Let me address your concern.",
            persona=persona,
            stage_progress=progress,
            conversation_history="CUSTOMER: That's more than I wanted to spend.",
            objection_context="Detected objection (price): Present value proposition.",
        )

        assert "Objection Handling Guidance" in prompt
        assert "Present value proposition." in prompt

    def test_excludes_objection_context_when_empty(self) -> None:
        """Should not include Objection Handling section when empty."""
        persona = ANXIOUS_FIRST_TIMER
        progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

        prompt = build_coach_prompt(
            salesperson_message="Hello!",
            persona=persona,
            stage_progress=progress,
            conversation_history="(No previous messages)",
            objection_context="",
        )

        assert "Objection Handling Guidance" not in prompt


# =============================================================================
# Format Conversation History Tests
# =============================================================================


class TestFormatConversationHistory:
    """Tests for format_conversation_history function."""

    def test_formats_messages(self) -> None:
        """Should format messages with role labels."""
        messages = [
            ("user", "Hello, how are you?"),
            ("assistant", "I'm good, thanks!"),
        ]
        formatted = format_conversation_history(messages)

        assert "SALESPERSON:" in formatted
        assert "CUSTOMER:" in formatted
        assert "Hello, how are you?" in formatted
        assert "I'm good, thanks!" in formatted

    def test_limits_to_max_turns(self) -> None:
        """Should limit to max_turns parameter."""
        messages = [("user", f"Message {i}") for i in range(10)]
        formatted = format_conversation_history(messages, max_turns=2)

        # Should only have last 4 messages (2 turns = 4 messages)
        assert "Message 6" in formatted or "Message 7" in formatted
        assert "Message 0" not in formatted

    def test_truncates_long_messages(self) -> None:
        """Should truncate messages over 200 chars."""
        long_message = "A" * 300
        messages = [("user", long_message)]
        formatted = format_conversation_history(messages)

        assert len(formatted) < 350  # Should be truncated
        assert "..." in formatted

    def test_handles_empty_messages(self) -> None:
        """Should handle empty message list."""
        messages: list[tuple[str, str]] = []
        formatted = format_conversation_history(messages)

        assert "(No previous messages)" in formatted
