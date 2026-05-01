"""Curated customer objections for sales training roleplay.

Objections are categorized by type and difficulty level. The customer agent
selects from these based on persona configuration and conversation context.
"""

from enum import Enum
from typing import TypedDict


class ObjectionCategory(str, Enum):
    """Categories of customer objections."""

    PRICE = "price"  # Budget, cost, financing concerns
    TIMING = "timing"  # Need more time, not ready to decide
    AUTHORITY = "authority"  # Need to consult others
    COMPETITION = "competition"  # Shopping elsewhere, comparing
    TRUST = "trust"  # Brand, quality, or salesperson concerns
    LOGISTICS = "logistics"  # Measurements, delivery, space concerns


class ObjectionEntry(TypedDict):
    """A single objection with metadata."""

    text: str
    category: ObjectionCategory
    difficulty: str  # "soft", "firm", "immovable"
    resolution_hint: str


# =============================================================================
# PRICE OBJECTIONS
# =============================================================================

PRICE_OBJECTIONS: list[ObjectionEntry] = [
    {
        "text": "That's more than I wanted to spend.",
        "category": ObjectionCategory.PRICE,
        "difficulty": "soft",
        "resolution_hint": "Present monthly payment option, focus on value per day",
    },
    {
        "text": "I'm on a tight budget right now.",
        "category": ObjectionCategory.PRICE,
        "difficulty": "firm",
        "resolution_hint": "Acknowledge constraint, show Good tier option, mention financing",
    },
    {
        "text": "Way over my budget.",
        "category": ObjectionCategory.PRICE,
        "difficulty": "firm",
        "resolution_hint": "Ask what budget range works, adjust tier accordingly",
    },
    {
        "text": "I can't afford monthly payments.",
        "category": ObjectionCategory.PRICE,
        "difficulty": "immovable",
        "resolution_hint": "Respect the constraint, offer layaway or future appointment",
    },
    {
        "text": "I don't want to finance anything.",
        "category": ObjectionCategory.PRICE,
        "difficulty": "firm",
        "resolution_hint": "Present cash price option, emphasize total savings",
    },
]

# =============================================================================
# TIMING OBJECTIONS
# =============================================================================

TIMING_OBJECTIONS: list[ObjectionEntry] = [
    {
        "text": "I need to think about it.",
        "category": ObjectionCategory.TIMING,
        "difficulty": "soft",
        "resolution_hint": "Use Clear the Constraint - what specifically needs thinking?",
    },
    {
        "text": "I'm not ready to make a decision today.",
        "category": ObjectionCategory.TIMING,
        "difficulty": "firm",
        "resolution_hint": "Respect timeline, schedule follow-up, get contact info",
    },
    {
        "text": "Just browsing today.",
        "category": ObjectionCategory.TIMING,
        "difficulty": "firm",
        "resolution_hint": "Offer to be a resource, create favorites list for later",
    },
    {
        "text": "We're still in the looking phase.",
        "category": ObjectionCategory.TIMING,
        "difficulty": "soft",
        "resolution_hint": "Acknowledge, ask what they're looking for to help narrow",
    },
    {
        "text": "I need more time to decide.",
        "category": ObjectionCategory.TIMING,
        "difficulty": "firm",
        "resolution_hint": "Ask what information would help, offer to hold item",
    },
]

# =============================================================================
# AUTHORITY OBJECTIONS
# =============================================================================

AUTHORITY_OBJECTIONS: list[ObjectionEntry] = [
    {
        "text": "I need to talk to my spouse first.",
        "category": ObjectionCategory.AUTHORITY,
        "difficulty": "firm",
        "resolution_hint": "Offer to schedule time when both can come, create favorites",
    },
    {
        "text": "My husband/wife makes these decisions.",
        "category": ObjectionCategory.AUTHORITY,
        "difficulty": "firm",
        "resolution_hint": "Respect dynamic, gather info to share, schedule return visit",
    },
    {
        "text": "I need to run this by my family.",
        "category": ObjectionCategory.AUTHORITY,
        "difficulty": "soft",
        "resolution_hint": "Offer photos, measurements, pricing to take home",
    },
    {
        "text": "Can I bring my partner back to see this?",
        "category": ObjectionCategory.AUTHORITY,
        "difficulty": "soft",
        "resolution_hint": "Absolutely! Schedule specific time, hold the item if possible",
    },
]

# =============================================================================
# COMPETITION OBJECTIONS
# =============================================================================

