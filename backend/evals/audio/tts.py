"""TTS fixture synthesis for the voice eval suite.

Scripted salesperson turns are synthesized to speech once via Gemini TTS and
cached on disk, so repeated eval runs cost nothing in TTS calls. Output format
is what every ``LiveSession.send_audio`` expects: PCM16 mono @ 16 kHz (the
browser capture rate), with a trailing second of silence so each provider's
server-side VAD detects end-of-utterance.

One fixed "salesperson" voice is used for every turn so the variable under
test is the speech-to-speech model, not the input voice.
"""

import hashlib
import logging
import wave
from pathlib import Path
from typing import Any

from google.genai import types

from app.config import Settings
from app.llm_providers.audio import PcmResampler

logger = logging.getLogger(__name__)

# gemini-2.5-flash-preview-tts outputs PCM16 mono @ 24 kHz.
DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"
SALESPERSON_VOICE = "kore"
TTS_OUTPUT_RATE = 24000
LIVE_INPUT_RATE = 16000
SILENCE_TAIL_MS = 1000

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "audio"


def fixture_path(text: str, voice: str, model: str) -> Path:
    """Deterministic cache path for one synthesized turn."""
    key = f"{model}|{voice}|{LIVE_INPUT_RATE}|{SILENCE_TAIL_MS}|{text}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return FIXTURES_DIR / f"{digest}.pcm"


async def synthesize_turn_audio(
    text: str,
    *,
    settings: Settings,
    client: Any | None = None,
    voice: str = SALESPERSON_VOICE,
    model: str = DEFAULT_TTS_MODEL,
) -> bytes:
    """Return 16 kHz PCM16 mono audio for a scripted turn (cached on disk).

    Args:
        text: The salesperson line to speak.
        settings: App settings (for the Gemini API key).
        client: Optional pre-built ``google.genai.Client`` (injected in tests).
        voice: Prebuilt TTS voice name.
        model: Gemini TTS model id.
    """
    path = fixture_path(text, voice, model)
    if path.exists():
        return path.read_bytes()

    if client is None:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)

    logger.info("Synthesizing TTS fixture: %r (voice=%s)", text[:60], voice)
    response = await client.aio.models.generate_content(
        model=model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )

    pcm_24k = _extract_pcm(response)
    if not pcm_24k:
        raise RuntimeError(f"Gemini TTS returned no audio for: {text!r}")

    pcm_16k = PcmResampler(TTS_OUTPUT_RATE, LIVE_INPUT_RATE).process(pcm_24k)
    silence = b"\x00\x00" * (LIVE_INPUT_RATE * SILENCE_TAIL_MS // 1000)
    audio = pcm_16k + silence

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    return audio


def _extract_pcm(response: Any) -> bytes:
    """Concatenate inline audio bytes from a generate_content TTS response."""
    pcm = b""
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            data = getattr(inline, "data", None)
            if isinstance(data, bytes):
                pcm += data
    return pcm


def write_wav(path: Path, pcm: bytes, sample_rate: int) -> None:
    """Write PCM16 mono bytes as a WAV file (for saved eval audio artifacts)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
