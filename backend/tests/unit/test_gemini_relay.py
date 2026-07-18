"""Unit tests for GeminiWebSocketRelay agent processing.

Covers the hardening fixes from AGENTIC_ENGINEERING.md §9:
- Independent exception scopes for customer agent vs coach (fix 1)
- Voice mode skips graph response generation (fix 2, call-site)
- Stage-scoped analysis cache key (fix 3)
"""

from unittest.mock import AsyncMock, MagicMock, patch

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

        await relay._process_agents(
            salesperson_message="Hello!", websocket=websocket, user_id="user-1"
        )

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

        await relay._process_agents(
            salesperson_message="Hello!", websocket=websocket, user_id="user-1"
        )

    async def test_skips_response_generation_in_voice_mode(
        self,
        relay: GeminiWebSocketRelay,
        agent_state: CustomerAgentState,
        websocket: AsyncMock,
    ) -> None:
        """The relay discards the graph's text, so it must not be generated (fix 2)."""
        relay.customer_agent_service.process_message = AsyncMock(return_value=("", agent_state))
        relay._analyze_and_send_hint = AsyncMock()  # type: ignore[method-assign]

        await relay._process_agents(
            salesperson_message="Hello!", websocket=websocket, user_id="user-1"
        )

        call_kwargs = relay.customer_agent_service.process_message.call_args.kwargs
        assert call_kwargs["generate_response"] is False

    async def test_returns_early_without_agent_state(
        self, relay: GeminiWebSocketRelay, websocket: AsyncMock
    ) -> None:
        """No agent state means nothing to process."""
        relay._agent_state = None
        relay.customer_agent_service.process_message = AsyncMock()
        relay._analyze_and_send_hint = AsyncMock()  # type: ignore[method-assign]

        await relay._process_agents(
            salesperson_message="Hello!", websocket=websocket, user_id="user-1"
        )

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

        await relay._process_agents(
            salesperson_message="Hello!", websocket=websocket, user_id="user-1"
        )

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


class TestSendMoodUpdate:
    """Tests for pushing customer mood to the client."""

    async def test_sends_mood_after_agent_update(
        self, relay: GeminiWebSocketRelay, websocket: AsyncMock, agent_state: CustomerAgentState
    ) -> None:
        """A successful customer-agent turn should push the new mood."""
        updated = {**agent_state, "mood": Mood.SKEPTICAL, "regard_level": RegardLevel.LOW}
        relay.customer_agent_service.process_message = AsyncMock(return_value=(None, updated))
        relay._analyze_and_send_hint = AsyncMock()  # type: ignore[method-assign]

        await relay._process_agents(
            salesperson_message="What's your budget?", websocket=websocket, user_id="user-1"
        )

        mood_events = [
            call.args[0]
            for call in websocket.send_json.call_args_list
            if call.args[0]["type"] == "mood_update"
        ]
        assert mood_events == [{"type": "mood_update", "mood": "skeptical", "regard_level": "low"}]

    async def test_no_mood_sent_when_customer_agent_fails(
        self, relay: GeminiWebSocketRelay, websocket: AsyncMock
    ) -> None:
        """A failed customer-agent turn must not report a stale mood as current."""
        relay.customer_agent_service.process_message = AsyncMock(side_effect=RuntimeError("boom"))
        relay._analyze_and_send_hint = AsyncMock()  # type: ignore[method-assign]

        await relay._process_agents(
            salesperson_message="Hello!", websocket=websocket, user_id="user-1"
        )

        assert not [
            c for c in websocket.send_json.call_args_list if c.args[0]["type"] == "mood_update"
        ]

    async def test_no_mood_sent_without_agent_state(
        self, relay: GeminiWebSocketRelay, websocket: AsyncMock
    ) -> None:
        """Should no-op when there is no agent state to report."""
        relay._agent_state = None

        await relay._send_mood_update(websocket)

        websocket.send_json.assert_not_awaited()


