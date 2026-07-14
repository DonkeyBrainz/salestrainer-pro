"""Unit tests for GeminiWebSocketRelay agent processing.

Covers the hardening fixes from AGENTIC_ENGINEERING.md §9:
- Independent exception scopes for customer agent vs coach (fix 1)
- Voice mode skips graph response generation (fix 2, call-site)
- Stage-scoped analysis cache key (fix 3)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.personas import OPTIMISTIC_RENOVATOR
from app.agents.state import (
    CoreStageProgress,
    CustomerAgentState,
    Mood,
    RegardLevel,
    SalesStage,
)
from app.api.ws.gemini_relay import GeminiWebSocketRelay
from app.models.coach import CoachAnalysis, InterventionLevel


@pytest.fixture
def agent_state() -> CustomerAgentState:
    """Sample agent state for relay tests."""
    return {
        "messages": [],
        "turn_count": 1,
        "persona": OPTIMISTIC_RENOVATOR,
        "mood": Mood.INTERESTED,
        "regard_level": RegardLevel.HIGH,
        "objections_available": [],
        "objections_raised": [],
        "objections_resolved": [],
        "stage_progress": CoreStageProgress(),
        "session_id": "test-session",
        "user_id": "test-user",
    }


@pytest.fixture
def relay(agent_state: CustomerAgentState) -> GeminiWebSocketRelay:
    """Relay with mocked services and an active agent state."""
    live_provider = MagicMock()
    live_provider.name = "gemini"
    relay = GeminiWebSocketRelay(
        live_provider=live_provider,
        auth_service=MagicMock(),
        session_service=MagicMock(),
        customer_agent_service=MagicMock(),
        coach_agent_service=MagicMock(),
    )
    relay._session_id = "test-session"
    relay._agent_state = agent_state
    return relay


@pytest.fixture
def websocket() -> AsyncMock:
    """Mock WebSocket connection."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


def make_analysis() -> CoachAnalysis:
    """Minimal coach analysis result."""
    return CoachAnalysis(
        techniques_detected=[],
        stage_items_completed=[],
        pbms_acknowledged=[],
        deviations=[],
        intervention_level=InterventionLevel.NONE,
        hint=None,
        suggested_stage=None,
        confidence=1.0,
    )


class TestProcessAgents:
    """Tests for _process_agents exception decoupling (fix 1)."""

    async def test_coach_runs_when_customer_agent_fails(
        self, relay: GeminiWebSocketRelay, websocket: AsyncMock
    ) -> None:
        """A customer-agent exception must not prevent coach analysis."""
        relay.customer_agent_service.process_message = AsyncMock(
            side_effect=RuntimeError("mood update exploded")
        )
        relay._analyze_and_send_hint = AsyncMock()  # type: ignore[method-assign]

        await relay._process_agents(salesperson_message="Hello!", websocket=websocket)

        relay._analyze_and_send_hint.assert_awaited_once()

    async def test_coach_failure_does_not_propagate(
        self,
        relay: GeminiWebSocketRelay,
        agent_state: CustomerAgentState,
        websocket: AsyncMock,
    ) -> None:
        """A coach exception is swallowed; the session continues."""
        relay.customer_agent_service.process_message = AsyncMock(return_value=("", agent_state))
        relay._analyze_and_send_hint = AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("coach exploded")
        )

        await relay._process_agents(salesperson_message="Hello!", websocket=websocket)

    async def test_skips_response_generation_in_voice_mode(
        self,
        relay: GeminiWebSocketRelay,
        agent_state: CustomerAgentState,
        websocket: AsyncMock,
    ) -> None:
        """The relay discards the graph's text, so it must not be generated (fix 2)."""
        relay.customer_agent_service.process_message = AsyncMock(return_value=("", agent_state))
        relay._analyze_and_send_hint = AsyncMock()  # type: ignore[method-assign]

        await relay._process_agents(salesperson_message="Hello!", websocket=websocket)

        call_kwargs = relay.customer_agent_service.process_message.call_args.kwargs
        assert call_kwargs["generate_response"] is False

    async def test_returns_early_without_agent_state(
        self, relay: GeminiWebSocketRelay, websocket: AsyncMock
    ) -> None:
        """No agent state means nothing to process."""
        relay._agent_state = None
        relay.customer_agent_service.process_message = AsyncMock()
        relay._analyze_and_send_hint = AsyncMock()  # type: ignore[method-assign]

        await relay._process_agents(salesperson_message="Hello!", websocket=websocket)

        relay.customer_agent_service.process_message.assert_not_awaited()
        relay._analyze_and_send_hint.assert_not_awaited()

    async def test_preserves_stage_progress_across_graph_invocation(
        self,
        relay: GeminiWebSocketRelay,
        agent_state: CustomerAgentState,
        websocket: AsyncMock,
    ) -> None:
        """Coach-owned stage_progress survives the LangGraph state update."""
        coach_progress = CoreStageProgress(current_stage=SalesStage.RECOMMEND)
        assert relay._agent_state is not None
        relay._agent_state["stage_progress"] = coach_progress

        # Graph returns state with a fresh (reset) stage_progress
        returned_state = dict(agent_state)
        returned_state["stage_progress"] = CoreStageProgress()
        relay.customer_agent_service.process_message = AsyncMock(return_value=("", returned_state))
        relay._analyze_and_send_hint = AsyncMock()  # type: ignore[method-assign]

        await relay._process_agents(salesperson_message="Hello!", websocket=websocket)

        assert relay._agent_state["stage_progress"] is coach_progress


