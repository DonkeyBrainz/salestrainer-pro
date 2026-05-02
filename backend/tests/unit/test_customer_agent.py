"""Unit tests for CustomerAgentGraph and CustomerAgentService."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.customer_agent import CustomerAgentGraph
from app.agents.personas import ANXIOUS_FIRST_TIMER, WEALTHY_SKEPTIC, OPTIMISTIC_RENOVATOR
from app.agents.prompts import (
    build_customer_prompt,
    get_regard_description,
    get_timeline_description,
)
from app.agents.state import (
    DIFFICULTY_CONFIG,
    CoreStageProgress,
    CustomerAgentState,
    Mood,
    RegardLevel,
    Timeline,
)
from app.services.customer_agent_service import CustomerAgentService


@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock settings for testing."""
    settings = MagicMock()
    settings.gemini_model = "gemini-2.0-flash"
    settings.gemini_api_key = "test-key"
    settings.gemini_temperature = 0.7
    settings.gemini_max_tokens = 1024
    return settings


@pytest.fixture
def sample_state() -> CustomerAgentState:
    """Sample customer agent state for testing."""
    return {
        "messages": [],
        "turn_count": 0,
        "persona": OPTIMISTIC_RENOVATOR,
        "mood": Mood.INTERESTED,
        "regard_level": RegardLevel.HIGH,
        "objections_available": ["I can fix all this myself — no problem"],
        "objections_raised": [],
        "objections_resolved": [],
        "stage_progress": CoreStageProgress(),
        "session_id": "test-session",
        "user_id": "test-user",
    }


# =============================================================================
# Prompt Tests
# =============================================================================


class TestPromptHelpers:
    """Tests for prompt helper functions."""

    def test_get_timeline_description_urgent(self) -> None:
        """Should return urgent description."""
        result = get_timeline_description(Timeline.URGENT)
        assert "soon" in result.lower() or "time-sensitive" in result.lower()

    def test_get_timeline_description_flexible(self) -> None:
        """Should return flexible description."""
        result = get_timeline_description(Timeline.FLEXIBLE)
        assert "rush" in result.lower() or "weeks" in result.lower()

    def test_get_timeline_description_browsing(self) -> None:
        """Should return browsing description."""
        result = get_timeline_description(Timeline.BROWSING)
        assert "looking" in result.lower() or "no pressure" in result.lower()

    def test_get_regard_description_high(self) -> None:
        """Should return high regard description."""
        result = get_regard_description(RegardLevel.HIGH)
        assert "open" in result.lower() or "friendly" in result.lower()

    def test_get_regard_description_low(self) -> None:
        """Should return low regard description."""
        result = get_regard_description(RegardLevel.LOW)
        assert "guarded" in result.lower()

    def test_get_regard_description_no(self) -> None:
        """Should return no regard description."""
        result = get_regard_description(RegardLevel.NO)
        assert "resistant" in result.lower() or "skeptical" in result.lower()


class TestBuildCustomerPrompt:
    """Tests for build_customer_prompt function."""

    def test_includes_persona_name(self, sample_state: CustomerAgentState) -> None:
        """Should include persona name in prompt."""
        result = build_customer_prompt(sample_state["persona"], sample_state)
        assert sample_state["persona"].name in result

    def test_includes_budget_range(self, sample_state: CustomerAgentState) -> None:
        """Should include budget range in prompt."""
        result = build_customer_prompt(sample_state["persona"], sample_state)
        budget_min, budget_max = sample_state["persona"].budget_range
        assert str(budget_min) in result.replace(",", "")
        assert str(budget_max) in result.replace(",", "")

    def test_includes_primary_pbm(self, sample_state: CustomerAgentState) -> None:
        """Should include primary PBM in prompt."""
        result = build_customer_prompt(sample_state["persona"], sample_state)
        assert sample_state["persona"].primary_pbm in result

    def test_includes_pending_objections(self, sample_state: CustomerAgentState) -> None:
        """Should include pending objections in prompt."""
        result = build_customer_prompt(sample_state["persona"], sample_state)
        assert sample_state["objections_available"][0] in result


# =============================================================================
# CustomerAgentGraph Node Tests
# =============================================================================


