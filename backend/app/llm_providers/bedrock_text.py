"""Shared LLMProvider base for Bedrock text models reachable via Converse API.

Amazon Nova (Lite/Pro/Micro) and Mistral's Voxtral/Ministral/Mistral-Large
family are all invoked identically through Bedrock's Converse API — only the
``model_id`` and default sampling config differ. Concrete providers
(``NovaProvider``, ``VoxtralProvider``) are thin subclasses that just supply
those defaults; this class owns all the Converse plumbing.

Speech-only models (Nova Sonic) use a completely different bidirectional
stream API and are NOT served by this class — see ``nova_sonic.py``.
"""

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from app.config import Settings, get_settings
from app.core.exceptions import InvalidRequestError, ServiceUnavailableError
from app.llm_providers.aws_credentials import bootstrap_aws_env_credentials
from app.llm_providers.base import ChatMessage, ChatRole, CompletionResult

if TYPE_CHECKING:
    from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient

logger = logging.getLogger(__name__)


class BedrockTextProvider:
    """LLMProvider base for any Bedrock Converse-compatible text model."""

    name = "bedrock"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        default_model: str,
        default_temperature: float,
    ) -> None:
        self._settings = settings or get_settings()
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._client: BedrockRuntimeClient | None = None

    @property
    def client(self) -> "BedrockRuntimeClient":
        """Get or create the Bedrock runtime client (lazy: needs the optional SDK)."""
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _build_client(self) -> "BedrockRuntimeClient":
        try:
            from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient
            from aws_sdk_bedrock_runtime.config import Config
            from smithy_aws_core.identity import EnvironmentCredentialsResolver
        except ImportError as e:
            raise InvalidRequestError("Bedrock support requires: uv sync --extra nova") from e

        # The Smithy SDK only resolves credentials from the environment; load
        # them from boto3's full chain (~/.aws, IAM role) first.
        bootstrap_aws_env_credentials()

        config = Config(
            region=self._settings.aws_region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        return BedrockRuntimeClient(config=config)

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        thinking_budget: int | None = None,
    ) -> CompletionResult:
        """Generate a free-text completion for the given messages.

        ``thinking_budget`` is accepted for interface parity and ignored: the
        Converse models used here have no configurable thinking mode.
        """
        return await self._converse(
            messages,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
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
        """Generate a JSON completion matching ``response_schema``.

        Bedrock's Converse API has no Gemini-style ``response_schema`` mode,
        so this appends a schema + "JSON only" instruction to the prompt and
        parses the result. Less reliable than Gemini's native structured
        output — acceptable for eval-harness comparison, not production use.

        ``thinking_budget`` is accepted for interface parity and ignored: the
        Converse models used here have no configurable thinking mode.
        """
        if not (isinstance(response_schema, type) and issubclass(response_schema, BaseModel)):
            raise TypeError(
                f"response_schema must be a Pydantic v2 BaseModel subclass, got {response_schema!r}"
            )

        schema_json = json.dumps(response_schema.model_json_schema())
        instruction = ChatMessage(
            ChatRole.SYSTEM,
            "Respond with ONLY valid JSON matching this schema, no prose, no "
            f"markdown fences:\n{schema_json}",
        )
        result = await self._converse(
            [instruction, *messages],
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        parsed: BaseModel | None = None
        try:
            text = (
                result.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            )
            parsed = response_schema.model_validate_json(text)
        except Exception as e:  # noqa: BLE001 - malformed output is a valid eval outcome
            logger.warning(f"{self.name} structured output failed to parse: {e}")

        return CompletionResult(
            text=result.text,
            parsed=parsed,
            raw=result.raw,
            model=result.model,
            latency_ms=result.latency_ms,
            usage=result.usage,
        )

    async def _converse(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None,
        temperature: float | None,
        max_output_tokens: int | None,
    ) -> CompletionResult:
        from aws_sdk_bedrock_runtime.models import (
            ContentBlockText,
            ConverseInput,
            InferenceConfiguration,
        )

        resolved_model = model or self._default_model
        system_blocks, turns = self._convert_messages(messages)

        inference_config = InferenceConfiguration(
            temperature=temperature if temperature is not None else self._default_temperature,
            max_tokens=max_output_tokens or 1024,
        )

        started = time.monotonic()
        try:
            response = await self.client.converse(
                ConverseInput(
                    model_id=resolved_model,
                    messages=turns,
                    system=system_blocks or None,
                    inference_config=inference_config,
                )
            )
        except InvalidRequestError:
            raise
        except Exception as e:
            raise ServiceUnavailableError(f"{self.name} API error: {e}") from e
        latency_ms = (time.monotonic() - started) * 1000

        output_text = ""
        message = response.output.value
        for block in message.content:
            if isinstance(block, ContentBlockText):
                output_text += block.value

        return CompletionResult(
            text=output_text,
            parsed=None,
            raw=response,
            model=resolved_model,
            latency_ms=latency_ms,
            usage=self._extract_usage(response),
        )

    @staticmethod
    def _convert_messages(
        messages: list[ChatMessage],
    ) -> tuple[list[Any], list[Any]]:
        """Split provider-agnostic messages into Bedrock system blocks + turns.

        Bedrock Converse requires the first/last turn to be "user" and roles
        to strictly alternate; system messages are pulled out into the
        dedicated ``system`` field (matching GeminiProvider's convention).
        """
        from aws_sdk_bedrock_runtime.models import (
            ContentBlockText,
            ConversationRole,
            Message,
            SystemContentBlockText,
        )

        system_blocks: list[Any] = []
        turns: list[Any] = []
        for msg in messages:
            if msg.role == ChatRole.SYSTEM:
                system_blocks.append(SystemContentBlockText(msg.content))
            else:
                role = (
                    ConversationRole.USER
                    if msg.role == ChatRole.USER
                    else ConversationRole.ASSISTANT
                )
                turns.append(Message(role=role, content=[ContentBlockText(msg.content)]))
        return system_blocks, turns

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, int] | None:
        """Map Bedrock's TokenUsage to strict vendor-agnostic keys."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return None
        return {
            "prompt_tokens": int(usage.input_tokens or 0),
            "completion_tokens": int(usage.output_tokens or 0),
            "total_tokens": int(usage.total_tokens or 0),
        }
