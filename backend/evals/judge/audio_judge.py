"""Audio-level LLM judge: scores the model's actual spoken audio, not the words.

Sends the saved per-turn WAV artifacts to multimodal Gemini (audio input) with
the persona sheet and an audio-specific rubric. This is the layer that hears
prosody, pacing, and tone — everything the transcript judge cannot see.
Opt-in via ``--audio-judge`` (extra cost: audio input tokens on the judge).
"""

import logging
from pathlib import Path
from typing import Any

from google.genai import types

from app.agents.state import CustomerPersona
from app.config import Settings
from evals.judge.judge import JudgeVerdict
from evals.judge.rubric import RubricDimension
from evals.report.models import JudgeDimensionScore, ScenarioResult

logger = logging.getLogger(__name__)

AUDIO_JUDGE_MODEL = "gemini-2.5-flash"

AUDIO_DIMENSIONS: tuple[RubricDimension, ...] = (
    RubricDimension(
        name="vocal_naturalness",
        description="The voice sounds like a real person: prosody, intonation, no artifacts.",
        anchor_low="Flat, robotic, glitchy, or obviously synthetic delivery.",
        anchor_high="Indistinguishable from a natural human speaker.",
    ),
    RubricDimension(
        name="tone_matches_persona",
        description="Vocal tone and energy fit the persona's temperament and situation.",
        anchor_low="Tone contradicts the persona (chipper for a gruff skeptic, flat for anxious).",
        anchor_high="Tone embodies the persona's temperament convincingly.",
    ),
    RubricDimension(
        name="speech_clarity",
        description="Words are clearly articulated and intelligible throughout.",
        anchor_low="Mumbled, clipped, distorted, or partially unintelligible.",
        anchor_high="Every word clear at normal listening volume.",
    ),
    RubricDimension(
        name="pacing",
        description="Speaking rate and pauses feel conversational.",
        anchor_low="Rushed, dragging, or unnatural pauses mid-phrase.",
        anchor_high="Comfortable conversational rhythm with natural pauses.",
    ),
)


def _rubric_text(dimensions: tuple[RubricDimension, ...]) -> str:
    return "\n".join(
        f"- {d.name}: {d.description}\n  1 = {d.anchor_low}\n  5 = {d.anchor_high}"
        for d in dimensions
    )


async def judge_scenario_audio(
    result: ScenarioResult,
    persona: CustomerPersona,
    settings: Settings,
    *,
    client: Any | None = None,
    judge_model: str = AUDIO_JUDGE_MODEL,
) -> list[JudgeDimensionScore] | None:
    """Score a scenario's saved output audio against the audio rubric.

    Returns None (never raises) if there is no audio or the judge call fails —
    audio-judge scores are a soft signal, like the transcript judge.
    """
    wav_parts: list[types.Part] = []
    for turn in result.voice_turns:
        if turn.audio_path and Path(turn.audio_path).exists():
            wav_parts.append(
                types.Part.from_bytes(
                    data=Path(turn.audio_path).read_bytes(), mime_type="audio/wav"
                )
            )
    if not wav_parts:
        logger.warning(f"Audio judge: no audio artifacts for {result.scenario_id}")
        return None

    prompt = f"""You are an expert evaluator of AI voice agents for sales training.

The attached audio clips are consecutive spoken replies from an AI playing this
customer persona in a live voice roleplay:

PERSONA: {persona.name} — {persona.backstory}
Temperament context: {persona.primary_pbm}

Listen to the audio and score each dimension on a 1-5 integer scale:
{_rubric_text(AUDIO_DIMENSIONS)}

Score all dimensions exactly once each, using the exact dimension names given,
with a one-or-two-sentence rationale citing what you heard."""

    if client is None:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)

    try:
        response = await client.aio.models.generate_content(
            model=judge_model,
            contents=[prompt, *wav_parts],
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=JudgeVerdict,
            ),
        )
    except Exception as e:  # noqa: BLE001 - judge failure must not fail the run
        logger.warning(f"Audio judge call failed for {result.scenario_id}: {e}")
        return None

    parsed = getattr(response, "parsed", None)
    if not isinstance(parsed, JudgeVerdict):
        logger.warning(f"Audio judge produced no structured output for {result.scenario_id}")
        return None

    valid_names = {d.name for d in AUDIO_DIMENSIONS}
    return [
        JudgeDimensionScore(dimension=s.dimension, score=s.score, rationale=s.rationale)
        for s in parsed.dimension_scores
        if s.dimension in valid_names
    ]
