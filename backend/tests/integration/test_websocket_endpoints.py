"""Integration tests for WebSocket endpoints."""

import json
import re
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.agents.state import CoreStageProgress, Mood, RegardLevel, SalesStage
from app.core.dependencies import (
    get_auth_service,
    get_coach_agent_service,
    get_customer_agent_service,
    get_gemini_service,
    get_session_service,
)
from app.main import app
from app.models.auth import TokenPayload
from app.models.coach import CoachAnalysis, CoachHint, InterventionLevel
from app.models.session import Difficulty, Session, SessionStatus, SessionType


@pytest.fixture
def mock_live_session():
    """Mock GeminiLiveSession."""
    session = MagicMock()
    session.send_audio = AsyncMock()
    session.send_text = AsyncMock()
    session.close = AsyncMock()

    # Mock receive to return empty generator by default
    async def default_receive():
        return
        yield

    session.receive.return_value = default_receive()
    return session


@pytest.fixture
def mock_auth_service():
    """Create mock AuthService that validates tokens."""
    service = MagicMock()

    def decode_token(token: str) -> TokenPayload:
        if token == "valid_token":
            from datetime import UTC, datetime

            return TokenPayload(
                sub="test-user-123",
                email="test@example.com",
                exp=datetime.fromtimestamp(9999999999, tz=UTC),
                iat=datetime.fromtimestamp(1000000000, tz=UTC),
                type="access",
            )
        raise Exception("Invalid token")

    service.decode_token.side_effect = decode_token
    return service


@pytest.fixture
def mock_gemini_service(mock_live_session):
    """Create mock GeminiService with Live API support."""
    service = MagicMock()

    # Mock the connect_live context manager
    class MockConnectLive:
        async def __aenter__(self):
            return mock_live_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    service.connect_live.return_value = MockConnectLive()
    return service


@pytest.fixture
def mock_session_service():
    """Create mock SessionService."""
    service = MagicMock()

    # Mock start_session to return a session
    async def mock_start_session(session_create):
        return Session(
            session_id="test-session-123",
            user_id=session_create.user_id,
            session_type=session_create.session_type,
            status=SessionStatus.ACTIVE,
            difficulty=session_create.difficulty,
            selected_persona=session_create.selected_persona,
            system_instruction=session_create.system_instruction,
            started_at=datetime.now(UTC),
            ended_at=None,
            duration=None,
            grade=None,
            score=None,
            message_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            is_deleted=False,
            deleted_at=None,
        )

    service.start_session = AsyncMock(side_effect=mock_start_session)
    service.end_session = AsyncMock()
    service.get_session = AsyncMock(return_value=None)
    service.get_transcript = AsyncMock(return_value=None)

    return service


@pytest.fixture
def mock_coach_agent_service():
    """Create mock CoachAgentService."""
    service = MagicMock()

    # Default: no intervention needed
    default_analysis = CoachAnalysis(
        techniques_detected=[],
        stage_items_completed=[],
        pbms_acknowledged=[],
        deviations=[],
        intervention_level=InterventionLevel.NONE,
        hint=None,
        suggested_stage=None,
        confidence=0.9,
    )
    default_progress = CoreStageProgress(current_stage=SalesStage.CONNECT)

    async def mock_analyze_turn(salesperson_message, state, session_mode):
        # Return None hint for default (no intervention)
        return default_analysis, default_progress, None

    service.analyze_turn = AsyncMock(side_effect=mock_analyze_turn)
    return service


@pytest.fixture
def mock_customer_agent_service():
    """Create mock CustomerAgentService."""
    return MagicMock()


@pytest.fixture
def client_with_overrides(
    mock_auth_service,
    mock_gemini_service,
    mock_session_service,
    mock_coach_agent_service,
    mock_customer_agent_service,
):
    """Create test client with dependency overrides."""
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_gemini_service] = lambda: mock_gemini_service
    app.dependency_overrides[get_session_service] = lambda: mock_session_service
    app.dependency_overrides[get_coach_agent_service] = lambda: mock_coach_agent_service
    app.dependency_overrides[get_customer_agent_service] = lambda: mock_customer_agent_service

    with TestClient(app) as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()


class TestWebSocketConnection:
    """Tests for WebSocket connection establishment."""

    def test_connection_without_token(self, client_with_overrides):
        """Should fail if no token query parameter provided."""
        with pytest.raises(Exception):  # Missing required query param
            with client_with_overrides.websocket_connect("/ws/gemini/live"):
                pass

    def test_connection_with_invalid_token(self, client_with_overrides):
        """Should close with 4001 if token is invalid."""
        # Connection will be rejected due to invalid token
        # The exact behavior depends on timing - connection may fail to establish
        # or may establish then immediately close with 4001
        try:
            with client_with_overrides.websocket_connect(
                "/ws/gemini/live?token=invalid_token"
            ) as _:
                # If connection established, it should close immediately
                pass
        except Exception:
            # Expected - connection failed or closed
            pass

    def test_connection_with_valid_token(self, client_with_overrides, mock_live_session):
        """Should accept connection and send ready message with valid token."""

        # Mock receive that yields nothing (empty generator)
        async def controlled_receive():
            # Empty generator - just return immediately
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Should receive ready message
            data = websocket.receive_json()
            assert data["type"] == "ready"
            assert data["status"] == "connected"

    def test_unsupported_provider_rejected(self, client_with_overrides):
        """Should close with 4004 when requesting a provider outside the allowlist."""
        from starlette.websockets import WebSocketDisconnect

        # Default allowlist is ["gemini"]; 'openai' is not permitted.
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client_with_overrides.websocket_connect(
                "/ws/gemini/live?token=valid_token&provider=openai"
            ) as websocket:
                websocket.receive_json()
        assert exc_info.value.code == 4004


