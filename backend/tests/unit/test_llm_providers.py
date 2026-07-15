"""Unit tests for the Gemini LLMProvider implementation."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import types
from pydantic import BaseModel

from app.llm_providers import ChatMessage, ChatRole, GeminiProvider


class _Schema(BaseModel):
    """Minimal response schema for structured-output tests."""

    answer: str = ""


@pytest.fixture
def settings() -> MagicMock:
    """Settings stub with the fields the provider reads."""
    stub = MagicMock()
    stub.gemini_api_key = "test-key"
    stub.gemini_model = "gemini-2.5-flash"
    return stub


def _response(
    *,
    finish_reason: types.FinishReason = types.FinishReason.STOP,
    parsed: BaseModel | None = None,
    thoughts: int = 0,
    emitted: int = 10,
) -> MagicMock:
    """Build a stub GenerateContentResponse."""
    response = MagicMock()
    response.text = "{}"
    response.parsed = parsed
    response.candidates = [MagicMock(finish_reason=finish_reason)]
    response.usage_metadata = MagicMock(
        prompt_token_count=5,
        candidates_token_count=emitted,
        total_token_count=5 + emitted + thoughts,
        thoughts_token_count=thoughts,
    )
    return response


def _provider_with(settings: MagicMock, response: MagicMock) -> tuple[GeminiProvider, MagicMock]:
    """Wire a provider to a stubbed generate_content returning ``response``."""
    provider = GeminiProvider(settings)
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=response)
    provider._client = client
    return provider, client


class TestThinkingBudget:
    """Tests for thinking_budget plumbing into GenerateContentConfig."""

    @pytest.mark.asyncio
    async def test_thinking_budget_forwarded(self, settings: MagicMock) -> None:
        """Should translate thinking_budget into a ThinkingConfig."""
        provider, client = _provider_with(settings, _response())

        await provider.complete(
            [ChatMessage(ChatRole.USER, "hi")],
            thinking_budget=0,
        )

        config = client.aio.models.generate_content.call_args.kwargs["config"]
        assert config.thinking_config.thinking_budget == 0

    @pytest.mark.asyncio
    async def test_thinking_budget_omitted_when_none(self, settings: MagicMock) -> None:
        """Should leave the provider default alone when unset."""
        provider, client = _provider_with(settings, _response())

        await provider.complete([ChatMessage(ChatRole.USER, "hi")])

        config = client.aio.models.generate_content.call_args.kwargs["config"]
        assert config.thinking_config is None

    @pytest.mark.asyncio
    async def test_thinking_budget_forwarded_for_structured(self, settings: MagicMock) -> None:
        """Should forward thinking_budget on the structured path too."""
        provider, client = _provider_with(settings, _response(parsed=_Schema()))

        await provider.complete_structured(
            [ChatMessage(ChatRole.USER, "hi")],
            response_schema=_Schema,
            thinking_budget=0,
        )

        config = client.aio.models.generate_content.call_args.kwargs["config"]
        assert config.thinking_config.thinking_budget == 0


class TestTruncationWarning:
    """Tests for surfacing MAX_TOKENS truncation.

    A reasoning model that spends its whole output budget thinking returns
    HTTP 200 with no content, which callers see only as parsed=None. These
    tests pin the log that names that cause.
    """

    @pytest.mark.asyncio
    async def test_warns_when_thinking_exhausts_budget(
        self, settings: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should warn when the response was truncated at max_output_tokens."""
        provider, _ = _provider_with(
            settings,
            _response(finish_reason=types.FinishReason.MAX_TOKENS, thoughts=982, emitted=0),
        )

        with caplog.at_level(logging.WARNING, logger="app.llm_providers.gemini"):
            result = await provider.complete_structured(
                [ChatMessage(ChatRole.USER, "hi")],
                response_schema=_Schema,
                max_output_tokens=1024,
            )

        assert result.parsed is None
        assert "max_output_tokens" in caplog.text
        assert "thinking_tokens=982" in caplog.text

    @pytest.mark.asyncio
    async def test_no_warning_on_normal_completion(
        self, settings: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should stay quiet when the model finished normally."""
        provider, _ = _provider_with(settings, _response(parsed=_Schema()))

        with caplog.at_level(logging.WARNING, logger="app.llm_providers.gemini"):
            await provider.complete_structured(
                [ChatMessage(ChatRole.USER, "hi")],
                response_schema=_Schema,
            )

        assert caplog.text == ""

    @pytest.mark.asyncio
    async def test_handles_response_without_candidates(self, settings: MagicMock) -> None:
        """Should not raise when the response carries no candidates."""
        response = _response()
        response.candidates = []

        provider, _ = _provider_with(settings, response)

        result = await provider.complete([ChatMessage(ChatRole.USER, "hi")])

        assert result.parsed is None


class TestStructuredSchemaValidation:
    """Tests for response_schema type enforcement."""

    @pytest.mark.asyncio
    async def test_rejects_non_basemodel_schema(self, settings: MagicMock) -> None:
        """Should reject a schema that is not a Pydantic model."""
        provider, _ = _provider_with(settings, _response())

        with pytest.raises(TypeError, match="BaseModel"):
            await provider.complete_structured(
                [ChatMessage(ChatRole.USER, "hi")],
                response_schema=dict,  # type: ignore[arg-type]
            )

    @pytest.mark.asyncio
    async def test_parsed_none_when_schema_mismatch(self, settings: MagicMock) -> None:
        """Should drop a parsed value that is not the requested schema."""

        class _Other(BaseModel):
            x: int = 1

        provider, _ = _provider_with(settings, _response(parsed=_Other()))

        result = await provider.complete_structured(
            [ChatMessage(ChatRole.USER, "hi")],
            response_schema=_Schema,
        )

        assert result.parsed is None