class TestCurrentSystemInstruction:
    """Tests for _current_system_instruction (prompt rebuild on reconnect)."""

    def test_reflects_current_agent_state(
        self, relay: GeminiWebSocketRelay, agent_state: CustomerAgentState
    ) -> None:
        """The rebuilt prompt must reflect mutated state, not the connect-time snapshot."""
        relay._persona = OPTIMISTIC_RENOVATOR

        initial = relay._current_system_instruction()
        assert initial is not None
        assert Mood.INTERESTED.value in initial

        # Conversation soured; objection raised
        agent_state["mood"] = Mood.FRUSTRATED
        agent_state["objections_raised"] = ["price too high"]

        rebuilt = relay._current_system_instruction()
        assert rebuilt is not None
        assert rebuilt != initial
        assert Mood.FRUSTRATED.value in rebuilt

    def test_returns_none_without_persona(self, relay: GeminiWebSocketRelay) -> None:
        """No persona stored (agent init failed) -> no instruction."""
        relay._persona = None
        assert relay._current_system_instruction() is None

    def test_returns_none_without_agent_state(self, relay: GeminiWebSocketRelay) -> None:
        """No agent state -> no instruction."""
        relay._persona = OPTIMISTIC_RENOVATOR
        relay._agent_state = None
        assert relay._current_system_instruction() is None


class TestAnalysisCacheKey:
    """Tests for the stage-scoped analysis cache key (fix 3)."""

    def _setup_coach(self, relay: GeminiWebSocketRelay) -> AsyncMock:
        analyze = AsyncMock(return_value=(make_analysis(), CoreStageProgress(), None))
        relay.coach_agent_service.analyze_turn = analyze
        relay._min_hint_interval = 0.0  # disable throttle for cache tests
        return analyze

    async def test_same_message_same_stage_hits_cache(
        self, relay: GeminiWebSocketRelay, websocket: AsyncMock
    ) -> None:
        analyze = self._setup_coach(relay)

        await relay._analyze_and_send_hint("Hello!", websocket)
        await relay._analyze_and_send_hint("Hello!", websocket)

        assert analyze.await_count == 1

    async def test_same_message_different_stage_misses_cache(
        self, relay: GeminiWebSocketRelay, websocket: AsyncMock
    ) -> None:
        """Identical text at a different C.O.R.E. stage means a different analysis."""
        analyze = self._setup_coach(relay)

        await relay._analyze_and_send_hint("Hello!", websocket)

        assert relay._agent_state is not None
        relay._agent_state["stage_progress"] = CoreStageProgress(current_stage=SalesStage.OBSERVE)
        await relay._analyze_and_send_hint("Hello!", websocket)

        assert analyze.await_count == 2