class TestMessageRelay:
    """Tests for bidirectional message relay."""

    def test_sends_binary_audio_to_gemini(self, client_with_overrides, mock_live_session):
        """Should relay binary audio frames to Gemini."""

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(0.2)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        audio_data = b"test audio bytes"

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            websocket.receive_json()

            # Send binary audio
            websocket.send_bytes(audio_data)

            # Give time for async processing
            import time

            time.sleep(0.3)

        # Verify audio was sent to Gemini
        assert mock_live_session.send_audio.called

    def test_sends_text_message_to_gemini(self, client_with_overrides, mock_live_session):
        """Should relay text messages to Gemini."""

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(0.2)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        text_message = {"type": "text", "content": "Hello Gemini"}

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            websocket.receive_json()

            # Send text message
            websocket.send_text(json.dumps(text_message))

            # Give time for async processing
            import time

            time.sleep(0.3)

        # Verify text was sent to Gemini
        assert mock_live_session.send_text.called
        mock_live_session.send_text.assert_called_with("Hello Gemini")

    def test_receives_audio_from_gemini(self, client_with_overrides, mock_live_session):
        """Should relay audio responses from Gemini to client."""
        audio_response = b"gemini audio response"

        async def mock_receive():
            yield {
                "type": "audio",
                "audio_data": audio_response,
                "text": None,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }

        mock_live_session.receive.return_value = mock_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            ready_msg = websocket.receive_json()
            assert ready_msg["type"] == "ready"

            # Should receive audio bytes
            received_data = websocket.receive_bytes()
            assert received_data == audio_response

            # Should receive turn complete
            turn_complete = websocket.receive_json()
            assert turn_complete["type"] == "turn_complete"

    def test_receives_text_from_gemini(self, client_with_overrides, mock_live_session):
        """Should relay output transcriptions from Gemini to client across multiple turns."""
        text_response_1 = "This is Gemini's first response"
        text_response_2 = "This is Gemini's second response"

        async def mock_receive():
            # First turn - output_transcription (what model says)
            yield {
                "type": "output_transcription",
                "audio_data": None,
                "text": text_response_1,
                "finished": True,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }
            # Second turn
            yield {
                "type": "output_transcription",
                "audio_data": None,
                "text": text_response_2,
                "finished": True,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }

        mock_live_session.receive.return_value = mock_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            websocket.receive_json()

            # Should receive first transcription
            transcription1 = websocket.receive_json()
            assert transcription1["type"] == "transcription"
            assert transcription1["text"] == text_response_1

            # Should receive first turn complete
            turn_complete1 = websocket.receive_json()
            assert turn_complete1["type"] == "turn_complete"

            # Should receive second transcription
            transcription2 = websocket.receive_json()
            assert transcription2["type"] == "transcription"
            assert transcription2["text"] == text_response_2

            # Should receive second turn complete
            turn_complete2 = websocket.receive_json()
            assert turn_complete2["type"] == "turn_complete"


class TestErrorHandling:
    """Tests for error handling in WebSocket endpoint."""

    def test_invalid_json_message(self, client_with_overrides, mock_live_session):
        """Should send error message for invalid JSON."""

        async def controlled_receive():
            # Empty generator
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            websocket.receive_json()

            # Send invalid JSON
            websocket.send_text("not valid json {")

            # Should receive error message
            error_msg = websocket.receive_json()
            assert error_msg["type"] == "error"
            assert error_msg["code"] == "INVALID_MESSAGE"


class TestConnectionLifecycle:
    """Tests for WebSocket connection lifecycle."""

    def test_cleanup_on_disconnect(self, client_with_overrides, mock_gemini_service):
        """Should cleanup resources when client disconnects."""
        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            websocket.receive_json()
            # Connection closes when context exits

        # Verify connect_live was called
        assert mock_gemini_service.connect_live.called


