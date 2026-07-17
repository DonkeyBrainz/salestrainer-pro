"""Gemini implementation of the LLMProvider interface.

Wraps ``google.genai.Client`` (the same SDK used by GeminiService) so all
turn-based call sites share one client-construction and usage-mapping path.
"""

import logging
import time
from typing import Any

from google import genai
from google.genai import types
from langfuse import get_client
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.llm_providers.base import ChatMessage, ChatRole, CompletionResult

logger = logging.getLogger(__name__)


class GeminiProvider:
    """LLMProvider implementation backed by the Gemini API."""

    name = "gemini"

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the provider.

        Args:
            settings: Application settings. Defaults to the cached instance.
        """
        self._settings = settings or get_settings()
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        """Get or create the Gemini client."""
        if self._client is None:
            self._client = genai.Client(api_key=self._settings.gemini_api_key)
        return self._client

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        thinking_budget: int | None = None,
    ) -> CompletionResult:
        """Generate a free-text completion for the given messages."""
        return await self._generate(
            messages,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            thinking_budget=thinking_budget,
        )

    async def complete_structured(
        self,
        messages: list[ChatMessage],
        *,
        response_schema: type[BaseModel],
        model: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        thinking_budget: int | None = None,
    ) -> CompletionResult:
        """Generate a schema-constrained JSON completion."""
        if not (isinstance(response_schema, type) and issubclass(response_schema, BaseModel)):
            raise TypeError(
                f"response_schema must be a Pydantic v2 BaseModel subclass, got {response_schema!r}"
            )
        return await self._generate(
            messages,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            thinking_budget=thinking_budget,
            response_schema=response_schema,
        )

    async def _generate(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None,
        temperature: float | None,
        max_output_tokens: int | None,
        thinking_budget: int | None = None,
        response_schema: type[BaseModel] | None = None,
    ) -> CompletionResult:
        """Shared generate_content path for both completion modes."""
        resolved_model = model or self._settings.gemini_model
        system_instruction, contents = self._convert_messages(messages)

        config_kwargs: dict[str, Any] = {}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if temperature is not None:
            config_kwargs["temperature"] = temperature
        if max_output_tokens is not None:
            config_kwargs["max_output_tokens"] = max_output_tokens
        if thinking_budget is not None:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        observation_name = (
            f"gemini.complete_structured:{response_schema.__name__}"
            if response_schema is not None
            else "gemini.complete"
        )
        langfuse = get_client()
        with langfuse.start_as_current_observation(
            as_type="generation",
            name=observation_name,
            model=resolved_model,
            input=[{"role": msg.role.value, "content": msg.content} for msg in messages],
            model_parameters={
                k: v
                for k, v in {
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                    "thinking_budget": thinking_budget,
                }.items()
                if v is not None
            },
        ) as generation:
            started = time.monotonic()
            response = await self.client.aio.models.generate_content(
                model=resolved_model,
                contents=contents,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            latency_ms = (time.monotonic() - started) * 1000

            self._warn_if_truncated(response, resolved_model, max_output_tokens)

            parsed: BaseModel | None = None
            if response_schema is not None:
                candidate = response.parsed
                if isinstance(candidate, response_schema):
                    parsed = candidate

            usage = self._extract_usage(response)
            generation.update(
                output=response.text or "",
                usage_details=(
                    {
                        "input": usage["prompt_tokens"],
                        "output": usage["completion_tokens"],
                        "total": usage["total_tokens"],
                    }
                    if usage is not None
                    else None
                ),
            )

        return CompletionResult(
            text=response.text or "",
            parsed=parsed,
            raw=response,
            model=resolved_model,
            latency_ms=latency_ms,
            usage=usage,
        )

    @staticmethod
    def _warn_if_truncated(
        response: types.GenerateContentResponse,
        model: str,
        max_output_tokens: int | None,
    ) -> None:
        """Log when the model hit the output cap before emitting an answer.

        A reasoning model spends thinking tokens out of max_output_tokens before
        any visible text, so an under-budgeted call returns HTTP 200 with a
        MAX_TOKENS candidate and no content — which callers see only as an empty
        or unparseable result. Naming it here keeps that failure from being
        silently swallowed as "the model had nothing to say".
        """
        candidates = response.candidates or []
        if not candidates:
            return
        if candidates[0].finish_reason != types.FinishReason.MAX_TOKENS:
            return

        usage = response.usage_metadata
        thoughts = getattr(usage, "thoughts_token_count", None) or 0
        emitted = getattr(usage, "candidates_token_count", None) or 0
        logger.warning(
            "Gemini hit max_output_tokens before completing its response "
            "(model=%s, max_output_tokens=%s, thinking_tokens=%s, output_tokens=%s). "
            "Raise max_output_tokens or pass thinking_budget=0.",
            model,
            max_output_tokens,
            thoughts,
            emitted,
        )

    @staticmethod
    def _convert_messages(
        messages: list[ChatMessage],
    ) -> tuple[str | None, list[types.Content] | str]:
        """Convert provider-agnostic messages to Gemini contents.

        System messages are joined into a single system_instruction; user and
        assistant messages become "user"/"model" Content turns. A single user
        message with no system text is passed as a plain string (matching how
        the coach analyzer historically called the SDK).
        """
        system_parts: list[str] = []
        turns: list[types.Content] = []
        for msg in messages:
            if msg.role == ChatRole.SYSTEM:
                system_parts.append(msg.content)
            else:
                role = "user" if msg.role == ChatRole.USER else "model"
                turns.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))

        system_instruction = "\n\n".join(system_parts) if system_parts else None

        if not system_parts and len(turns) == 1 and turns[0].role == "user":
            return None, messages[-1].content
        return system_instruction, turns

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, int] | None:
        """Map Gemini usage_metadata to strict vendor-agnostic keys."""
        usage_metadata = getattr(response, "usage_metadata", None)
        if usage_metadata is None:
            return None
        prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
        total_tokens = getattr(usage_metadata, "total_token_count", 0) or 0
        return {
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(total_tokens),
        }
