"""Tests for GeminiService."""

from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors, types

from app.config import Settings
from app.core.exceptions import (
    InternalError,
    InvalidRequestError,
    RateLimitError,
    ServiceUnavailableError,
)
from app.models.gemini import GeminiRequest
from app.services.gemini_service import GeminiService


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for tests."""
    return Settings(
        gemini_api_key="test-api-key",
        gemini_model="gemini-2.5-flash-preview-04-17",
        gemini_temperature=0.7,
        gemini_max_tokens=1024,
    )


@pytest.fixture
def gemini_service(mock_settings: Settings) -> GeminiService:
    """Create GeminiService with mocked settings."""
    with patch("app.services.gemini_service.genai.Client"):
        return GeminiService(settings=mock_settings)


class TestGenerate:
    """Tests for generate method."""

    async def test_successful_generation(self, gemini_service: GeminiService) -> None:
        """Should generate text successfully and return response."""
        # Mock response
        mock_response = MagicMock()
        mock_response.text = "This is a test response from Gemini."
        mock_response.usage_metadata = types.UsageMetadata(
            prompt_token_count=10,
            response_token_count=15,
            total_token_count=25,
        )

        # Mock the client
        gemini_service.client.models.generate_content = MagicMock(return_value=mock_response)

        # Test request
        request = GeminiRequest(prompt="Tell me a joke")

        # Execute
        result = await gemini_service.generate(request)

        # Verify
        assert result.text == "This is a test response from Gemini."
        assert result.usage.prompt_token_count == 10
        assert result.usage.candidates_token_count == 15
        assert result.usage.total_token_count == 25
        assert result.model_info.model == "gemini-2.5-flash-preview-04-17"
        assert result.model_info.temperature == 0.7
        assert result.model_info.max_tokens == 1024

        # Verify client was called correctly
        gemini_service.client.models.generate_content.assert_called_once()
        call_args = gemini_service.client.models.generate_content.call_args
        assert call_args.kwargs["model"] == "gemini-2.5-flash-preview-04-17"
        assert call_args.kwargs["contents"] == "Tell me a joke"
        assert call_args.kwargs["config"].temperature == 0.7
        assert call_args.kwargs["config"].max_output_tokens == 1024

    async def test_parameter_overrides(self, gemini_service: GeminiService) -> None:
        """Should use request parameters when provided, overriding defaults."""
        # Mock response
        mock_response = MagicMock()
        mock_response.text = "Overridden response"
        mock_response.usage_metadata = types.UsageMetadata(
            prompt_token_count=5,
            response_token_count=10,
            total_token_count=15,
        )

        gemini_service.client.models.generate_content = MagicMock(return_value=mock_response)

        # Request with overrides
        request = GeminiRequest(prompt="Test", temperature=1.2, max_tokens=500)

        # Execute
        result = await gemini_service.generate(request)

        # Verify overrides were used
        assert result.model_info.temperature == 1.2
        assert result.model_info.max_tokens == 500

        call_args = gemini_service.client.models.generate_content.call_args
        assert call_args.kwargs["config"].temperature == 1.2
        assert call_args.kwargs["config"].max_output_tokens == 500

    async def test_missing_usage_metadata(self, gemini_service: GeminiService) -> None:
        """Should handle missing usage metadata gracefully."""
        # Mock response without usage metadata
        mock_response = MagicMock()
        mock_response.text = "Response without metadata"
        mock_response.usage_metadata = None

        gemini_service.client.models.generate_content = MagicMock(return_value=mock_response)

        # Execute
        request = GeminiRequest(prompt="Test")
        result = await gemini_service.generate(request)

        # Verify defaults to 0
        assert result.usage.prompt_token_count == 0
        assert result.usage.candidates_token_count == 0
        assert result.usage.total_token_count == 0

    async def test_empty_response_text(self, gemini_service: GeminiService) -> None:
        """Should raise InternalError if Gemini returns empty text."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.text = ""

        gemini_service.client.models.generate_content = MagicMock(return_value=mock_response)

        # Execute and verify
        request = GeminiRequest(prompt="Test")
        with pytest.raises(InternalError, match="Gemini returned empty response"):
            await gemini_service.generate(request)

    async def test_rate_limit_error(self, gemini_service: GeminiService) -> None:
        """Should raise RateLimitError on 429 from Gemini."""
        # Mock API error
        api_error = errors.APIError(
            code=429, response_json={"error": {"message": "Too many requests"}}
        )
        gemini_service.client.models.generate_content = MagicMock(side_effect=api_error)

        # Execute and verify
        request = GeminiRequest(prompt="Test")
        with pytest.raises(RateLimitError, match="Gemini API rate limit exceeded"):
            await gemini_service.generate(request)

    async def test_invalid_request_error_400(self, gemini_service: GeminiService) -> None:
        """Should raise InvalidRequestError on 400 from Gemini."""
        # Mock API error
        api_error = errors.APIError(
            code=400, response_json={"error": {"message": "Invalid prompt"}}
        )
        gemini_service.client.models.generate_content = MagicMock(side_effect=api_error)

        # Execute and verify
        request = GeminiRequest(prompt="Test prompt")
        with pytest.raises(InvalidRequestError, match="Invalid request to Gemini"):
            await gemini_service.generate(request)

    async def test_permission_denied_error(self, gemini_service: GeminiService) -> None:
        """Should raise InvalidRequestError on 403 from Gemini."""
        # Mock API error
        api_error = errors.APIError(
            code=403, response_json={"error": {"message": "Permission denied"}}
        )
        gemini_service.client.models.generate_content = MagicMock(side_effect=api_error)

        # Execute and verify
        request = GeminiRequest(prompt="Test")
        with pytest.raises(InvalidRequestError, match="Permission denied for Gemini API"):
            await gemini_service.generate(request)

    async def test_model_not_found_error(self, gemini_service: GeminiService) -> None:
        """Should raise InvalidRequestError on 404 from Gemini."""
        # Mock API error
        api_error = errors.APIError(
            code=404, response_json={"error": {"message": "Model not found"}}
        )
        gemini_service.client.models.generate_content = MagicMock(side_effect=api_error)

        # Execute and verify
        request = GeminiRequest(prompt="Test")
        with pytest.raises(InvalidRequestError, match="Model not found"):
            await gemini_service.generate(request)

    async def test_service_unavailable_error(self, gemini_service: GeminiService) -> None:
        """Should raise ServiceUnavailableError on 503 from Gemini."""
        # Mock API error
        api_error = errors.APIError(
            code=503, response_json={"error": {"message": "Service unavailable"}}
        )
        gemini_service.client.models.generate_content = MagicMock(side_effect=api_error)

        # Execute and verify
        request = GeminiRequest(prompt="Test")
        with pytest.raises(ServiceUnavailableError, match="Gemini service temporarily unavailable"):
            await gemini_service.generate(request)

    async def test_unknown_api_error(self, gemini_service: GeminiService) -> None:
        """Should raise InternalError on unknown API error codes."""
        # Mock API error with unknown code
        api_error = errors.APIError(code=999, response_json={"error": {"message": "Unknown error"}})
        gemini_service.client.models.generate_content = MagicMock(side_effect=api_error)

        # Execute and verify
        request = GeminiRequest(prompt="Test")
        with pytest.raises(InternalError, match="Gemini API error"):
            await gemini_service.generate(request)

    async def test_unexpected_exception(self, gemini_service: GeminiService) -> None:
        """Should raise InternalError on unexpected exceptions."""
        # Mock unexpected error
        gemini_service.client.models.generate_content = MagicMock(
            side_effect=ValueError("Unexpected error")
        )

        # Execute and verify
        request = GeminiRequest(prompt="Test")
        with pytest.raises(InternalError, match="Unexpected error calling Gemini"):
            await gemini_service.generate(request)


