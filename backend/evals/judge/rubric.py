"""Rubric dimension definitions for the LLM judge.

Each dimension is scored independently on a 1-5 scale (per eval-decomposition
guidance: no single blended "vibes" score). Anchor text for 1 and 5 is
embedded in the judge prompt to reduce judge drift.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RubricDimension:
    """One independently-scored quality dimension."""

    name: str
    description: str
    anchor_low: str  # what a 1 looks like
    anchor_high: str  # what a 5 looks like


CUSTOMER_DIMENSIONS: tuple[RubricDimension, ...] = (
    RubricDimension(
        name="persona_consistency",
        description="Responses match the persona's backstory, budget, timeline, and motivators.",
        anchor_low="Contradicts persona facts (wrong budget, invented family, changed goals).",
        anchor_high="Every detail consistent with the persona sheet; motivators surface naturally.",
    ),
    RubricDimension(
        name="emotional_realism",
        description="Tone matches the customer's current mood state on each turn.",
        anchor_low="Cheerful while frustrated, or flat/unchanged tone despite mood swings.",
        anchor_high="Tone tracks the mood ladder believably turn by turn.",
    ),
    RubricDimension(
        name="conversational_naturalness",
        description="Responses read like a real person talking, not a template.",
        anchor_low="Robotic, repetitive, list-like, or unnaturally formal.",
        anchor_high="Natural varied phrasing, realistic hesitations and colloquialisms.",
    ),
    RubricDimension(
        name="stays_in_character",
        description="Never breaks the fourth wall or leaks meta/coaching language.",
        anchor_low="Mentions being an AI, references the training exercise, or coaches the trainee.",
        anchor_high="Fully in character for the entire conversation.",
    ),
    RubricDimension(
        name="objection_realism",
        description="Raised objections feel organic to the conversation, not bolted on.",
        anchor_low="Objection appears verbatim with no connection to what was said.",
        anchor_high="Objection woven naturally into the response, motivated by context.",
    ),
)

VOICE_DIMENSIONS: tuple[RubricDimension, ...] = (
    RubricDimension(
        name="persona_consistency",
        description="Spoken replies match the persona's backstory, budget, timeline, motivators.",
        anchor_low="Contradicts persona facts (wrong budget, invented family, changed goals).",
        anchor_high="Every detail consistent with the persona sheet; motivators surface naturally.",
    ),
    RubricDimension(
        name="stays_in_character",
        description="Never breaks the fourth wall or leaks meta/assistant language in speech.",
        anchor_low="Mentions being an AI, references the exercise, or sounds like an assistant.",
        anchor_high="Fully in character as the customer for the entire conversation.",
    ),
    RubricDimension(
        name="conversational_naturalness",
        description="Replies sound like real speech: contractions, short clauses, no lists.",
        anchor_low="Written-prose phrasing, enumerations, or robotic template answers.",
        anchor_high="Natural spoken cadence with varied, colloquial phrasing.",
    ),
    RubricDimension(
        name="comprehension_grounding",
        description="Replies engage with what was actually said (per '[model heard:]' lines).",
        anchor_low="Ignores or contradicts the salesperson's spoken content; answers off-topic.",
        anchor_high="Directly and accurately builds on the salesperson's specifics (numbers, names).",
    ),
)

COACH_DIMENSIONS: tuple[RubricDimension, ...] = (
    RubricDimension(
        name="hint_actionability",
        description="Hints and example phrases are concrete and immediately usable.",
        anchor_low="Generic advice ('build rapport') with no usable phrasing.",
        anchor_high="Specific, situational guidance with a word-for-word example phrase.",
    ),
    RubricDimension(
        name="technique_detection_precision",
        description="Detected techniques actually occurred in the salesperson message.",
        anchor_low="Credits techniques that plainly did not happen (false positives).",
        anchor_high="Every detected technique is clearly evidenced in the message.",
    ),
    RubricDimension(
        name="coaching_accuracy",
        description="The hint addresses what actually happened in the transcript.",
        anchor_low="Hint about an issue that didn't occur, or misses the obvious problem.",
        anchor_high="Hint targets the most important real issue in the turn.",
    ),
)
