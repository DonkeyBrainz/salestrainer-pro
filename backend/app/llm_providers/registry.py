"""Registry of live (speech-to-speech) providers.

Mirrors the eval-harness ``PROVIDERS`` registry pattern (evals/run.py). The
WebSocket route resolves a provider name to a constructed ``LLMStreamProvider``
here, gated by ``Settings.live_provider_allowlist``.
"""

from collections.abc import Callable

from app.config import Settings
from app.core.exceptions import InvalidRequestError
from app.llm_providers.gemini_live import GeminiLiveProvider
from app.llm_providers.nova_sonic import NovaSonicProvider
from app.llm_providers.openai_realtime import OpenAIRealtimeProvider
from app.llm_providers.streaming import LLMStreamProvider

# Provider name -> factory taking Settings. New adapters register here.
LIVE_PROVIDERS: dict[str, Callable[[Settings], LLMStreamProvider]] = {
    "gemini": GeminiLiveProvider,
    "openai": OpenAIRealtimeProvider,
    "nova": NovaSonicProvider,
}


def build_live_provider(name: str, settings: Settings) -> LLMStreamProvider:
    """Construct a live provider from the registry.

    Args:
        name: Provider name (must be a registered key).
        settings: Application settings passed to the provider factory.

    Raises:
        InvalidRequestError: If ``name`` is not a registered provider.
    """
    factory = LIVE_PROVIDERS.get(name)
    if factory is None:
        raise InvalidRequestError(
            f"Unknown live provider {name!r}. Available: {sorted(LIVE_PROVIDERS)}"
        )
    return factory(settings)