class TestGenerateStream:
    """Tests for generate_stream method."""

    async def test_successful_streaming(self, gemini_service: GeminiService) -> None:
        """Should stream text chunks successfully."""
        # Mock streaming response
        chunk1 = MagicMock()
        chunk1.text = "Hello "
        chunk2 = MagicMock()
        chunk2.text = "world!"

        async def mock_stream(*args, **kwargs):
            yield chunk1
            yield chunk2

        # Mock the async stream method
        mock_aio = MagicMock()
        mock_aio.models.generate_content_stream = mock_stream
        gemini_service.client.aio = mock_aio

        # Execute
        request = GeminiRequest(prompt="Say hello")
        chunks = []
        async for chunk in gemini_service.generate_stream(request):
            chunks.append(chunk)

        # Verify
        assert len(chunks) == 3  # 2 text chunks + 1 final marker
        assert chunks[0].text == "Hello "
        assert chunks[0].is_final is False
        assert chunks[1].text == "world!"
        assert chunks[1].is_final is False
        assert chunks[2].text == ""
        assert chunks[2].is_final is True

    async def test_stream_with_parameter_overrides(self, gemini_service: GeminiService) -> None:
        """Should use request parameters in streaming."""
        # Mock streaming response
        chunk = MagicMock()
        chunk.text = "Test"

        async def mock_stream(*args, **kwargs):
            # Verify parameters
            assert kwargs["config"].temperature == 1.5
            assert kwargs["config"].max_output_tokens == 200
            yield chunk

        # Mock the async stream method
        mock_aio = MagicMock()
        mock_aio.models.generate_content_stream = mock_stream
        gemini_service.client.aio = mock_aio

        # Execute
        request = GeminiRequest(prompt="Test", temperature=1.5, max_tokens=200)
        chunks = []
        async for chunk in gemini_service.generate_stream(request):
            chunks.append(chunk)

        # Verify we got chunks
        assert len(chunks) == 2  # 1 text chunk + 1 final marker

    async def test_stream_rate_limit_error(self, gemini_service: GeminiService) -> None:
        """Should raise RateLimitError on 429 during streaming."""

        # Mock API error
        async def mock_stream(*args, **kwargs):
            raise errors.APIError(code=429, response_json={"error": {"message": "Rate limited"}})
            yield  # Never reached

        # Mock the async stream method
        mock_aio = MagicMock()
        mock_aio.models.generate_content_stream = mock_stream
        gemini_service.client.aio = mock_aio

        # Execute and verify
        request = GeminiRequest(prompt="Test")
        with pytest.raises(RateLimitError):
            async for chunk in gemini_service.generate_stream(request):
                pass

    async def test_stream_empty_chunks(self, gemini_service: GeminiService) -> None:
        """Should skip chunks with empty text."""
        # Mock streaming response with empty chunks
        chunk1 = MagicMock()
        chunk1.text = ""  # Empty
        chunk2 = MagicMock()
        chunk2.text = "Valid text"
        chunk3 = MagicMock()
        chunk3.text = None  # None

        async def mock_stream(*args, **kwargs):
            yield chunk1
            yield chunk2
            yield chunk3

        # Mock the async stream method
        mock_aio = MagicMock()
        mock_aio.models.generate_content_stream = mock_stream
        gemini_service.client.aio = mock_aio

        # Execute
        request = GeminiRequest(prompt="Test")
        chunks = []
        async for chunk in gemini_service.generate_stream(request):
            chunks.append(chunk)

        # Verify only valid text chunk and final marker
        assert len(chunks) == 2
        assert chunks[0].text == "Valid text"
        assert chunks[1].is_final is True
