"""Provider-agnostic voice resolution for customer personas.

Each persona carries a ``voices`` dict keyed by live-provider name
(``{"gemini": "puck", "openai": "cedar", "nova": "matthew"}``). ``resolve_voice``
picks the persona's voice for a given provider, falling back to a per-provider
default when the persona has no explicit cast for that provider.
"""

from app.agents.state import CustomerPersona

# Fallback voice per provider, used when a persona has no explicit cast.
# Verify voice IDs against current provider docs when adding a provider.
DEFAULT_VOICES: dict[str, str] = {
    "gemini": "aoede",
    "openai": "marin",
    "nova": "matthew",
}


def resolve_voice(persona: CustomerPersona, provider: str) -> str:
    """Return the persona's voice ID for ``provider``.

    Args:
        persona: The customer persona whose voice is being resolved.
        provider: Live-provider name (e.g. "gemini", "openai", "nova").

    Returns:
        The persona's mapped voice for the provider, or the provider default
        if the persona has no explicit cast for it.

    Raises:
        KeyError: If ``provider`` is unknown (no default configured). This is a
            programming error — the live-provider registry gates provider names
            before any session is opened.
    """
    voice = persona.voices.get(provider)
    if voice:
        return voice
    return DEFAULT_VOICES[provider]