class TestAnalyzeInput:
    """Tests for _analyze_input node."""

    def test_detects_greeting(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should detect greeting in message."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["messages"] = [HumanMessage(content="Hi there, how are you today?")]

        result = agent._analyze_input(sample_state)

        assert result.get("_analysis", {}).get("has_greeting") is True

    def test_detects_pushy_language(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should detect pushy sales language."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["messages"] = [HumanMessage(content="Buy now while the deal lasts!")]

        result = agent._analyze_input(sample_state)

        assert result.get("_analysis", {}).get("is_pushy") is True

    def test_detects_acknowledgment(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should detect acknowledgment of concerns."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["messages"] = [HumanMessage(content="I understand your concerns about that.")]

        result = agent._analyze_input(sample_state)

        assert result.get("_analysis", {}).get("acknowledges_concern") is True

    def test_detects_question(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should detect questions."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["messages"] = [HumanMessage(content="What are you looking for today?")]

        result = agent._analyze_input(sample_state)

        assert result.get("_analysis", {}).get("has_question") is True

    def test_empty_messages_returns_empty(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should return empty dict for no messages."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["messages"] = []

        result = agent._analyze_input(sample_state)

        assert result == {}

    def test_ai_message_returns_empty(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should return empty for AI messages (not human)."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["messages"] = [AIMessage(content="Hello!")]

        result = agent._analyze_input(sample_state)

        assert result == {}


class TestUpdateMood:
    """Tests for _update_mood node."""

    def test_improves_mood_on_acknowledgment(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should improve mood when salesperson acknowledges concern."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["mood"] = Mood.NEUTRAL
        sample_state["_analysis"] = {"acknowledges_concern": True}

        result = agent._update_mood(sample_state)

        assert result["mood"] == Mood.INTERESTED

    def test_improves_regard_on_acknowledgment(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should improve regard when salesperson acknowledges concern."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["regard_level"] = RegardLevel.LOW
        sample_state["_analysis"] = {"acknowledges_concern": True}

        result = agent._update_mood(sample_state)

        assert result["regard_level"] == RegardLevel.HIGH

    def test_worsens_mood_on_pushy(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should worsen mood on pushy behavior."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["mood"] = Mood.INTERESTED
        sample_state["_analysis"] = {"is_pushy": True}

        result = agent._update_mood(sample_state)

        assert result["mood"] == Mood.NEUTRAL

    def test_improves_regard_on_early_greeting(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should improve regard on greeting in early turns."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["turn_count"] = 1
        sample_state["regard_level"] = RegardLevel.LOW
        sample_state["_analysis"] = {"has_greeting": True}

        result = agent._update_mood(sample_state)

        assert result["regard_level"] == RegardLevel.HIGH


class TestObjectionRouting:
    """Tests for objection routing logic."""

    def test_routes_to_inject_early_turn_medium_difficulty(self, mock_settings: MagicMock) -> None:
        """Should inject objection on turns 2-4 for medium difficulty."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        state: CustomerAgentState = {
            "messages": [],
            "turn_count": 3,
            "persona": ANXIOUS_FIRST_TIMER,  # Medium difficulty
            "mood": Mood.NEUTRAL,
            "regard_level": RegardLevel.LOW,
            "objections_available": ["need to talk to my husband"],
            "objections_raised": [],
            "objections_resolved": [],
            "stage_progress": CoreStageProgress(),
            "session_id": "test",
            "user_id": "test",
        }

        result = agent._route_objection(state)

        assert result == "inject"

    def test_routes_to_respond_when_no_objections(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should route to respond when no objections available."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["objections_available"] = []

        result = agent._route_objection(sample_state)

        assert result == "respond"

    def test_routes_to_respond_when_all_raised(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should route to respond when all objections already raised."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["objections_raised"] = list(sample_state["objections_available"])

        result = agent._route_objection(sample_state)

        assert result == "respond"

    def test_routes_to_respond_easy_persona_early_turn(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should not auto-inject for easy personas even in early turns."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # OPTIMISTIC_RENOVATOR is easy difficulty
        sample_state["turn_count"] = 3
        sample_state["mood"] = Mood.INTERESTED  # Good mood, no behavior-responsive trigger

        result = agent._route_objection(sample_state)

        assert result == "respond"


class TestInjectObjection:
    """Tests for _inject_objection node."""

    def test_selects_first_pending_objection(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should select first unraised objection."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["objections_available"] = ["objection1", "objection2"]
        sample_state["objections_raised"] = []

        result = agent._inject_objection(sample_state)

        assert result["objections_raised"] == ["objection1"]
        assert result["_injected_objection"] == "objection1"

    def test_skips_already_raised(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should skip objections already raised."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["objections_available"] = ["objection1", "objection2"]
        sample_state["objections_raised"] = ["objection1"]

        result = agent._inject_objection(sample_state)

        assert "objection2" in result["objections_raised"]
        assert result["_injected_objection"] == "objection2"

    def test_returns_empty_when_all_raised(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should return empty when all objections already raised."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        sample_state["objections_available"] = ["objection1"]
        sample_state["objections_raised"] = ["objection1"]

        result = agent._inject_objection(sample_state)

        assert result == {}


class TestMoodHelpers:
    """Tests for mood/regard helper methods."""

    def test_improve_mood_progression(self, mock_settings: MagicMock) -> None:
        """Should progress mood positively (using easy difficulty for 100% chance)."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # Use "high_regard" difficulty (100% improve chance) to test progression
        assert agent._improve_mood(Mood.FRUSTRATED, "high_regard") == Mood.SKEPTICAL
        assert agent._improve_mood(Mood.SKEPTICAL, "high_regard") == Mood.NEUTRAL
        assert agent._improve_mood(Mood.NEUTRAL, "high_regard") == Mood.INTERESTED
        assert agent._improve_mood(Mood.INTERESTED, "high_regard") == Mood.READY_TO_BUY
        assert agent._improve_mood(Mood.READY_TO_BUY, "high_regard") == Mood.READY_TO_BUY  # Max

    def test_worsen_mood_progression(self, mock_settings: MagicMock) -> None:
        """Should progress mood negatively (using easy difficulty for 1-step)."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # Use "high_regard" difficulty (1 step worsen) to test single-step progression
        assert agent._worsen_mood(Mood.READY_TO_BUY, "high_regard") == Mood.INTERESTED
        assert agent._worsen_mood(Mood.INTERESTED, "high_regard") == Mood.NEUTRAL
        assert agent._worsen_mood(Mood.NEUTRAL, "high_regard") == Mood.SKEPTICAL
        assert agent._worsen_mood(Mood.SKEPTICAL, "high_regard") == Mood.FRUSTRATED
        assert agent._worsen_mood(Mood.FRUSTRATED, "high_regard") == Mood.FRUSTRATED  # Min

    def test_improve_regard_progression(self, mock_settings: MagicMock) -> None:
        """Should progress regard positively."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        assert agent._improve_regard(RegardLevel.NO) == RegardLevel.LOW
        assert agent._improve_regard(RegardLevel.LOW) == RegardLevel.HIGH
        assert agent._improve_regard(RegardLevel.HIGH) == RegardLevel.HIGH  # Max


class TestGenerateResponse:
    """Tests for _generate_response node."""

    async def test_generates_response_with_llm(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should call LLM and return response."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI") as MockLLM:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke.return_value = MagicMock(
                content="Hello! I'm looking for a sofa."
            )
            MockLLM.return_value = mock_llm_instance

            agent = CustomerAgentGraph(mock_settings)

        sample_state["messages"] = [HumanMessage(content="Hi there!")]

        result = await agent._generate_response(sample_state)

        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert result["turn_count"] == 1

    async def test_includes_injected_objection(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should include objection instruction when injected."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI") as MockLLM:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke.return_value = MagicMock(content="I need to measure first.")
            MockLLM.return_value = mock_llm_instance

            agent = CustomerAgentGraph(mock_settings)

        sample_state["messages"] = [HumanMessage(content="Hi there!")]
        sample_state["_injected_objection"] = "need to measure"

        await agent._generate_response(sample_state)

        # Check that LLM was called with extra instruction
        call_args = mock_llm_instance.ainvoke.call_args
        messages = call_args[0][0]
        # Should have system prompt + user message + objection instruction
        assert len(messages) >= 3


# =============================================================================
# CustomerAgentService Tests
# =============================================================================


class TestStartSession:
    """Tests for start_session method."""

    async def test_creates_initial_state_from_persona(self, mock_settings: MagicMock) -> None:
        """Should create state with persona defaults."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

            state = await service.start_session(
                session_id="test-session",
                user_id="test-user",
                persona_id="optimistic_renovator",
            )

        assert state["session_id"] == "test-session"
        assert state["user_id"] == "test-user"
        assert state["persona"].id == "optimistic_renovator"
        assert state["turn_count"] == 0
        assert state["messages"] == []

    async def test_raises_error_for_invalid_persona(self, mock_settings: MagicMock) -> None:
        """Should raise ValueError for unknown persona."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

            with pytest.raises(ValueError, match="Persona 'nonexistent' not found"):
                await service.start_session("s", "u", "nonexistent")

    async def test_sets_initial_mood_high_regard(self, mock_settings: MagicMock) -> None:
        """Should set interested mood for high regard personas."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

            # OPTIMISTIC_RENOVATOR has high regard
            state = await service.start_session("s", "u", "optimistic_renovator")

        assert state["mood"] == Mood.INTERESTED

    async def test_sets_initial_mood_low_regard(self, mock_settings: MagicMock) -> None:
        """Should set neutral mood for low regard personas."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

            # ANXIOUS_FIRST_TIMER has low regard
            state = await service.start_session("s", "u", "anxious_first_timer")

        assert state["mood"] == Mood.NEUTRAL

    async def test_sets_initial_mood_medium_regard(self, mock_settings: MagicMock) -> None:
        """Should set neutral mood for medium regard personas."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

            # PRIVACY_SEEKING_REMOTE_WORKER has medium regard
            state = await service.start_session("s", "u", "privacy_remote_worker")

        assert state["mood"] == Mood.NEUTRAL

    async def test_copies_persona_objections(self, mock_settings: MagicMock) -> None:
        """Should copy persona objections to available list."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

            state = await service.start_session("s", "u", "anxious_first_timer")

        assert len(state["objections_available"]) == len(ANXIOUS_FIRST_TIMER.objections)
        assert state["objections_raised"] == []


class TestProcessMessage:
    """Tests for process_message method."""

    async def test_adds_user_message_to_state(self, mock_settings: MagicMock) -> None:
        """Should add user message before invoking graph."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph") as MockGraph:
            mock_agent = MagicMock()
            mock_agent.invoke = AsyncMock(
                return_value={
                    "messages": [
                        HumanMessage(content="Hello!"),
                        AIMessage(content="Hi there!"),
                    ],
                    "turn_count": 1,
                    "persona": OPTIMISTIC_RENOVATOR,
                    "mood": Mood.INTERESTED,
                    "regard_level": RegardLevel.HIGH,
                    "objections_available": [],
                    "objections_raised": [],
                    "objections_resolved": [],
                    "stage_progress": CoreStageProgress(),
                    "session_id": "s",
                    "user_id": "u",
                }
            )
            MockGraph.return_value = mock_agent

            service = CustomerAgentService(mock_settings)
            initial_state = await service.start_session("s", "u", "optimistic_renovator")

            response, new_state = await service.process_message("s", "Hello!", initial_state)

        # Verify invoke was called with message added
        call_args = mock_agent.invoke.call_args
        passed_state = call_args[0][0]
        assert len(passed_state["messages"]) == 1
        assert isinstance(passed_state["messages"][0], HumanMessage)

    async def test_returns_response_text(self, mock_settings: MagicMock) -> None:
        """Should extract response text from AI message."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph") as MockGraph:
            mock_agent = MagicMock()
            mock_agent.invoke = AsyncMock(
                return_value={
                    "messages": [AIMessage(content="I'm looking for a sofa.")],
                    "turn_count": 1,
                    "persona": OPTIMISTIC_RENOVATOR,
                    "mood": Mood.INTERESTED,
                    "regard_level": RegardLevel.HIGH,
                    "objections_available": [],
                    "objections_raised": [],
                    "objections_resolved": [],
                    "stage_progress": CoreStageProgress(),
                    "session_id": "s",
                    "user_id": "u",
                }
            )
            MockGraph.return_value = mock_agent

            service = CustomerAgentService(mock_settings)
            initial_state = await service.start_session("s", "u", "optimistic_renovator")

            response, new_state = await service.process_message("s", "Hello!", initial_state)

        assert response == "I'm looking for a sofa."


class TestGetSessionState:
    """Tests for get_session_state method."""

    async def test_delegates_to_agent(self, mock_settings: MagicMock) -> None:
        """Should call agent's get_state method."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph") as MockGraph:
            mock_agent = MagicMock()
            mock_agent.get_state.return_value = None
            MockGraph.return_value = mock_agent

            service = CustomerAgentService(mock_settings)
            result = await service.get_session_state("test-session")

        mock_agent.get_state.assert_called_once_with("test-session")
        assert result is None


# =============================================================================
# State Serialization Tests
# =============================================================================


class TestSerializeDeserializeState:
    """Tests for state serialization and deserialization."""

    def test_serialize_state_includes_all_fields(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should serialize all relevant fields to JSON."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

        result = service.serialize_state(sample_state)
        data = json.loads(result)

        assert data["turn_count"] == sample_state["turn_count"]
        assert data["mood"] == sample_state["mood"].value
        assert data["regard_level"] == sample_state["regard_level"].value
        assert data["session_id"] == sample_state["session_id"]
        assert data["user_id"] == sample_state["user_id"]
        assert "objections_available" in data
        assert "objections_raised" in data
        assert "stage_progress" in data

    def test_deserialize_state_restores_all_fields(self, mock_settings: MagicMock) -> None:
        """Should deserialize JSON back to CustomerAgentState."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

        snapshot = json.dumps(
            {
                "turn_count": 5,
                "mood": "skeptical",
                "regard_level": "low",
                "objections_available": ["too expensive", "need to measure"],
                "objections_raised": ["too expensive"],
                "objections_resolved": [],
                "session_id": "test-session",
                "user_id": "test-user",
                "stage_progress": {
                    "current_stage": "OBSERVE",
                    "connect": {
                        "warm_greeting": True,
                        "establish_credibility": False,
                        "create_comfort": False,
                    },
                    "observe": {
                        "needs_discovery": False,
                        "goal_identification": False,
                        "motivator_mapping": False,
                    },
                    "recommend": {
                        "solution_presentation": False,
                        "value_connection": False,
                        "risk_mitigation": False,
                    },
                    "execute": {
                        "commitment_request": False,
                        "objection_handling": False,
                        "finalize_agreement": False,
                    },
                    "pbms_expressed": ["durability"],
                    "pbms_acknowledged": [],
                },
            }
        )

        messages = [HumanMessage(content="Hello"), AIMessage(content="Hi there")]

        result = service.deserialize_state(snapshot, OPTIMISTIC_RENOVATOR, messages)

        assert result["turn_count"] == 5
        assert result["mood"] == Mood.SKEPTICAL
        assert result["regard_level"] == RegardLevel.LOW
        assert result["objections_available"] == ["too expensive", "need to measure"]
        assert result["objections_raised"] == ["too expensive"]
        assert result["session_id"] == "test-session"
        assert result["persona"] == OPTIMISTIC_RENOVATOR
        assert len(result["messages"]) == 2
        assert result["stage_progress"].current_stage.value == "OBSERVE"
        assert result["stage_progress"].pbms_expressed == ["durability"]

    def test_serialize_deserialize_roundtrip(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Should be able to serialize and deserialize back to equivalent state."""
        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

        # Add some messages
        sample_state["messages"] = [
            HumanMessage(content="Hi"),
            AIMessage(content="Hello!"),
        ]
        sample_state["turn_count"] = 1
        sample_state["objections_raised"] = ["I can fix all this myself — no problem"]

        # Serialize
        serialized = service.serialize_state(sample_state)

        # Deserialize
        restored = service.deserialize_state(
            serialized,
            sample_state["persona"],
            sample_state["messages"],
        )

        # Verify key fields match
        assert restored["turn_count"] == sample_state["turn_count"]
        assert restored["mood"] == sample_state["mood"]
        assert restored["regard_level"] == sample_state["regard_level"]
        assert restored["objections_raised"] == sample_state["objections_raised"]
        assert restored["persona"] == sample_state["persona"]
        assert len(restored["messages"]) == len(sample_state["messages"])


class TestResumeSession:
    """Tests for resume_session method."""

    def test_resume_session_with_snapshot_and_transcript(self, mock_settings: MagicMock) -> None:
        """Should restore full state from session and transcript."""
        from datetime import UTC, datetime

        from app.models.session import Difficulty as SessionDifficulty
        from app.models.session import Session, SessionStatus, SessionType
        from app.models.transcript import MessageRole, Transcript, TranscriptMessage

        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

        now = datetime.now(UTC)

        # Create mock session with snapshot
        session = Session(
            session_id="test-session",
            user_id="test-user",
            session_type=SessionType.TRAINING,
            status=SessionStatus.COMPLETED,
            selected_persona="optimistic_renovator",
            difficulty=SessionDifficulty.HIGH_REGARD,
            agent_state_snapshot=json.dumps(
                {
                    "turn_count": 2,
                    "mood": "interested",
                    "regard_level": "high",
                    "objections_available": ["I can fix all this myself — no problem"],
                    "objections_raised": [],
                    "objections_resolved": [],
                    "session_id": "test-session",
                    "user_id": "test-user",
                    "stage_progress": {},
                }
            ),
            started_at=now,
            created_at=now,
            updated_at=now,
        )

        # Create mock transcript
        transcript = Transcript(
            transcript_id="transcript-1",
            session_id="test-session",
            user_id="test-user",
            messages=[
                TranscriptMessage(
                    message_id="msg-1",
                    role=MessageRole.USER,
                    text="Hi there!",
                    timestamp=now,
                ),
                TranscriptMessage(
                    message_id="msg-2",
                    role=MessageRole.ASSISTANT,
                    text="Hello! Looking for furniture?",
                    timestamp=now,
                ),
            ],
            total_messages=2,
            total_words=6,
            started_at=now,
            created_at=now,
            updated_at=now,
        )

        result = service.resume_session(session, transcript)

        assert result["session_id"] == "test-session"
        assert result["turn_count"] == 2
        assert result["mood"] == Mood.INTERESTED
        assert result["persona"].id == "optimistic_renovator"
        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][0], HumanMessage)
        assert isinstance(result["messages"][1], AIMessage)

    def test_resume_session_without_snapshot(self, mock_settings: MagicMock) -> None:
        """Should create fresh state when no snapshot exists."""
        from datetime import UTC, datetime

        from app.models.session import Difficulty as SessionDifficulty
        from app.models.session import Session, SessionStatus, SessionType

        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

        now = datetime.now(UTC)

        session = Session(
            session_id="test-session",
            user_id="test-user",
            session_type=SessionType.TRAINING,
            status=SessionStatus.ACTIVE,
            selected_persona="anxious_first_timer",
            difficulty=SessionDifficulty.MEDIUM_REGARD,
            agent_state_snapshot=None,  # No snapshot
            started_at=now,
            created_at=now,
            updated_at=now,
        )

        result = service.resume_session(session, None)

        assert result["session_id"] == "test-session"
        assert result["persona"].id == "anxious_first_timer"
        assert result["mood"] == Mood.NEUTRAL  # Low regard -> neutral
        assert result["turn_count"] == 0
        assert result["messages"] == []

    def test_resume_session_raises_for_missing_persona(self, mock_settings: MagicMock) -> None:
        """Should raise ValueError when selected_persona is missing."""
        from datetime import UTC, datetime

        from app.models.session import Difficulty as SessionDifficulty
        from app.models.session import Session, SessionStatus, SessionType

        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

        now = datetime.now(UTC)

        session = Session(
            session_id="test-session",
            user_id="test-user",
            session_type=SessionType.TRAINING,
            status=SessionStatus.ACTIVE,
            selected_persona=None,  # Missing persona
            difficulty=SessionDifficulty.MEDIUM_REGARD,
            started_at=now,
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError, match="Session has no selected_persona"):
            service.resume_session(session, None)

    def test_resume_session_raises_for_invalid_persona(self, mock_settings: MagicMock) -> None:
        """Should raise ValueError when persona ID is invalid."""
        from datetime import UTC, datetime

        from app.models.session import Difficulty as SessionDifficulty
        from app.models.session import Session, SessionStatus, SessionType

        with patch("app.services.customer_agent_service.CustomerAgentGraph"):
            service = CustomerAgentService(mock_settings)

        now = datetime.now(UTC)

        session = Session(
            session_id="test-session",
            user_id="test-user",
            session_type=SessionType.TRAINING,
            status=SessionStatus.ACTIVE,
            selected_persona="nonexistent_persona",
            difficulty=SessionDifficulty.MEDIUM_REGARD,
            started_at=now,
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError, match="Persona 'nonexistent_persona' not found"):
            service.resume_session(session, None)


# =============================================================================
# Difficulty Tuning Tests
# =============================================================================


class TestDifficultyTuning:
    """Tests for difficulty-based behavior tuning."""

    def test_hard_persona_resists_mood_improvement(self, mock_settings: MagicMock) -> None:
        """Hard persona should resist mood improvement when random > 0.5."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # Mock random to return 0.6 (above hard persona's 0.5 threshold)
        with patch("app.agents.customer_agent.random.random", return_value=0.6):
            result = agent._improve_mood(Mood.NEUTRAL, "low_regard")

        # Should remain neutral (resisted improvement)
        assert result == Mood.NEUTRAL

    def test_hard_persona_improves_mood_when_random_low(self, mock_settings: MagicMock) -> None:
        """Hard persona should improve mood when random <= 0.5."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # Mock random to return 0.3 (below hard persona's 0.5 threshold)
        with patch("app.agents.customer_agent.random.random", return_value=0.3):
            result = agent._improve_mood(Mood.NEUTRAL, "low_regard")

        # Should improve to interested
        assert result == Mood.INTERESTED

    def test_easy_persona_always_improves_mood(self, mock_settings: MagicMock) -> None:
        """Easy persona should always improve mood (1.0 chance)."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # Even with high random value, should still improve
        with patch("app.agents.customer_agent.random.random", return_value=0.99):
            result = agent._improve_mood(Mood.NEUTRAL, "high_regard")

        # Should improve to interested
        assert result == Mood.INTERESTED

    def test_medium_persona_mood_improvement(self, mock_settings: MagicMock) -> None:
        """Medium persona should improve 70% of the time."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # Random = 0.6 < 0.7 threshold -> should improve
        with patch("app.agents.customer_agent.random.random", return_value=0.6):
            result = agent._improve_mood(Mood.NEUTRAL, "medium_regard")
        assert result == Mood.INTERESTED

        # Random = 0.8 > 0.7 threshold -> should resist
        with patch("app.agents.customer_agent.random.random", return_value=0.8):
            result = agent._improve_mood(Mood.NEUTRAL, "medium_regard")
        assert result == Mood.NEUTRAL

    def test_hard_persona_worsens_mood_two_steps(self, mock_settings: MagicMock) -> None:
        """Hard persona should worsen mood by 2 steps."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # INTERESTED -> SKEPTICAL (2 steps down)
        result = agent._worsen_mood(Mood.INTERESTED, "low_regard")
        assert result == Mood.SKEPTICAL

        # READY_TO_BUY -> NEUTRAL (2 steps down)
        result = agent._worsen_mood(Mood.READY_TO_BUY, "low_regard")
        assert result == Mood.NEUTRAL

    def test_easy_persona_worsens_mood_one_step(self, mock_settings: MagicMock) -> None:
        """Easy persona should worsen mood by only 1 step."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # INTERESTED -> NEUTRAL (1 step down)
        result = agent._worsen_mood(Mood.INTERESTED, "high_regard")
        assert result == Mood.NEUTRAL

        # READY_TO_BUY -> INTERESTED (1 step down)
        result = agent._worsen_mood(Mood.READY_TO_BUY, "high_regard")
        assert result == Mood.INTERESTED

    def test_hard_persona_mood_decays(self, mock_settings: MagicMock) -> None:
        """Hard persona should decay mood when random < 0.2."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # Mock random to return 0.1 (below hard persona's 0.2 decay threshold)
        with patch("app.agents.customer_agent.random.random", return_value=0.1):
            result = agent._apply_mood_decay(Mood.INTERESTED, "low_regard")

        # Should decay to neutral
        assert result == Mood.NEUTRAL

    def test_hard_persona_no_decay_when_random_high(self, mock_settings: MagicMock) -> None:
        """Hard persona should not decay when random >= 0.2."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # Mock random to return 0.5 (above hard persona's 0.2 decay threshold)
        with patch("app.agents.customer_agent.random.random", return_value=0.5):
            result = agent._apply_mood_decay(Mood.INTERESTED, "low_regard")

        # Should remain interested
        assert result == Mood.INTERESTED

    def test_easy_persona_no_mood_decay(self, mock_settings: MagicMock) -> None:
        """Easy persona should never have mood decay (0.0 chance)."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # Even with very low random value, should not decay
        with patch("app.agents.customer_agent.random.random", return_value=0.0):
            # Note: 0.0 >= 0.0 is True, so no decay (>=, not >)
            result = agent._apply_mood_decay(Mood.INTERESTED, "high_regard")

        # Should remain interested
        assert result == Mood.INTERESTED

    def test_hard_persona_higher_objection_chance(self, mock_settings: MagicMock) -> None:
        """Hard persona should inject objections at 60% rate."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        state: CustomerAgentState = {
            "messages": [],
            "turn_count": 5,  # Past automatic window
            "persona": WEALTHY_SKEPTIC,  # Hard difficulty
            "mood": Mood.SKEPTICAL,
            "regard_level": RegardLevel.NO,
            "objections_available": ["too expensive"],
            "objections_raised": [],
            "objections_resolved": [],
            "stage_progress": CoreStageProgress(),
            "session_id": "test",
            "user_id": "test",
        }

        # Random = 0.5 < 0.6 (hard threshold) -> should inject
        with patch("app.agents.customer_agent.random.random", return_value=0.5):
            result = agent._route_objection(state)
        assert result == "inject"

        # Random = 0.65 > 0.6 -> should respond
        with patch("app.agents.customer_agent.random.random", return_value=0.65):
            result = agent._route_objection(state)
        assert result == "respond"

    def test_easy_persona_lower_objection_chance(
        self, mock_settings: MagicMock, sample_state: CustomerAgentState
    ) -> None:
        """Easy persona should inject objections at only 20% rate."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        # OPTIMISTIC_RENOVATOR is easy difficulty
        sample_state["turn_count"] = 5  # Past automatic window
        sample_state["mood"] = Mood.SKEPTICAL  # Need negative mood for behavior-responsive

        # Random = 0.15 < 0.2 (easy threshold) -> should inject
        with patch("app.agents.customer_agent.random.random", return_value=0.15):
            result = agent._route_objection(sample_state)
        assert result == "inject"

        # Random = 0.25 > 0.2 -> should respond
        with patch("app.agents.customer_agent.random.random", return_value=0.25):
            result = agent._route_objection(sample_state)
        assert result == "respond"

    def test_hard_persona_selects_hardest_objection(self, mock_settings: MagicMock) -> None:
        """Hard persona should select last (hardest) objection."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        pending = ["easy objection", "medium objection", "hard objection"]
        result = agent._select_objection(pending, "low_regard")

        # Should select last (hardest)
        assert result == "hard objection"

    def test_easy_persona_selects_first_objection(self, mock_settings: MagicMock) -> None:
        """Easy persona should select first objection."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        pending = ["easy objection", "medium objection", "hard objection"]
        result = agent._select_objection(pending, "high_regard")

        # Should select first
        assert result == "easy objection"

    def test_medium_persona_selects_first_objection(self, mock_settings: MagicMock) -> None:
        """Medium persona should also select first objection."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        pending = ["easy objection", "medium objection", "hard objection"]
        result = agent._select_objection(pending, "medium_regard")

        # Should select first
        assert result == "easy objection"

    def test_difficulty_config_values(self) -> None:
        """Verify DIFFICULTY_CONFIG has expected values."""
        # Easy config
        assert DIFFICULTY_CONFIG["high_regard"]["mood_improve_chance"] == 1.0
        assert DIFFICULTY_CONFIG["high_regard"]["mood_worsen_steps"] == 1
        assert DIFFICULTY_CONFIG["high_regard"]["mood_decay_chance"] == 0.0
        assert DIFFICULTY_CONFIG["high_regard"]["objection_inject_chance"] == 0.2
        assert DIFFICULTY_CONFIG["high_regard"]["objection_priority"] == "first"

        # Medium config
        assert DIFFICULTY_CONFIG["medium_regard"]["mood_improve_chance"] == 0.7
        assert DIFFICULTY_CONFIG["medium_regard"]["mood_worsen_steps"] == 1
        assert DIFFICULTY_CONFIG["medium_regard"]["mood_decay_chance"] == 0.1
        assert DIFFICULTY_CONFIG["medium_regard"]["objection_inject_chance"] == 0.4
        assert DIFFICULTY_CONFIG["medium_regard"]["objection_priority"] == "first"

        # Hard config
        assert DIFFICULTY_CONFIG["low_regard"]["mood_improve_chance"] == 0.5
        assert DIFFICULTY_CONFIG["low_regard"]["mood_worsen_steps"] == 2
        assert DIFFICULTY_CONFIG["low_regard"]["mood_decay_chance"] == 0.2
        assert DIFFICULTY_CONFIG["low_regard"]["objection_inject_chance"] == 0.6
        assert DIFFICULTY_CONFIG["low_regard"]["objection_priority"] == "hardest"

    def test_update_mood_applies_decay_when_no_action(self, mock_settings: MagicMock) -> None:
        """Should apply mood decay when no positive/negative action detected."""
        with patch("app.agents.customer_agent.ChatGoogleGenerativeAI"):
            agent = CustomerAgentGraph(mock_settings)

        state: CustomerAgentState = {
            "messages": [],
            "turn_count": 5,
            "persona": WEALTHY_SKEPTIC,  # Hard difficulty
            "mood": Mood.INTERESTED,
            "regard_level": RegardLevel.NO,
            "objections_available": [],
            "objections_raised": [],
            "objections_resolved": [],
            "stage_progress": CoreStageProgress(),
            "session_id": "test",
            "user_id": "test",
            "_analysis": {},  # No actions detected
        }

        # Mock random to trigger decay
        with patch("app.agents.customer_agent.random.random", return_value=0.1):
            result = agent._update_mood(state)

        # Mood should have decayed
        assert result["mood"] == Mood.NEUTRAL