class TestVoiceTurnObservability:
    """Tests for the customer-voice-turn Langfuse generation (live-voice tracing)."""

    def test_full_turn_updates_and_ends_generation(self, relay: GeminiWebSocketRelay) -> None:
        """A turn's accumulated transcripts and usage land on one generation."""
        mock_generation = MagicMock()
        mock_client = MagicMock()
        mock_client.start_observation.return_value = mock_generation

        with patch("app.api.ws.gemini_relay.get_client", return_value=mock_client):
            relay._ensure_turn_observation("user-1")
            relay._ensure_turn_observation("user-1")  # lazy-open: second call is a no-op

        assert mock_client.start_observation.call_count == 1
        _, kwargs = mock_client.start_observation.call_args
        assert kwargs["as_type"] == "generation"
        assert kwargs["name"] == "customer-voice-turn"
        assert kwargs["model"] == relay._live_model

        relay._pending_user_transcription = "What's your budget?"
        relay._pending_assistant_transcription = "Around 450 to 500."
        relay._pending_usage = {"prompt_tokens": 120, "completion_tokens": 40, "total_tokens": 160}

        relay._finish_turn_observation()

        mock_generation.update.assert_called_once()
        _, update_kwargs = mock_generation.update.call_args
        assert update_kwargs["input"] == "What's your budget?"
        assert update_kwargs["output"] == "Around 450 to 500."
        assert update_kwargs["usage_details"] == {"input": 120, "output": 40, "total": 160}
        mock_generation.end.assert_called_once()

        # Per-turn state is reset so the next turn starts clean
        assert relay._turn_generation is None
        assert relay._pending_usage is None
        assert relay._turn_first_audio_at is None

    def test_input_falls_back_to_last_text_input(self, relay: GeminiWebSocketRelay) -> None:
        """Typed turns have no input_transcription event; the typed text is used instead."""
        mock_generation = MagicMock()
        mock_client = MagicMock()
        mock_client.start_observation.return_value = mock_generation

        with patch("app.api.ws.gemini_relay.get_client", return_value=mock_client):
            relay._ensure_turn_observation("user-1")

        relay._last_text_input = "typed message"
        relay._finish_turn_observation()

        _, update_kwargs = mock_generation.update.call_args
        assert update_kwargs["input"] == "typed message"

    def test_cumulative_usage_reported_as_per_turn_delta(self, relay: GeminiWebSocketRelay) -> None:
        """Gemini/Nova report cumulative session totals; Langfuse gets the per-turn delta."""
        mock_generation_1 = MagicMock()
        mock_generation_2 = MagicMock()
        mock_client = MagicMock()
        mock_client.start_observation.side_effect = [mock_generation_1, mock_generation_2]

        assert (
            relay.provider_name == "gemini"
        )  # fixture's live_provider.name; a cumulative provider

        with patch("app.api.ws.gemini_relay.get_client", return_value=mock_client):
            relay._ensure_turn_observation("user-1")
            relay._pending_usage = {
                "prompt_tokens": 100,
                "completion_tokens": 30,
                "total_tokens": 130,
            }
            relay._finish_turn_observation()

            relay._ensure_turn_observation("user-1")
            relay._pending_usage = {
                "prompt_tokens": 260,
                "completion_tokens": 70,
                "total_tokens": 330,
            }  # cumulative session total, not this turn's usage alone
            relay._finish_turn_observation()

        _, kwargs1 = mock_generation_1.update.call_args
        assert kwargs1["usage_details"] == {"input": 100, "output": 30, "total": 130}

        _, kwargs2 = mock_generation_2.update.call_args
        assert kwargs2["usage_details"] == {"input": 160, "output": 40, "total": 200}

    def test_usage_baseline_updates_without_open_generation(
        self, relay: GeminiWebSocketRelay
    ) -> None:
        """The delta baseline stays correct even on turns with no Langfuse generation."""
        relay._pending_usage = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}

        relay._finish_turn_observation()

        assert relay._usage_baseline == {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
        }

    def test_no_observation_without_session_id(self, relay: GeminiWebSocketRelay) -> None:
        """No session means nothing to correlate the trace to — skip entirely."""
        relay._session_id = None
        mock_client = MagicMock()

        with patch("app.api.ws.gemini_relay.get_client", return_value=mock_client):
            relay._ensure_turn_observation("user-1")

        mock_client.start_observation.assert_not_called()

    def test_start_observation_failure_is_non_fatal(self, relay: GeminiWebSocketRelay) -> None:
        """A Langfuse outage on turn-open must not interrupt the voice session."""
        mock_client = MagicMock()
        mock_client.start_observation.side_effect = RuntimeError("langfuse down")

        with patch("app.api.ws.gemini_relay.get_client", return_value=mock_client):
            relay._ensure_turn_observation("user-1")  # must not raise

        assert relay._turn_generation is None

    def test_update_failure_is_non_fatal_and_resets_state(
        self, relay: GeminiWebSocketRelay
    ) -> None:
        """A Langfuse outage on turn-close must not interrupt the voice session."""
        mock_generation = MagicMock()
        mock_generation.update.side_effect = RuntimeError("network blip")
        mock_client = MagicMock()
        mock_client.start_observation.return_value = mock_generation

        with patch("app.api.ws.gemini_relay.get_client", return_value=mock_client):
            relay._ensure_turn_observation("user-1")
            relay._pending_usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
            relay._finish_turn_observation()  # must not raise

        assert relay._turn_generation is None
        assert relay._pending_usage is None


class TestInterruptedRelay:
    """Barge-in events from the provider must reach the client immediately."""

    async def test_interrupted_event_forwarded_to_client(
        self, relay: GeminiWebSocketRelay, websocket: AsyncMock
    ) -> None:
        live_session = MagicMock()

        async def _events():
            yield {"type": "interrupted", "audio_data": None, "text": None}

        live_session.receive = _events

        await relay._relay_gemini_to_client(websocket, live_session, user_id="user-1")

        websocket.send_json.assert_awaited_once_with({"type": "interrupted"})
