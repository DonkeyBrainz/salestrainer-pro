"""Unit tests for LangGraph agent state schemas and registries."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents import (
    CoreStageProgress,
    CustomerAgentState,
    CustomerPersona,
    Difficulty,
    Mood,
    ObjectionDifficulty,
    RegardLevel,
    SalesStage,
    Timeline,
)
from app.agents.personas import (
    ANXIOUS_FIRST_TIMER,
    LANDLORD_INVESTOR,
    OPTIMISTIC_RENOVATOR,
    PERSONAS,
    PRACTICAL_FAMILY,
    WEALTHY_SKEPTIC,
    get_persona,
    get_personas_by_difficulty,
    list_all_personas,
)
from app.data import (
    ALL_OBJECTIONS,
    CORE_FULL_CONTEXT,
    CORE_STAGES,
    CUSTOMER_MOTIVATORS,
    ObjectionCategory,
    get_objection_texts,
    get_objections_by_category,
    get_objections_by_difficulty,
    get_stage_content,
    get_stage_requirements,
)

# =============================================================================
# CustomerPersona Tests
# =============================================================================


class TestCustomerPersona:
    """Tests for CustomerPersona model."""

    def test_create_valid_persona(self) -> None:
        """Test creating a valid persona with all required fields."""
        persona = CustomerPersona(
            id="test_persona",
            name="Test Customer",
            backstory="A test customer for unit testing.",
            looking_for="Test property",
            budget_range=(200000, 300000),
            timeline=Timeline.FLEXIBLE,
            difficulty=Difficulty.MEDIUM_REGARD,
            initial_regard=RegardLevel.LOW,
            primary_pbm="value",
            secondary_pbm="location",
            objections=["need to think about it"],
            objection_difficulty=ObjectionDifficulty.FIRM,
            voice_name="leda",
        )
        assert persona.id == "test_persona"
        assert persona.name == "Test Customer"
        assert persona.budget_range == (200000, 300000)
        assert persona.difficulty == Difficulty.MEDIUM_REGARD
        assert persona.voice_name == "leda"
        assert persona.is_evaluation_only is False

    def test_persona_is_frozen(self) -> None:
        """Test that persona is immutable after creation."""
        persona = CustomerPersona(
            id="frozen_test",
            name="Frozen",
            backstory="Test",
            looking_for="House",
            budget_range=(300000, 400000),
            timeline=Timeline.URGENT,
            difficulty=Difficulty.HIGH_REGARD,
            initial_regard=RegardLevel.HIGH,
            primary_pbm="opportunity",
            voice_name="kore",
        )
        with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen
            persona.name = "Changed"  # type: ignore[misc]

    def test_persona_optional_secondary_pbm(self) -> None:
        """Test that secondary_pbm is optional."""
        persona = CustomerPersona(
            id="no_secondary",
            name="Test",
            backstory="Test",
            looking_for="Land",
            budget_range=(100000, 200000),
            timeline=Timeline.BROWSING,
            difficulty=Difficulty.LOW_REGARD,
            initial_regard=RegardLevel.NO,
            primary_pbm="budget",
            secondary_pbm=None,
            voice_name="puck",
        )
        assert persona.secondary_pbm is None

    def test_persona_default_objections(self) -> None:
        """Test that objections default to empty list."""
        persona = CustomerPersona(
            id="no_objections",
            name="Easy Buyer",
            backstory="Very agreeable first-time buyer",
            looking_for="Starter home",
            budget_range=(250000, 350000),
            timeline=Timeline.URGENT,
            difficulty=Difficulty.HIGH_REGARD,
            initial_regard=RegardLevel.HIGH,
            primary_pbm="quality",
            voice_name="charon",
        )
        assert persona.objections == []
        assert persona.objection_difficulty == ObjectionDifficulty.SOFT

    def test_persona_medium_regard_level(self) -> None:
        """Test that MEDIUM regard level is a valid enum value."""
        persona = CustomerPersona(
            id="medium_regard_test",
            name="Test",
            backstory="Test",
            looking_for="Duplex",
            budget_range=(350000, 420000),
            timeline=Timeline.MEDIUM,
            difficulty=Difficulty.MEDIUM_REGARD,
            initial_regard=RegardLevel.MEDIUM,
            primary_pbm="cash flow",
            voice_name="aoede",
        )
        assert persona.initial_regard == RegardLevel.MEDIUM
        assert persona.timeline == Timeline.MEDIUM


# =============================================================================
# CoreStageProgress Tests
# =============================================================================


class TestCoreStageProgress:
    """Tests for CoreStageProgress model."""

    def test_default_stage_is_connect(self) -> None:
        """Test that progress starts at CONNECT stage."""
        progress = CoreStageProgress()
        assert progress.current_stage == SalesStage.CONNECT

    def test_default_checklists_are_false(self) -> None:
        """Test that all checklist items start as False."""
        progress = CoreStageProgress()
        assert all(v is False for v in progress.connect.values())
        assert all(v is False for v in progress.observe.values())
        assert all(v is False for v in progress.recommend.values())
        assert all(v is False for v in progress.execute.values())

    def test_connect_checklist_keys(self) -> None:
        """Test CONNECT stage has correct checklist keys."""
        progress = CoreStageProgress()
        expected_keys = {"warm_greeting", "establish_credibility", "create_comfort"}
        assert set(progress.connect.keys()) == expected_keys

    def test_observe_checklist_keys(self) -> None:
        """Test OBSERVE stage has correct checklist keys."""
        progress = CoreStageProgress()
        expected_keys = {"needs_discovery", "goal_identification", "motivator_mapping"}
        assert set(progress.observe.keys()) == expected_keys

    def test_recommend_checklist_keys(self) -> None:
        """Test RECOMMEND stage has correct checklist keys."""
        progress = CoreStageProgress()
        expected_keys = {"solution_presentation", "value_connection", "risk_mitigation"}
        assert set(progress.recommend.keys()) == expected_keys

    def test_execute_checklist_keys(self) -> None:
        """Test EXECUTE stage has correct checklist keys."""
        progress = CoreStageProgress()
        expected_keys = {"commitment_request", "objection_handling", "finalize_agreement"}
        assert set(progress.execute.keys()) == expected_keys

    def test_motivator_tracking_lists(self) -> None:
        """Test customer motivator tracking starts empty."""
        progress = CoreStageProgress()
        assert progress.pbms_expressed == []
        assert progress.pbms_acknowledged == []

    def test_update_checklist_item(self) -> None:
        """Test updating a checklist item."""
        progress = CoreStageProgress()
        progress.connect["warm_greeting"] = True
        assert progress.connect["warm_greeting"] is True

    def test_add_motivator(self) -> None:
        """Test adding customer motivators to tracking lists."""
        progress = CoreStageProgress()
        progress.pbms_expressed.append("value")
        progress.pbms_acknowledged.append("value")
        assert "value" in progress.pbms_expressed
        assert "value" in progress.pbms_acknowledged


# =============================================================================
# CustomerAgentState Tests
# =============================================================================


class TestCustomerAgentState:
    """Tests for CustomerAgentState TypedDict structure."""

    def test_create_valid_state(self) -> None:
        """Test creating a valid agent state."""
        persona = OPTIMISTIC_RENOVATOR
        progress = CoreStageProgress()

        state: CustomerAgentState = {
            "messages": [HumanMessage(content="Hello!")],
            "turn_count": 1,
            "persona": persona,
            "mood": Mood.INTERESTED,
            "regard_level": RegardLevel.HIGH,
            "objections_available": list(OPTIMISTIC_RENOVATOR.objections),
            "objections_raised": [],
            "objections_resolved": [],
            "stage_progress": progress,
            "session_id": "test-session-123",
            "user_id": "user-456",
        }

        assert len(state["messages"]) == 1
        assert state["turn_count"] == 1
        assert state["persona"].name == "Marcus"
        assert state["mood"] == Mood.INTERESTED

    def test_state_with_multiple_messages(self) -> None:
        """Test state with conversation history."""
        state: CustomerAgentState = {
            "messages": [
                HumanMessage(content="Hi there!"),
                AIMessage(content="Hello! How can I help you today?"),
                HumanMessage(content="I'm looking for a starter home."),
            ],
            "turn_count": 3,
            "persona": ANXIOUS_FIRST_TIMER,
            "mood": Mood.NEUTRAL,
            "regard_level": RegardLevel.LOW,
            "objections_available": ANXIOUS_FIRST_TIMER.objections.copy(),
            "objections_raised": [],
            "objections_resolved": [],
            "stage_progress": CoreStageProgress(),
            "session_id": "session-789",
            "user_id": "user-012",
        }

        assert len(state["messages"]) == 3
        assert state["persona"].difficulty == Difficulty.MEDIUM_REGARD


# =============================================================================
# Persona Registry Tests
# =============================================================================


class TestPersonaRegistry:
    """Tests for persona registry functions."""

    def test_all_personas_registered(self) -> None:
        """Test that all 10 real estate buyer personas are in the registry."""
        assert len(PERSONAS) == 10
        assert "optimistic_renovator" in PERSONAS
        assert "anxious_first_timer" in PERSONAS
        assert "practical_family" in PERSONAS
        assert "urban_minimalist" in PERSONAS
        assert "privacy_remote_worker" in PERSONAS
        assert "scaling_investor" in PERSONAS
        assert "wealthy_skeptic" in PERSONAS
        assert "landlord_investor" in PERSONAS
        assert "school_obsessed_parent" in PERSONAS
        assert "lifestyle_retiree" in PERSONAS

    def test_get_persona_valid_id(self) -> None:
        """Test retrieving a persona by valid ID."""
        persona = get_persona("optimistic_renovator")
        assert persona is not None
        assert persona.name == "Marcus"

    def test_get_persona_invalid_id(self) -> None:
        """Test retrieving a persona by invalid ID returns None."""
        persona = get_persona("nonexistent")
        assert persona is None

    def test_get_personas_by_difficulty_easy(self) -> None:
        """Test getting easy (high regard) difficulty personas."""
        easy_personas = get_personas_by_difficulty(Difficulty.HIGH_REGARD)
        assert len(easy_personas) == 1
        assert easy_personas[0].id == "optimistic_renovator"

    def test_get_personas_by_difficulty_medium(self) -> None:
        """Test getting medium difficulty personas."""
        medium_personas = get_personas_by_difficulty(Difficulty.MEDIUM_REGARD)
        assert len(medium_personas) == 5
        ids = [p.id for p in medium_personas]
        assert "anxious_first_timer" in ids
        assert "practical_family" in ids
        assert "urban_minimalist" in ids
        assert "privacy_remote_worker" in ids
        assert "scaling_investor" in ids

    def test_get_personas_by_difficulty_hard(self) -> None:
        """Test getting hard (low regard) difficulty personas."""
        hard_personas = get_personas_by_difficulty(Difficulty.LOW_REGARD)
        assert len(hard_personas) == 4
        ids = [p.id for p in hard_personas]
        assert "wealthy_skeptic" in ids
        assert "landlord_investor" in ids
        assert "school_obsessed_parent" in ids
        assert "lifestyle_retiree" in ids

    def test_list_all_personas(self) -> None:
        """Test listing all personas."""
        all_personas = list_all_personas()
        assert len(all_personas) == 10

    def test_predefined_persona_values(self) -> None:
        """Test that predefined personas have expected values."""
        assert OPTIMISTIC_RENOVATOR.difficulty == Difficulty.HIGH_REGARD
        assert OPTIMISTIC_RENOVATOR.initial_regard == RegardLevel.HIGH

        assert ANXIOUS_FIRST_TIMER.difficulty == Difficulty.MEDIUM_REGARD
        assert ANXIOUS_FIRST_TIMER.primary_pbm == "confidence"

        assert PRACTICAL_FAMILY.initial_regard == RegardLevel.LOW

        assert WEALTHY_SKEPTIC.difficulty == Difficulty.LOW_REGARD

        assert LANDLORD_INVESTOR.objection_difficulty == ObjectionDifficulty.FIRM


# =============================================================================
# C.O.R.E. System Content Tests
# =============================================================================


class TestCORESystemContent:
    """Tests for C.O.R.E. system content."""

    def test_all_stages_defined(self) -> None:
        """Test that all 4 C.O.R.E. stages are defined."""
        assert len(CORE_STAGES) == 4
        assert "CONNECT" in CORE_STAGES
        assert "OBSERVE" in CORE_STAGES
        assert "RECOMMEND" in CORE_STAGES
        assert "EXECUTE" in CORE_STAGES

    def test_customer_motivators_defined(self) -> None:
        """Test that customer motivators are defined."""
        assert len(CUSTOMER_MOTIVATORS) > 0
        assert "value" in CUSTOMER_MOTIVATORS
        assert "quality" in CUSTOMER_MOTIVATORS
        assert "convenience" in CUSTOMER_MOTIVATORS

    def test_get_stage_content_valid(self) -> None:
        """Test getting stage content by valid name."""
        content = get_stage_content("CONNECT")
        assert content is not None
        assert content["name"] == "CONNECT"
        assert "purpose" in content
        assert "requirements" in content

    def test_get_stage_content_case_insensitive(self) -> None:
        """Test that stage lookup is case insensitive."""
        content = get_stage_content("connect")
        assert content is not None
        assert content["name"] == "CONNECT"

    def test_get_stage_content_invalid(self) -> None:
        """Test getting stage content by invalid name returns None."""
        content = get_stage_content("INVALID")
        assert content is None

    def test_get_stage_requirements(self) -> None:
        """Test getting stage requirements."""
        requirements = get_stage_requirements("OBSERVE")
        assert len(requirements) == 3
        ids = [r["id"] for r in requirements]
        assert "needs_discovery" in ids
        assert "goal_identification" in ids
        assert "motivator_mapping" in ids

    def test_get_stage_requirements_invalid(self) -> None:
        """Test getting requirements for invalid stage returns empty list."""
        requirements = get_stage_requirements("INVALID")
        assert requirements == []

    def test_full_context_not_empty(self) -> None:
        """Test that full context string is populated."""
        assert len(CORE_FULL_CONTEXT) > 1000
        assert "C.O.R.E." in CORE_FULL_CONTEXT
        assert "CONNECT" in CORE_FULL_CONTEXT
        assert "Customer Motivators" in CORE_FULL_CONTEXT


# =============================================================================
# Objections Tests
# =============================================================================


class TestObjections:
    """Tests for objection registry."""

    def test_objections_exist(self) -> None:
        """Test that objections are defined."""
        assert len(ALL_OBJECTIONS) > 0

    def test_all_categories_have_objections(self) -> None:
        """Test that all categories have at least one objection."""
        for category in ObjectionCategory:
            objections = get_objections_by_category(category)
            assert len(objections) > 0, f"No objections for {category}"

    def test_get_objections_by_category(self) -> None:
        """Test filtering objections by category."""
        price_objections = get_objections_by_category(ObjectionCategory.PRICE)
        assert all(obj["category"] == ObjectionCategory.PRICE for obj in price_objections)

    def test_get_objections_by_difficulty(self) -> None:
        """Test filtering objections by difficulty."""
        soft_objections = get_objections_by_difficulty("soft")
        assert all(obj["difficulty"] == "soft" for obj in soft_objections)

        firm_objections = get_objections_by_difficulty("firm")
        assert all(obj["difficulty"] == "firm" for obj in firm_objections)

    def test_get_objection_texts(self) -> None:
        """Test getting just objection text strings."""
        texts = get_objection_texts()
        assert len(texts) == len(ALL_OBJECTIONS)
        assert all(isinstance(t, str) for t in texts)

    def test_objection_entry_structure(self) -> None:
        """Test that objection entries have required fields."""
        for obj in ALL_OBJECTIONS:
            assert "text" in obj
            assert "category" in obj
            assert "difficulty" in obj
            assert "resolution_hint" in obj

    def test_objection_difficulties_valid(self) -> None:
        """Test that all objection difficulties are valid values."""
        valid_difficulties = {"soft", "firm", "immovable"}
        for obj in ALL_OBJECTIONS:
            assert obj["difficulty"] in valid_difficulties


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for enum definitions."""

    def test_sales_stage_values(self) -> None:
        """Test SalesStage enum values."""
        assert SalesStage.CONNECT.value == "CONNECT"
        assert SalesStage.OBSERVE.value == "OBSERVE"
        assert SalesStage.RECOMMEND.value == "RECOMMEND"
        assert SalesStage.EXECUTE.value == "EXECUTE"
        assert SalesStage.COMPLETE.value == "COMPLETE"

    def test_difficulty_values(self) -> None:
        """Test Difficulty enum values."""
        assert Difficulty.HIGH_REGARD.value == "high_regard"
        assert Difficulty.MEDIUM_REGARD.value == "medium_regard"
        assert Difficulty.LOW_REGARD.value == "low_regard"

    def test_regard_level_values(self) -> None:
        """Test RegardLevel enum values."""
        assert RegardLevel.HIGH.value == "high"
        assert RegardLevel.MEDIUM.value == "medium"
        assert RegardLevel.LOW.value == "low"
        assert RegardLevel.NO.value == "no"

    def test_mood_values(self) -> None:
        """Test Mood enum values."""
        assert Mood.INTERESTED.value == "interested"
        assert Mood.NEUTRAL.value == "neutral"
        assert Mood.SKEPTICAL.value == "skeptical"
        assert Mood.FRUSTRATED.value == "frustrated"
        assert Mood.READY_TO_BUY.value == "ready_to_buy"

    def test_timeline_values(self) -> None:
        """Test Timeline enum values."""
        assert Timeline.URGENT.value == "urgent"
        assert Timeline.MEDIUM.value == "medium"
        assert Timeline.FLEXIBLE.value == "flexible"
        assert Timeline.BROWSING.value == "browsing"

    def test_objection_difficulty_values(self) -> None:
        """Test ObjectionDifficulty enum values."""
        assert ObjectionDifficulty.SOFT.value == "soft"
        assert ObjectionDifficulty.FIRM.value == "firm"
        assert ObjectionDifficulty.IMMOVABLE.value == "immovable"