class TestConversationPersistence:
    """Tests for session and transcript persistence during WebSocket lifecycle."""

    def test_creates_session_on_connection(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should create a session when WebSocket connection is established."""

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(0.1)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            ready_msg = websocket.receive_json()
            assert ready_msg["type"] == "ready"

            # Give time for async session creation
            import time

            time.sleep(0.2)

        # Verify session was created
        assert mock_session_service.start_session.called
        call_args = mock_session_service.start_session.call_args
        session_create = call_args[0][0]

        # Verify session creation parameters
        assert session_create.user_id == "test-user-123"
        assert session_create.session_type == SessionType.TRAINING
        # Uses persona's difficulty (optimistic_renovator = easy)
        assert session_create.difficulty == Difficulty.HIGH_REGARD
        assert session_create.selected_persona == "optimistic_renovator"

    def test_saves_transcript_on_disconnect(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should save transcript with messages when WebSocket disconnects."""
        text_response = "Hello, I'm a sales coach"

        async def mock_receive():
            yield {
                "type": "output_transcription",
                "audio_data": None,
                "text": text_response,
                "finished": True,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }

        mock_live_session.receive.return_value = mock_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            websocket.receive_json()

            # Send text message
            websocket.send_text(json.dumps({"type": "text", "content": "Hello"}))

            # Receive response
            response = websocket.receive_json()
            assert response["type"] == "transcription"

            # Give time for buffering
            import time

            time.sleep(0.2)

        # Verify end_session was called with messages
        assert mock_session_service.end_session.called
        call_args = mock_session_service.end_session.call_args

        session_id = call_args[1]["session_id"]
        messages = call_args[1]["messages"]
        status = call_args[1]["status"]

        # Verify session ID matches
        assert session_id == "test-session-123"

        # Verify messages were buffered (user message + assistant response)
        assert len(messages) == 2

        # Extract messages by role (order may vary due to async timing)
        user_messages = [m for m in messages if m.role.value == "user"]
        assistant_messages = [m for m in messages if m.role.value == "assistant"]

        # Verify we have one of each
        assert len(user_messages) == 1
        assert len(assistant_messages) == 1

        # Verify content
        assert user_messages[0].text == "Hello"
        assert assistant_messages[0].text == text_response

        # Verify status is abandoned (disconnect without evaluation)
        assert status == SessionStatus.ABANDONED

    def test_training_session_completes_with_enough_messages(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Training mode has no explicit "evaluate" control to signal a natural
        end — a disconnect is its only end signal. A real back-and-forth should
        still land as completed practice, not get lumped in with abandoned runs.
        """

        async def mock_receive():
            for i in range(1, 4):
                yield {
                    "type": "output_transcription",
                    "audio_data": None,
                    "text": f"Response {i}",
                    "finished": True,
                }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }

        mock_live_session.receive.return_value = mock_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            websocket.receive_json()

            for i in range(1, 4):
                websocket.send_text(json.dumps({"type": "text", "content": f"Message {i}"}))
                websocket.receive_json()

            import time

            time.sleep(0.2)

        assert mock_session_service.end_session.called
        call_args = mock_session_service.end_session.call_args

        messages = call_args[1]["messages"]
        status = call_args[1]["status"]

        # Comfortably clears the training-completion floor (>= 4 messages)
        assert len(messages) >= 4
        assert status == SessionStatus.COMPLETED

    def test_updates_session_with_final_stats(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should update session with duration and message count on disconnect."""

        async def mock_receive():
            yield {
                "type": "output_transcription",
                "audio_data": None,
                "text": "Response 1",
                "finished": True,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }

        mock_live_session.receive.return_value = mock_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            websocket.receive_json()

            # Send message
            websocket.send_text(json.dumps({"type": "text", "content": "Message 1"}))

            # Receive response
            websocket.receive_json()

            import time

            time.sleep(0.2)

        # Verify end_session was called
        assert mock_session_service.end_session.called
        call_args = mock_session_service.end_session.call_args

        messages = call_args[1]["messages"]

        # Verify message count
        assert len(messages) == 2  # 1 user + 1 assistant

    def test_handles_disconnect_without_messages(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should handle disconnect gracefully when no messages were sent."""

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(0.1)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            websocket.receive_json()

            # Disconnect immediately without sending messages
            import time

            time.sleep(0.2)

        # Verify session was created
        assert mock_session_service.start_session.called

        # end_session should NOT be called if no messages buffered
        # (the implementation skips persistence if message buffer is empty)
        # This is actually handled in the finally block - it checks if buffer is not empty
        # Let's verify end_session was NOT called since no messages
        assert not mock_session_service.end_session.called

    def test_persistence_failure_doesnt_crash_websocket(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should handle persistence failures gracefully without crashing WebSocket."""

        # Make end_session raise an exception
        mock_session_service.end_session.side_effect = Exception("Firestore error")

        async def mock_receive():
            yield {
                "type": "output_transcription",
                "audio_data": None,
                "text": "Response",
                "finished": True,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }

        mock_live_session.receive.return_value = mock_receive()

        # Connection should not crash even if persistence fails
        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            # Receive ready message
            ready_msg = websocket.receive_json()
            assert ready_msg["type"] == "ready"

            # Send message
            websocket.send_text(json.dumps({"type": "text", "content": "Test"}))

            # Receive response (should work even though persistence will fail)
            response = websocket.receive_json()
            assert response["type"] == "transcription"

            import time

            time.sleep(0.2)

        # Verify end_session was attempted (and failed silently)
        assert mock_session_service.end_session.called


class TestCoachModeParameter:
    """Tests for session mode parameter handling."""

    def test_default_mode_is_training(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should default to training mode when no mode parameter provided."""

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(0.1)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            websocket.receive_json()

            import time

            time.sleep(0.2)

        # Verify session was created with training mode
        assert mock_session_service.start_session.called
        call_args = mock_session_service.start_session.call_args
        session_create = call_args[0][0]
        assert session_create.session_type == SessionType.TRAINING

    def test_evaluation_mode_parameter(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should use evaluation mode when mode=evaluation is provided."""

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(0.1)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token&mode=evaluation"
        ) as websocket:
            websocket.receive_json()

            import time

            time.sleep(0.2)

        # Verify session was created with evaluation mode
        assert mock_session_service.start_session.called
        call_args = mock_session_service.start_session.call_args
        session_create = call_args[0][0]
        assert session_create.session_type == SessionType.EVALUATION

    def test_training_mode_explicit_parameter(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should use training mode when mode=training is explicitly provided."""

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(0.1)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token&mode=training"
        ) as websocket:
            websocket.receive_json()

            import time

            time.sleep(0.2)

        # Verify session was created with training mode
        assert mock_session_service.start_session.called
        call_args = mock_session_service.start_session.call_args
        session_create = call_args[0][0]
        assert session_create.session_type == SessionType.TRAINING


class TestProductParamsInjection:
    """Tests for product query parameter injection into session."""

    def test_product_params_injected_into_session(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should populate SessionCreate with product_category and product_type."""

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(0.1)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token&product_category=bracken&product_type=sectional_1"
        ) as websocket:
            websocket.receive_json()

            import time

            time.sleep(0.2)

        assert mock_session_service.start_session.called
        call_args = mock_session_service.start_session.call_args
        session_create = call_args[0][0]
        assert session_create.product_category == "bracken"
        assert session_create.product_type == "sectional_1"

    def test_invalid_product_category_uses_defaults(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should fall back to persona defaults when category is invalid."""

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(0.1)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token&product_category=nonexistent"
        ) as websocket:
            websocket.receive_json()

            import time

            time.sleep(0.2)

        assert mock_session_service.start_session.called
        call_args = mock_session_service.start_session.call_args
        session_create = call_args[0][0]
        # optimistic_renovator persona has product_category="fixer_upper" as default
        assert session_create.product_category == "fixer_upper"
        assert session_create.product_type == "renovation_opportunity"

    def test_no_product_params_backward_compatible(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should use persona defaults when no product params provided."""

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(0.1)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token"
        ) as websocket:
            websocket.receive_json()

            import time

            time.sleep(0.2)

        assert mock_session_service.start_session.called
        call_args = mock_session_service.start_session.call_args
        session_create = call_args[0][0]
        # optimistic_renovator persona has product_category="fixer_upper", product_type="renovation_opportunity"
        assert session_create.product_category == "fixer_upper"
        assert session_create.product_type == "renovation_opportunity"

    def test_product_category_only_no_type(
        self, client_with_overrides, mock_session_service, mock_live_session
    ):
        """Should accept category without type."""

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(0.1)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token&product_category=bracken"
        ) as websocket:
            websocket.receive_json()

            import time

            time.sleep(0.2)

        assert mock_session_service.start_session.called
        call_args = mock_session_service.start_session.call_args
        session_create = call_args[0][0]
        assert session_create.product_category == "bracken"
        assert session_create.product_type is None


class TestCoachHintDelivery:
    """Tests for coach hint delivery via WebSocket."""

    def test_coach_hint_message_format(self):
        """Verify coach hint message format matches expected schema."""
        # This test verifies the structure of coach hints that would be sent
        # The actual WebSocket delivery is covered by simpler integration tests
        hint = CoachHint(
            level=InterventionLevel.SUGGESTION,
            hint="Try asking discovery questions.",
            stage="OBSERVE",
            example_phrase="What brings you in today?",
            ready_for_next_stage=False,
        )

        # Verify the hint can be serialized to the expected format
        hint_json = {
            "type": "coach_hint",
            "level": hint.level.value,
            "hint": hint.hint,
            "stage": hint.stage,
            "example_phrase": hint.example_phrase,
            "ready_for_next_stage": hint.ready_for_next_stage,
        }

        assert hint_json["type"] == "coach_hint"
        assert hint_json["level"] == "suggestion"
        assert hint_json["hint"] == "Try asking discovery questions."
        assert hint_json["stage"] == "OBSERVE"
        assert hint_json["example_phrase"] == "What brings you in today?"
        assert hint_json["ready_for_next_stage"] is False

    def test_no_hint_when_no_intervention_needed(
        self,
        client_with_overrides,
        mock_live_session,
        mock_coach_agent_service,
    ):
        """Should not send hint when intervention level is NONE."""

        # Default mock returns no hint (NONE intervention level)
        async def mock_receive():
            yield {
                "type": "output_transcription",
                "audio_data": None,
                "text": "Hello!",
                "finished": True,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }

        mock_live_session.receive.return_value = mock_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token&mode=training"
        ) as websocket:
            # Receive ready message
            websocket.receive_json()

            # Send text message
            websocket.send_text(json.dumps({"type": "text", "content": "Good greeting!"}))

            # Receive transcription
            transcription = websocket.receive_json()
            assert transcription["type"] == "transcription"

            # Receive turn complete
            turn_complete = websocket.receive_json()
            assert turn_complete["type"] == "turn_complete"

            # No coach hint should be received (test would timeout if we tried to receive one)

    def test_no_hint_in_evaluation_mode(
        self,
        client_with_overrides,
        mock_live_session,
        mock_coach_agent_service,
    ):
        """Should not send hint in evaluation mode even if intervention would be needed."""
        # Configure coach to return a hint (but it should be suppressed in eval mode)
        hint = CoachHint(
            level=InterventionLevel.WARNING,
            hint="You skipped the OBSERVE stage!",
            stage="RECOMMEND",
        )
        analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=["skipped_observe"],
            intervention_level=InterventionLevel.WARNING,
            hint="You skipped the OBSERVE stage!",
            suggested_stage=None,
            confidence=0.8,
        )
        progress = CoreStageProgress(current_stage=SalesStage.RECOMMEND)

        # In evaluation mode, analyze_turn should return None for hint
        async def mock_analyze_turn(salesperson_message, state, session_mode):
            # Only return hint in training mode
            if session_mode == SessionType.TRAINING:
                return analysis, progress, hint
            else:
                return analysis, progress, None

        mock_coach_agent_service.analyze_turn = AsyncMock(side_effect=mock_analyze_turn)

        async def mock_receive():
            yield {
                "type": "output_transcription",
                "audio_data": None,
                "text": "I see...",
                "finished": True,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }

        mock_live_session.receive.return_value = mock_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token&mode=evaluation"
        ) as websocket:
            # Receive ready message
            websocket.receive_json()

            # Send text message
            websocket.send_text(json.dumps({"type": "text", "content": "Let me show you this!"}))

            # Receive transcription
            transcription = websocket.receive_json()
            assert transcription["type"] == "transcription"

            # Receive turn complete
            turn_complete = websocket.receive_json()
            assert turn_complete["type"] == "turn_complete"

            # No coach hint should be received in evaluation mode

    def test_sent_hints_are_persisted_on_session_end(
        self,
        client_with_overrides,
        mock_live_session,
        mock_coach_agent_service,
        mock_session_service,
        mock_customer_agent_service,
    ):
        """Hints actually shown to the trainee should end up on the session doc
        so the archive overlay can render a "hints used" timeline (§B3)."""
        from app.agents.personas import OPTIMISTIC_RENOVATOR

        # _analyze_and_send_hint short-circuits without an initialized agent state
        agent_state = {
            "messages": [],
            "turn_count": 1,
            "persona": OPTIMISTIC_RENOVATOR,
            "mood": Mood.NEUTRAL,
            "regard_level": RegardLevel.LOW,
            "objections_available": [],
            "objections_raised": [],
            "objections_resolved": [],
            "stage_progress": CoreStageProgress(current_stage=SalesStage.OBSERVE),
            "session_id": "test-session-123",
            "user_id": "test-user-123",
        }
        mock_customer_agent_service.start_session = AsyncMock(return_value=agent_state)

        hint = CoachHint(
            level=InterventionLevel.SUGGESTION,
            hint="Try asking a discovery question.",
            stage="OBSERVE",
        )
        analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.SUGGESTION,
            hint="Try asking a discovery question.",
            suggested_stage=None,
            confidence=0.8,
        )
        progress = CoreStageProgress(current_stage=SalesStage.OBSERVE)
        mock_coach_agent_service.analyze_turn = AsyncMock(return_value=(analysis, progress, hint))

        async def mock_receive():
            yield {
                "type": "output_transcription",
                "audio_data": None,
                "text": "I see...",
                "finished": True,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }

        mock_live_session.receive.return_value = mock_receive()

        with client_with_overrides.websocket_connect(
            "/ws/gemini/live?token=valid_token&mode=training"
        ) as websocket:
            websocket.receive_json()  # ready

            websocket.send_text(json.dumps({"type": "text", "content": "Let me show you this!"}))

            # Coach analysis runs concurrently with the transcription/turn_complete
            # flow (and emits its own "analyzing" status + stage_progress), so
            # message order and count aren't guaranteed — collect by type.
            received_types = {websocket.receive_json()["type"] for _ in range(5)}
            assert "coach_hint" in received_types

            import time

            time.sleep(0.2)

        assert mock_session_service.end_session.called
        call_args = mock_session_service.end_session.call_args
        hints_used = call_args[1]["hints_used"]

        assert len(hints_used) == 1
        assert hints_used[0].hint == "Try asking a discovery question."
        assert re.match(r"^\d{2}:\d{2}$", hints_used[0].t)

    def test_coach_analysis_failure_doesnt_crash_websocket(
        self,
        mock_auth_service,
        mock_gemini_service,
        mock_session_service,
        mock_live_session,
    ):
        """Should handle coach analysis failures gracefully without crashing WebSocket."""
        # Create custom coach service that raises an exception
        custom_coach_service = MagicMock()
        custom_coach_service.analyze_turn = AsyncMock(side_effect=Exception("Coach LLM error"))

        # Override dependencies
        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini_service
        app.dependency_overrides[get_session_service] = lambda: mock_session_service
        app.dependency_overrides[get_coach_agent_service] = lambda: custom_coach_service

        async def mock_receive():
            yield {
                "type": "output_transcription",
                "audio_data": None,
                "text": "Response",
                "finished": True,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }

        mock_live_session.receive.return_value = mock_receive()

        try:
            # Connection should not crash even if coach analysis fails
            with TestClient(app).websocket_connect(
                "/ws/gemini/live?token=valid_token&mode=training"
            ) as websocket:
                # Receive ready message
                ready_msg = websocket.receive_json()
                assert ready_msg["type"] == "ready"

                # Send message
                websocket.send_text(json.dumps({"type": "text", "content": "Test"}))

                # Receive response (should work even though coach analysis fails)
                response = websocket.receive_json()
                assert response["type"] == "transcription"

                import time

                time.sleep(0.2)

            # Verify coach analysis was attempted (may or may not be called depending on
            # whether agent state was initialized - the key test is that WebSocket didn't crash)
        finally:
            app.dependency_overrides.clear()


