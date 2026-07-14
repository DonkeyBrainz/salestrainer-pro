"""Mistral Voxtral implementation of the LLMProvider interface (turn-based, eval harness).

Voxtral Small 24B accepts SPEECH and TEXT input; this provider only exercises
its TEXT path via Bedrock's Converse API (via ``BedrockTextProvider``), same
as Nova. Audio-input evaluation is out of scope for the turn-based harness.
"""

from app.config import Settings, get_settings
from app.llm_providers.bedrock_text import BedrockTextProvider


class VoxtralProvider(BedrockTextProvider):
    """LLMProvider implementation backed by Mistral Voxtral (Bedrock Converse API)."""

    name = "voxtral"

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        super().__init__(
            settings,
            default_model=settings.voxtral_model,
            default_temperature=settings.voxtral_temperature,
        )
