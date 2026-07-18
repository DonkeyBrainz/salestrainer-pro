"""Tests for GeminiLiveSession wrapper class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import InternalError
from app.services.gemini_service import GeminiLiveSession


@pytest.fixture
def mock_session():
    """Create mock AsyncSession from genai SDK."""
    session = MagicMock()
    session.send_realtime_input = AsyncMock()
    session.send_client_content = AsyncMock()
    session.receive = MagicMock()
    return session


@pytest.fixture
def live_session(mock_session):
    """Create GeminiLiveSession with mocked underlying session."""
    return GeminiLiveSession(mock_session)


class TestSendAudio:
    """Tests for send_audio method."""

    async def test_sends_audio_successfully(self, live_session, mock_session):
        """Should send audio data to Gemini."""
        audio_data = b"test audio bytes"

        await live_session.send_audio(audio_data)

        mock_session.send_realtime_input.assert_called_once_with(
            audio={"data": audio_data, "mime_type": "audio/pcm"}
        )

    async def test_sends_audio_with_custom_mime_type(self, live_session, mock_session):
        """Should support custom MIME type for audio."""
        audio_data = b"test audio bytes"

        await live_session.send_audio(audio_data, mime_type="audio/wav")

        mock_session.send_realtime_input.assert_called_once_with(
            audio={"data": audio_data, "mime_type": "audio/wav"}
        )

    async def test_raises_error_when_closed(self, live_session):
        """Should raise InternalError if session is closed."""
        await live_session.close()

        with pytest.raises(InternalError, match="Cannot send to closed Live session"):
            await live_session.send_audio(b"test")

    async def test_raises_error_on_send_failure(self, live_session, mock_session):
        """Should wrap send_realtime_input errors in InternalError."""
        mock_session.send_realtime_input.side_effect = Exception("SDK error")

        with pytest.raises(InternalError, match="Failed to send audio"):
            await live_session.send_audio(b"test")


class TestSendText:
    """Tests for send_text method."""

    async def test_sends_text_successfully(self, live_session, mock_session):
        """Should send text message to Gemini."""
        text = "Hello, Gemini"

        await live_session.send_text(text)

        mock_session.send_client_content.assert_called_once_with(
            turns=[{"role": "user", "parts": [{"text": text}]}],
            turn_complete=True,
        )

    async def test_raises_error_when_closed(self, live_session):
        """Should raise InternalError if session is closed."""
        await live_session.close()

        with pytest.raises(InternalError, match="Cannot send to closed Live session"):
            await live_session.send_text("test")

    async def test_raises_error_on_send_failure(self, live_session, mock_session):
        """Should wrap send_client_content errors in InternalError."""
        mock_session.send_client_content.side_effect = Exception("SDK error")

        with pytest.raises(InternalError, match="Failed to send text"):
            await live_session.send_text("test")


class TestReceive:
    """Tests for receive method."""

    async def test_receives_audio_response(self, live_session, mock_session):
        """Should yield audio data from Gemini response."""
        # Mock response with audio data
        mock_part = MagicMock()
        mock_part.inline_data.data = b"audio response bytes"

        mock_response = MagicMock()
        mock_response.server_content.model_turn.parts = [mock_part]
        # Disable transcription fields for this test
        mock_response.server_content.input_transcription = None
        mock_response.server_content.output_transcription = None
        mock_response.server_content.interrupted = None
        # Disable session resumption fields for this test
        mock_response.session_resumption_update = None
        mock_response.go_away = None
        # Must set turn_complete=True to break the while loop in receive()
        mock_response.server_content.turn_complete = True

        async def mock_turn_generator():
            yield mock_response

        mock_session.receive.return_value = mock_turn_generator()

        # Collect responses - need to close session after first turn to exit while loop
        responses = []
        async for response in live_session.receive():
            responses.append(response)
            if response["type"] == "end":
                await live_session.close()

        # Audio response + end marker
        assert len(responses) == 2
        assert responses[0]["type"] == "audio"
        assert responses[0]["audio_data"] == b"audio response bytes"
        assert responses[0]["text"] is None
        assert responses[1]["type"] == "end"

    async def test_receives_text_response(self, live_session, mock_session):
        """Should yield internal reasoning text from Gemini response."""
        # Mock response with text (internal reasoning from model_turn)
        mock_part = MagicMock()
        mock_part.text = "This is a text response"
        # Set inline_data to None so the audio check fails
        mock_part.inline_data = None

        mock_response = MagicMock()
        mock_response.server_content.model_turn.parts = [mock_part]
        # Disable transcription fields for this test
        mock_response.server_content.input_transcription = None
        mock_response.server_content.output_transcription = None
        mock_response.server_content.interrupted = None
        # Disable session resumption fields for this test
        mock_response.session_resumption_update = None
        mock_response.go_away = None
        # Must set turn_complete=True to break the while loop in receive()
        mock_response.server_content.turn_complete = True

        async def mock_turn_generator():
            yield mock_response

        mock_session.receive.return_value = mock_turn_generator()

        # Collect responses - need to close session after first turn to exit while loop
        responses = []
        async for response in live_session.receive():
            responses.append(response)
            if response["type"] == "end":
                await live_session.close()

        # Internal reasoning response + end marker
        assert len(responses) == 2
        assert responses[0]["type"] == "internal_reasoning"
        assert responses[0]["text"] == "This is a text response"
        assert responses[0]["audio_data"] is None
        assert responses[1]["type"] == "end"

    async def test_receives_turn_complete(self, live_session, mock_session):
        """Should yield end marker when turn is complete."""
        mock_response = MagicMock()
        mock_response.server_content.model_turn = None
        # Disable transcription fields for this test
        mock_response.server_content.input_transcription = None
        mock_response.server_content.output_transcription = None
        mock_response.server_content.interrupted = None
        # Disable session resumption fields for this test
        mock_response.session_resumption_update = None
        mock_response.go_away = None
        mock_response.server_content.turn_complete = True

        async def mock_turn_generator():
            yield mock_response

        mock_session.receive.return_value = mock_turn_generator()

        # Collect responses - need to close session after first turn to exit while loop
        responses = []
        async for response in live_session.receive():
            responses.append(response)
            if response["type"] == "end":
                await live_session.close()

        assert len(responses) == 1
        assert responses[0]["type"] == "end"
        assert responses[0]["audio_data"] is None
        assert responses[0]["text"] is None

    async def test_receives_interrupted(self, live_session, mock_session):
        """Should yield interrupted marker on barge-in before the turn ends."""
        mock_response = MagicMock()
        mock_response.server_content.model_turn = None
        mock_response.server_content.input_transcription = None
        mock_response.server_content.output_transcription = None
        mock_response.session_resumption_update = None
        mock_response.go_away = None
        mock_response.server_content.interrupted = True
        mock_response.server_content.turn_complete = True

        async def mock_turn_generator():
            yield mock_response

        mock_session.receive.return_value = mock_turn_generator()

        responses = []
        async for response in live_session.receive():
            responses.append(response)
            if response["type"] == "end":
                await live_session.close()

        assert [r["type"] for r in responses] == ["interrupted", "end"]
        assert responses[0]["audio_data"] is None
        assert responses[0]["text"] is None

    async def test_receives_multiple_parts(self, live_session, mock_session):
        """Should yield multiple parts from a single response."""
        # Mock response with both audio and text (internal reasoning)
        audio_part = MagicMock()
        audio_part.inline_data.data = b"audio"

        text_part = MagicMock()
        text_part.text = "text"
        text_part.inline_data = None

        mock_response = MagicMock()
        mock_response.server_content.model_turn.parts = [audio_part, text_part]
        # Disable transcription fields for this test
        mock_response.server_content.input_transcription = None
        mock_response.server_content.output_transcription = None
        mock_response.server_content.interrupted = None
        # Disable session resumption fields for this test
        mock_response.session_resumption_update = None
        mock_response.go_away = None
        mock_response.server_content.turn_complete = True

        async def mock_turn_generator():
            yield mock_response

        mock_session.receive.return_value = mock_turn_generator()

        # Collect responses - need to close session after first turn to exit while loop
        responses = []
        async for response in live_session.receive():
            responses.append(response)
            if response["type"] == "end":
                await live_session.close()

        # Should get audio, internal_reasoning, and end
        assert len(responses) == 3
        assert responses[0]["type"] == "audio"
        assert responses[1]["type"] == "internal_reasoning"
        assert responses[2]["type"] == "end"

    async def test_raises_error_when_closed(self, live_session):
        """Should raise InternalError if session is closed."""
        await live_session.close()

        with pytest.raises(InternalError, match="Cannot receive from closed Live session"):
            async for _ in live_session.receive():
                pass

    async def test_raises_error_on_receive_failure(self, live_session, mock_session):
        """Should wrap receive errors in InternalError."""

        async def failing_generator():
            raise Exception("SDK error")
            yield  # Never reached

        mock_session.receive.return_value = failing_generator()

        with pytest.raises(InternalError, match="Failed to receive from Gemini Live"):
            async for _ in live_session.receive():
                pass


class TestUsageExtraction:
    """Tests for the "usage" LiveEvent emitted from usage_metadata."""

    async def test_receive_yields_usage_event(self, live_session, mock_session):
        """Should translate usage_metadata into a usage event before end."""
        usage = MagicMock()
        usage.prompt_token_count = 100
        usage.response_token_count = 30
        usage.total_token_count = 130
        usage.thoughts_token_count = 12
        modality_detail = MagicMock()
        modality_detail.modality = "AUDIO"
        modality_detail.token_count = 90
        usage.prompt_tokens_details = [modality_detail]
        usage.response_tokens_details = None

        mock_response = MagicMock()
        mock_response.session_resumption_update = None
        mock_response.go_away = None
        mock_response.usage_metadata = usage
        mock_response.server_content.input_transcription = None
        mock_response.server_content.output_transcription = None
        mock_response.server_content.interrupted = None
        mock_response.server_content.model_turn = None
        mock_response.server_content.turn_complete = True

        async def mock_turn_generator():
            yield mock_response

        mock_session.receive.return_value = mock_turn_generator()

        responses = []
        async for response in live_session.receive():
            responses.append(response)
            if response["type"] == "end":
                await live_session.close()

        assert [r["type"] for r in responses] == ["usage", "end"]
        assert responses[0]["usage"] == {
            "prompt_tokens": 100,
            "completion_tokens": 30,
            "total_tokens": 130,
        }
        assert responses[0]["detail"]["prompt_tokens_details"] == [
            {"modality": "AUDIO", "token_count": 90}
        ]
        assert responses[0]["detail"]["thoughts_token_count"] == 12

    def test_extract_returns_none_without_metadata(self):
        """No usage_metadata -> no event."""
        response = MagicMock()
        response.usage_metadata = None
        assert GeminiLiveSession._extract_usage_event(response) is None

    def test_extract_coerces_non_int_garbage_to_none(self):
        """Non-int token counts (e.g. mock/SDK drift) degrade to no event."""
        response = MagicMock()  # every attr is a truthy MagicMock, none are ints
        assert GeminiLiveSession._extract_usage_event(response) is None


class TestClose:
    """Tests for close method."""

    async def test_marks_session_as_closed(self, live_session):
        """Should mark session as closed."""
        await live_session.close()

        assert live_session._closed is True

    async def test_close_is_idempotent(self, live_session):
        """Should allow multiple close calls."""
        await live_session.close()
        await live_session.close()  # Should not raise

        assert live_session._closed is True

    async def test_operations_fail_after_close(self, live_session):
        """Should prevent operations after close."""
        await live_session.close()

        with pytest.raises(InternalError):
            await live_session.send_audio(b"test")

        with pytest.raises(InternalError):
            await live_session.send_text("test")

        with pytest.raises(InternalError):
            async for _ in live_session.receive():
                pass