COMPETITION_OBJECTIONS: list[ObjectionEntry] = [
    {
        "text": "I saw this cheaper at another store.",
        "category": ObjectionCategory.COMPETITION,
        "difficulty": "firm",
        "resolution_hint": "Ask which store, discuss value differences, mention price match",
    },
    {
        "text": "I want to check a few more places first.",
        "category": ObjectionCategory.COMPETITION,
        "difficulty": "firm",
        "resolution_hint": "Respect decision, differentiate value, schedule follow-up",
    },
    {
        "text": "I'm comparing prices online.",
        "category": ObjectionCategory.COMPETITION,
        "difficulty": "firm",
        "resolution_hint": "Acknowledge, highlight in-store benefits (touch, delivery, service)",
    },
    {
        "text": "There's a sale at [competitor] right now.",
        "category": ObjectionCategory.COMPETITION,
        "difficulty": "firm",
        "resolution_hint": "Ask about the offer, compare total value not just price",
    },
]

# =============================================================================
# TRUST OBJECTIONS
# =============================================================================

TRUST_OBJECTIONS: list[ObjectionEntry] = [
    {
        "text": "I'm not sure about the quality.",
        "category": ObjectionCategory.TRUST,
        "difficulty": "soft",
        "resolution_hint": "Show construction details, mention warranty, share brand story",
    },
    {
        "text": "I've heard mixed reviews about this brand.",
        "category": ObjectionCategory.TRUST,
        "difficulty": "firm",
        "resolution_hint": "Acknowledge, share positive experiences, mention protection plan",
    },
    {
        "text": "How long will this really last?",
        "category": ObjectionCategory.TRUST,
        "difficulty": "soft",
        "resolution_hint": "Discuss materials, warranty, protection plan value",
    },
    {
        "text": "I want to speak with a manager.",
        "category": ObjectionCategory.TRUST,
        "difficulty": "firm",
        "resolution_hint": "Gladly introduce manager, this is standard process",
    },
    {
        "text": "I need to see reviews online first.",
        "category": ObjectionCategory.TRUST,
        "difficulty": "soft",
        "resolution_hint": "Encourage research, offer specific model info to look up",
    },
]

# =============================================================================
# LOGISTICS OBJECTIONS
# =============================================================================

LOGISTICS_OBJECTIONS: list[ObjectionEntry] = [
    {
        "text": "I need to measure my space first.",
        "category": ObjectionCategory.LOGISTICS,
        "difficulty": "soft",
        "resolution_hint": "Provide exact dimensions, offer to hold, schedule follow-up",
    },
    {
        "text": "I'm not sure it will fit.",
        "category": ObjectionCategory.LOGISTICS,
        "difficulty": "soft",
        "resolution_hint": "Review dimensions together, discuss delivery team assessment",
    },
    {
        "text": "When can you deliver?",
        "category": ObjectionCategory.LOGISTICS,
        "difficulty": "soft",
        "resolution_hint": "Check availability, discuss white glove service benefits",
    },
    {
        "text": "I'm moving soon and don't know my new address.",
        "category": ObjectionCategory.LOGISTICS,
        "difficulty": "firm",
        "resolution_hint": "Discuss storage options, delayed delivery, or future order",
    },
    {
        "text": "Will this fit through my door?",
        "category": ObjectionCategory.LOGISTICS,
        "difficulty": "soft",
        "resolution_hint": "Check dimensions, discuss delivery team experience",
    },
]

# =============================================================================
# ALL OBJECTIONS REGISTRY
# =============================================================================

ALL_OBJECTIONS: list[ObjectionEntry] = (
    PRICE_OBJECTIONS
    + TIMING_OBJECTIONS
    + AUTHORITY_OBJECTIONS
    + COMPETITION_OBJECTIONS
    + TRUST_OBJECTIONS
    + LOGISTICS_OBJECTIONS
)

OBJECTIONS_BY_CATEGORY: dict[ObjectionCategory, list[ObjectionEntry]] = {
    ObjectionCategory.PRICE: PRICE_OBJECTIONS,
    ObjectionCategory.TIMING: TIMING_OBJECTIONS,
    ObjectionCategory.AUTHORITY: AUTHORITY_OBJECTIONS,
    ObjectionCategory.COMPETITION: COMPETITION_OBJECTIONS,
    ObjectionCategory.TRUST: TRUST_OBJECTIONS,
    ObjectionCategory.LOGISTICS: LOGISTICS_OBJECTIONS,
}


def get_objections_by_category(category: ObjectionCategory) -> list[ObjectionEntry]:
    """Get all objections in a category.

    Args:
        category: The objection category to filter by.

    Returns:
        List of objections in that category.
    """
    return OBJECTIONS_BY_CATEGORY.get(category, [])


def get_objections_by_difficulty(difficulty: str) -> list[ObjectionEntry]:
    """Get all objections at a specific difficulty level.

    Args:
        difficulty: The difficulty level ("soft", "firm", "immovable").

    Returns:
        List of objections matching the difficulty.
    """
    return [obj for obj in ALL_OBJECTIONS if obj["difficulty"] == difficulty]


def get_objection_texts() -> list[str]:
    """Get just the text of all objections for quick lookup.

    Returns:
        List of objection text strings.
    """
    return [obj["text"] for obj in ALL_OBJECTIONS]