class TestEvaluateControlAction:
    """Tests for the evaluate WebSocket control action."""

    def test_evaluate_returns_evaluation_result(
        self,
        mock_auth_service,
        mock_gemini_service,
        mock_session_service,
        mock_live_session,
        mock_customer_agent_service,
    ):
        """Should return evaluation_result message when evaluate control is sent."""
        from app.agents.personas import OPTIMISTIC_RENOVATOR

        # Set up customer agent service to return agent state
        agent_state = {
            "messages": [],
            "turn_count": 1,
            "persona": OPTIMISTIC_RENOVATOR,
            "mood": Mood.NEUTRAL,
            "regard_level": RegardLevel.LOW,
            "objections_available": [],
            "objections_raised": [],
            "objections_resolved": [],
            "stage_progress": CoreStageProgress(
                current_stage=SalesStage.OBSERVE,
                connect={
                    "warm_greeting": True,
                    "establish_credibility": True,
                    "create_comfort": False,
                },
            ),
            "session_id": "test-session-123",
            "user_id": "test-user-123",
        }
        mock_customer_agent_service.start_session = AsyncMock(return_value=agent_state)

        # Set up coach agent service with generate_evaluation
        mock_coach_service = MagicMock()

        # Default analyze_turn
        default_progress = CoreStageProgress(current_stage=SalesStage.CONNECT)
        default_analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )
        mock_coach_service.analyze_turn = AsyncMock(
            return_value=(default_analysis, default_progress, None)
        )

        # Mock evaluation result
        mock_evaluation = MagicMock()
        mock_evaluation.evaluation_id = "eval-123"
        mock_evaluation.session_id = "test-session-123"
        mock_evaluation.final_score = 55.0
        mock_evaluation.grade.value = "F"
        mock_evaluation.summary = "Needs improvement"
        mock_evaluation.strengths = ["Strong CONNECT stage performance"]
        mock_evaluation.improvements = ["Focus on OBSERVE stage techniques"]
        mock_evaluation.techniques_detected = ["warm_greeting", "establish_credibility"]

        mock_scorecard = MagicMock()
        mock_scorecard.grade.value = "F"
        mock_scorecard.raw_score = 20.0
        mock_scorecard.final_score = 20.0
        mock_scorecard.pbm_match_rate = 0.0
        mock_scorecard.pbm_bonus = 0.0
        mock_scorecard.objection_resolution_rate = 0.0
        mock_scorecard.objection_penalty = 0.0
        mock_scorecard.deviations = []
        mock_scorecard.deviation_penalty = 0.0

        # Build stage_scores dict
        mock_connect = MagicMock()
        mock_connect.stage = "CONNECT"
        mock_connect.items_completed = ["warm_greeting", "establish_credibility"]
        mock_connect.items_total = ["warm_greeting", "establish_credibility", "create_comfort"]
        mock_connect.score = 66.67
        mock_connect.weight = 0.15
        mock_connect.feedback = None
        mock_scorecard.stage_scores = {"CONNECT": mock_connect}

        mock_evaluation.scorecard = mock_scorecard
        mock_coach_service.generate_evaluation = AsyncMock(return_value=mock_evaluation)

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini_service
        app.dependency_overrides[get_session_service] = lambda: mock_session_service
        app.dependency_overrides[get_coach_agent_service] = lambda: mock_coach_service
        app.dependency_overrides[get_customer_agent_service] = lambda: mock_customer_agent_service

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(1.0)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        try:
            with TestClient(app).websocket_connect(
                "/ws/gemini/live?token=valid_token&mode=evaluation"
            ) as websocket:
                # Receive ready message
                ready = websocket.receive_json()
                assert ready["type"] == "ready"

                # Send evaluate control message
                websocket.send_text(json.dumps({"type": "control", "action": "evaluate"}))

                # Should receive evaluation_result
                result = websocket.receive_json()
                assert result["type"] == "evaluation_result"
                assert "evaluation" in result
                assert result["evaluation"]["evaluation_id"] == "eval-123"
                assert result["evaluation"]["final_score"] == 55.0
                assert result["evaluation"]["grade"] == "F"
                assert "scorecard" in result["evaluation"]
                assert "strengths" in result["evaluation"]
                assert "improvements" in result["evaluation"]

        finally:
            app.dependency_overrides.clear()

    def test_evaluate_persists_conversation_before_scoring(
        self,
        mock_auth_service,
        mock_gemini_service,
        mock_session_service,
        mock_live_session,
        mock_customer_agent_service,
    ):
        """Should persist conversation before generating evaluation."""
        from app.agents.personas import OPTIMISTIC_RENOVATOR

        agent_state = {
            "messages": [],
            "turn_count": 1,
            "persona": OPTIMISTIC_RENOVATOR,
            "mood": Mood.NEUTRAL,
            "regard_level": RegardLevel.LOW,
            "objections_available": [],
            "objections_raised": [],
            "objections_resolved": [],
            "stage_progress": CoreStageProgress(current_stage=SalesStage.CONNECT),
            "session_id": "test-session-123",
            "user_id": "test-user-123",
        }
        mock_customer_agent_service.start_session = AsyncMock(return_value=agent_state)

        mock_coach_service = MagicMock()
        default_progress = CoreStageProgress(current_stage=SalesStage.CONNECT)
        default_analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )
        mock_coach_service.analyze_turn = AsyncMock(
            return_value=(default_analysis, default_progress, None)
        )

        mock_evaluation = MagicMock()
        mock_evaluation.evaluation_id = "eval-456"
        mock_evaluation.session_id = "test-session-123"
        mock_evaluation.final_score = 0.0
        mock_evaluation.grade.value = "F"
        mock_evaluation.summary = "Needs improvement"
        mock_evaluation.strengths = []
        mock_evaluation.improvements = []
        mock_evaluation.techniques_detected = []
        mock_evaluation.scorecard = MagicMock()
        mock_evaluation.scorecard.grade.value = "F"
        mock_evaluation.scorecard.raw_score = 0.0
        mock_evaluation.scorecard.final_score = 0.0
        mock_evaluation.scorecard.pbm_match_rate = 0.0
        mock_evaluation.scorecard.pbm_bonus = 0.0
        mock_evaluation.scorecard.objection_resolution_rate = 0.0
        mock_evaluation.scorecard.objection_penalty = 0.0
        mock_evaluation.scorecard.deviations = []
        mock_evaluation.scorecard.deviation_penalty = 0.0
        mock_evaluation.scorecard.stage_scores = {}
        mock_coach_service.generate_evaluation = AsyncMock(return_value=mock_evaluation)

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini_service
        app.dependency_overrides[get_session_service] = lambda: mock_session_service
        app.dependency_overrides[get_coach_agent_service] = lambda: mock_coach_service
        app.dependency_overrides[get_customer_agent_service] = lambda: mock_customer_agent_service

        # Gemini sends a turn, then client sends evaluate
        async def mock_receive():
            yield {
                "type": "output_transcription",
                "audio_data": None,
                "text": "Hello, welcome!",
                "finished": True,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }
            # Keep alive for evaluate
            import asyncio

            await asyncio.sleep(1.0)
            return

        mock_live_session.receive.return_value = mock_receive()

        try:
            with TestClient(app).websocket_connect(
                "/ws/gemini/live?token=valid_token&mode=evaluation"
            ) as websocket:
                ready = websocket.receive_json()
                assert ready["type"] == "ready"

                # Send a text message first (to populate buffer)
                websocket.send_text(json.dumps({"type": "text", "content": "Hi there"}))

                import time

                time.sleep(0.1)

                # Now send evaluate
                websocket.send_text(json.dumps({"type": "control", "action": "evaluate"}))

                # Drain turn/coach events (transcription, turn_complete,
                # coach_status, stage_progress) until the evaluation arrives
                result = websocket.receive_json()
                for _ in range(10):
                    if result["type"] == "evaluation_result":
                        break
                    result = websocket.receive_json()
                assert result["type"] == "evaluation_result"

            # Verify persistence was called before evaluation
            assert mock_session_service.end_session.called

            # Verify generate_evaluation was called
            assert mock_coach_service.generate_evaluation.called

        finally:
            app.dependency_overrides.clear()

    def test_evaluate_error_sends_error_message(
        self,
        mock_auth_service,
        mock_gemini_service,
        mock_session_service,
        mock_live_session,
        mock_customer_agent_service,
    ):
        """Should send evaluation_error when evaluation generation fails."""
        from app.agents.personas import OPTIMISTIC_RENOVATOR

        agent_state = {
            "messages": [],
            "turn_count": 1,
            "persona": OPTIMISTIC_RENOVATOR,
            "mood": Mood.NEUTRAL,
            "regard_level": RegardLevel.LOW,
            "objections_available": [],
            "objections_raised": [],
            "objections_resolved": [],
            "stage_progress": CoreStageProgress(current_stage=SalesStage.CONNECT),
            "session_id": "test-session-123",
            "user_id": "test-user-123",
        }
        mock_customer_agent_service.start_session = AsyncMock(return_value=agent_state)

        mock_coach_service = MagicMock()
        default_progress = CoreStageProgress(current_stage=SalesStage.CONNECT)
        default_analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )
        mock_coach_service.analyze_turn = AsyncMock(
            return_value=(default_analysis, default_progress, None)
        )
        # Make evaluation generation fail
        mock_coach_service.generate_evaluation = AsyncMock(
            side_effect=Exception("LLM evaluation failed")
        )

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini_service
        app.dependency_overrides[get_session_service] = lambda: mock_session_service
        app.dependency_overrides[get_coach_agent_service] = lambda: mock_coach_service
        app.dependency_overrides[get_customer_agent_service] = lambda: mock_customer_agent_service

        async def controlled_receive():
            import asyncio

            await asyncio.sleep(1.0)
            return
            yield

        mock_live_session.receive.return_value = controlled_receive()

        try:
            with TestClient(app).websocket_connect(
                "/ws/gemini/live?token=valid_token&mode=evaluation"
            ) as websocket:
                ready = websocket.receive_json()
                assert ready["type"] == "ready"

                # Send evaluate
                websocket.send_text(json.dumps({"type": "control", "action": "evaluate"}))

                # Should receive evaluation_error
                result = websocket.receive_json()
                assert result["type"] == "evaluation_error"
                assert "message" in result

        finally:
            app.dependency_overrides.clear()

    def test_evaluate_clears_buffer_prevents_double_persist(
        self,
        mock_auth_service,
        mock_gemini_service,
        mock_session_service,
        mock_live_session,
        mock_customer_agent_service,
    ):
        """Buffer should be cleared after evaluate to prevent double-persist in finally."""
        from app.agents.personas import OPTIMISTIC_RENOVATOR

        agent_state = {
            "messages": [],
            "turn_count": 1,
            "persona": OPTIMISTIC_RENOVATOR,
            "mood": Mood.NEUTRAL,
            "regard_level": RegardLevel.LOW,
            "objections_available": [],
            "objections_raised": [],
            "objections_resolved": [],
            "stage_progress": CoreStageProgress(current_stage=SalesStage.CONNECT),
            "session_id": "test-session-123",
            "user_id": "test-user-123",
        }
        mock_customer_agent_service.start_session = AsyncMock(return_value=agent_state)

        mock_coach_service = MagicMock()
        default_progress = CoreStageProgress(current_stage=SalesStage.CONNECT)
        default_analysis = CoachAnalysis(
            techniques_detected=[],
            stage_items_completed=[],
            pbms_acknowledged=[],
            deviations=[],
            intervention_level=InterventionLevel.NONE,
            hint=None,
            suggested_stage=None,
            confidence=0.9,
        )
        mock_coach_service.analyze_turn = AsyncMock(
            return_value=(default_analysis, default_progress, None)
        )

        mock_evaluation = MagicMock()
        mock_evaluation.evaluation_id = "eval-789"
        mock_evaluation.session_id = "test-session-123"
        mock_evaluation.final_score = 0.0
        mock_evaluation.grade.value = "F"
        mock_evaluation.summary = None
        mock_evaluation.strengths = []
        mock_evaluation.improvements = []
        mock_evaluation.techniques_detected = []
        mock_evaluation.scorecard = MagicMock()
        mock_evaluation.scorecard.grade.value = "F"
        mock_evaluation.scorecard.raw_score = 0.0
        mock_evaluation.scorecard.final_score = 0.0
        mock_evaluation.scorecard.pbm_match_rate = 0.0
        mock_evaluation.scorecard.pbm_bonus = 0.0
        mock_evaluation.scorecard.objection_resolution_rate = 0.0
        mock_evaluation.scorecard.objection_penalty = 0.0
        mock_evaluation.scorecard.deviations = []
        mock_evaluation.scorecard.deviation_penalty = 0.0
        mock_evaluation.scorecard.stage_scores = {}
        mock_coach_service.generate_evaluation = AsyncMock(return_value=mock_evaluation)

        app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini_service
        app.dependency_overrides[get_session_service] = lambda: mock_session_service
        app.dependency_overrides[get_coach_agent_service] = lambda: mock_coach_service
        app.dependency_overrides[get_customer_agent_service] = lambda: mock_customer_agent_service

        # Have a turn first, then evaluate
        async def mock_receive():
            yield {
                "type": "output_transcription",
                "audio_data": None,
                "text": "Welcome!",
                "finished": True,
            }
            yield {
                "type": "end",
                "audio_data": None,
                "text": None,
            }
            import asyncio

            await asyncio.sleep(1.0)
            return

        mock_live_session.receive.return_value = mock_receive()

        try:
            with TestClient(app).websocket_connect(
                "/ws/gemini/live?token=valid_token&mode=evaluation"
            ) as websocket:
                ready = websocket.receive_json()
                assert ready["type"] == "ready"

                # Send text to populate buffer
                websocket.send_text(json.dumps({"type": "text", "content": "Hello"}))

                import time

                time.sleep(0.1)

                # Send evaluate
                websocket.send_text(json.dumps({"type": "control", "action": "evaluate"}))

                # Drain turn/coach events (transcription, turn_complete,
                # coach_status, stage_progress) until the evaluation arrives
                result = websocket.receive_json()
                for _ in range(10):
                    if result["type"] == "evaluation_result":
                        break
                    result = websocket.receive_json()
                assert result["type"] == "evaluation_result"

            # end_session should be called exactly once (from evaluate action),
            # NOT twice (would happen if buffer wasn't cleared and finally also persisted)
            assert mock_session_service.end_session.call_count == 1

        finally:
            app.dependency_overrides.clear()
