"""Provider-agnostic LLM interface.

This module defines the abstraction used by every turn-based (request/response)
LLM call site in the app: the customer agent's response node, the coach
analyzer, and the evaluation feedback generator. Implementations wrap a
specific vendor SDK (see gemini.py) behind two methods: free-text completion
and schema-constrained structured completion.

Streaming/bidirectional-audio sessions (Gemini Live) are deliberately NOT part
of this interface. A future ``LLMStreamProvider`` protocol can be added
alongside this one without touching any ``LLMProvider`` consumer.

``CompletionResult.usage`` follows a strict vendor-agnostic key schema —
``{"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}`` —
so downstream aggregation (eval-harness cost tracking) never parses
provider-native structures.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class ChatRole(str, Enum):
    """Role of a chat message, vendor-agnostic."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class ChatMessage:
    """A single chat message in provider-agnostic form."""

    role: ChatRole
    content: str


@dataclass(frozen=True)
class CompletionResult:
    """Result of an LLM completion call.

    Attributes:
        text: The generated text. For structured calls this is the raw JSON.
        parsed: For structured calls, the validated response-schema instance.
        raw: Provider-native response object, for debugging/eval only.
        model: The model that served the request.
        latency_ms: Wall-clock latency of the provider call.
        usage: Token counts under strict vendor-agnostic keys
            (prompt_tokens/completion_tokens/total_tokens), or None.
    """

    text: str
    parsed: BaseModel | None = None
    raw: Any | None = None
    model: str | None = None
    latency_ms: float | None = None
    usage: dict[str, int] | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Turn-based LLM provider interface.

    Implementations must be safe to share across calls (construct the
    underlying client once, lazily).
    """

    name: str

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

        ``thinking_budget`` is in tokens: 0 disables thinking, -1 lets the
        provider choose, None leaves the provider default. On reasoning models
        thinking tokens are drawn from ``max_output_tokens``, so a caller that
        sets a tight output budget should disable thinking (see
        ``complete_structured``). Providers without a thinking mode ignore it.
        """
        ...

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
        """Generate a schema-constrained JSON completion.

        ``result.parsed`` holds the validated ``response_schema`` instance
        (or None if the provider produced no parseable structured output);
        ``result.text`` holds the raw JSON text.

        On reasoning models thinking tokens count against ``max_output_tokens``
        and are spent *before* any JSON is emitted, so an output budget that
        does not also cover thinking yields a truncated response and
        ``parsed is None``. Either leave headroom for both or pass
        ``thinking_budget=0``.
        """
        ...
