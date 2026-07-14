"""Amazon Nova implementation of the LLMProvider interface (turn-based, eval harness).

Uses Bedrock's Converse API via ``BedrockTextProvider`` — the standard
chat-style entrypoint for Nova's text models (Nova Lite/Pro/Micro). Nova Sonic
(``nova_sonic.py``) is a separate, speech-only model reachable only via the
bidirectional stream API; it cannot serve this turn-based interface.
"""

from app.config import Settings, get_settings
from app.llm_providers.bedrock_text import BedrockTextProvider


class NovaProvider(BedrockTextProvider):
    """LLMProvider implementation backed by Amazon Nova (Bedrock Converse API)."""

    name = "nova"

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        super().__init__(
            settings,
            default_model=settings.nova_model,
            default_temperature=settings.nova_temperature,
        )
