"""State schemas for LangGraph customer agent.

This module defines the state structures used by the customer agent during
sales training roleplay sessions. The customer agent plays a prospective
customer while the salesperson practices the C.O.R.E. selling system.
"""

from enum import Enum
from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class SalesStage(str, Enum):
    """C.O.R.E. selling system stages."""

    CONNECT = "CONNECT"
    OBSERVE = "OBSERVE"
    RECOMMEND = "RECOMMEND"
    EXECUTE = "EXECUTE"
    COMPLETE = "COMPLETE"


class Difficulty(str, Enum):
    """Customer persona difficulty level (based on customer regard)."""

    HIGH_REGARD = "high_regard"
    MEDIUM_REGARD = "medium_regard"
    LOW_REGARD = "low_regard"
    NO_REGARD = "no_regard"


# Difficulty-based behavior tuning configuration
# These values control how personas behave based on their difficulty level
DIFFICULTY_CONFIG: dict[str, dict[str, float | int | str]] = {
    "high_regard": {
        "mood_improve_chance": 1.0,  # Always succeeds
        "mood_worsen_steps": 1,  # Move 1 step
        "mood_decay_chance": 0.0,  # No decay
        "objection_inject_chance": 0.2,  # 20% behavior-responsive
        "objection_priority": "first",  # First available
    },
    "medium_regard": {
        "mood_improve_chance": 0.7,  # 70% chance to improve
        "mood_worsen_steps": 1,  # Move 1 step
        "mood_decay_chance": 0.1,  # 10% decay per turn
        "objection_inject_chance": 0.4,  # 40% (current behavior)
        "objection_priority": "first",  # First available
    },
    "low_regard": {
        "mood_improve_chance": 0.5,  # 50% chance to improve
        "mood_worsen_steps": 2,  # Move 2 steps (more severe)
        "mood_decay_chance": 0.2,  # 20% decay per turn
        "objection_inject_chance": 0.6,  # 60% behavior-responsive
        "objection_priority": "hardest",  # Pick hardest objection
    },
    "no_regard": {
        "mood_improve_chance": 0.3,  # 30% chance to improve (very difficult)
        "mood_worsen_steps": 2,  # Move 2 steps (more severe)
        "mood_decay_chance": 0.3,  # 30% decay per turn (highest)
        "objection_inject_chance": 0.7,  # 70% behavior-responsive
        "objection_priority": "hardest",  # Pick hardest objection
    },
}


class RegardLevel(str, Enum):
    """Customer engagement/regard level."""

    HIGH = "high"
    LOW = "low"
    NO = "no"


class Timeline(str, Enum):
    """Customer purchase timeline."""

    URGENT = "urgent"
    FLEXIBLE = "flexible"
    BROWSING = "browsing"


class ObjectionDifficulty(str, Enum):
    """How firmly the customer holds objections."""

    SOFT = "soft"  # Easily overcome with basic handling
    FIRM = "firm"  # Requires good technique to resolve
    IMMOVABLE = "immovable"  # Very difficult, may not resolve


class Mood(str, Enum):
    """Customer's current emotional state during conversation."""

    INTERESTED = "interested"
    NEUTRAL = "neutral"
    SKEPTICAL = "skeptical"
    FRUSTRATED = "frustrated"
    READY_TO_BUY = "ready_to_buy"


class CustomerPersona(BaseModel):
    """Pre-defined customer archetype for roleplay.

    Personas are single customers (not couples/groups) with distinct
    behavioral traits that affect how they respond during sales interactions.
    """

    id: str = Field(..., description="Unique identifier (e.g., 'busy_parent')")
    name: str = Field(..., description="Customer's first name")
    backstory: str = Field(..., description="Brief background context")
    looking_for: str = Field(..., description="What furniture they're shopping for")
    budget_range: tuple[int, int] = Field(..., description="Min/max budget in dollars")
    timeline: Timeline = Field(..., description="Purchase urgency")

    # Behavioral traits
    difficulty: Difficulty = Field(..., description="Overall difficulty level")
    initial_regard: RegardLevel = Field(..., description="Starting engagement level")

    # Personal Buying Motivators (what the customer cares about)
    primary_pbm: str = Field(..., description="Main buying motivation")
    secondary_pbm: str | None = Field(None, description="Secondary motivation if any")

    # Objections (from curated list)
    objections: list[str] = Field(default_factory=list, description="Potential objections to raise")
    objection_difficulty: ObjectionDifficulty = Field(
        ObjectionDifficulty.SOFT, description="How firmly objections are held"
    )

    # Voice configuration
    voice_name: str = Field(..., description="Gemini voice identifier (e.g., 'leda', 'kore')")
    is_evaluation_only: bool = Field(
        False, description="If True, only available in evaluation mode"
    )

    # Product metadata (for RAG filtering and analytics)
    product_category: str | None = Field(
        None, description="Product category (e.g., 'living_room', 'bedroom', 'mattress')"
    )
    product_type: str | None = Field(
        None, description="Specific product type (e.g., 'sectional', 'bedroom_set')"
    )
    product_keywords: list[str] = Field(
        default_factory=list,
        description="Product-related keywords (e.g., ['durability', 'family-friendly'])",
    )

    model_config = {"frozen": True}


class CoreStageProgress(BaseModel):
    """Tracks salesperson progress through C.O.R.E. stages.

    The coach agent populates these checklists based on conversation analysis.
    """

    current_stage: SalesStage = Field(
        SalesStage.CONNECT, description="Current stage in the sales process"
    )

    # Checklist items per stage (coach agent populates these)
    connect: dict[str, bool] = Field(
        default_factory=lambda: {
            "warm_greeting": False,
            "establish_credibility": False,
            "create_comfort": False,
        }
    )
    observe: dict[str, bool] = Field(
        default_factory=lambda: {
            "needs_discovery": False,
            "goal_identification": False,
            "motivator_mapping": False,
        }
    )
    recommend: dict[str, bool] = Field(
        default_factory=lambda: {
            "solution_presentation": False,
            "value_connection": False,
            "risk_mitigation": False,
        }
    )
    execute: dict[str, bool] = Field(
        default_factory=lambda: {
            "commitment_request": False,
            "objection_handling": False,
            "finalize_agreement": False,
        }
    )

    # Customer Motivator tracking
    pbms_expressed: list[str] = Field(
        default_factory=list, description="Customer motivators the customer has mentioned"
    )
    pbms_acknowledged: list[str] = Field(
        default_factory=list, description="Customer motivators the salesperson has acknowledged"
    )


class CustomerAgentState(TypedDict):
    """LangGraph state for customer agent.

    This state is passed through the graph and updated at each node.
    The messages field uses add_messages reducer to append conversation history.
    """

    # Conversation history (uses add_messages reducer for appending)
    messages: Annotated[list[BaseMessage], add_messages]
    turn_count: int

    # Persona (set at session start, immutable during session)
    persona: CustomerPersona

    # Customer's dynamic state (changes based on salesperson behavior)
    mood: Mood
    regard_level: RegardLevel

    # Objection tracking
    objections_available: list[str]  # Pool of objections to draw from
    objections_raised: list[str]  # Already raised in conversation
    objections_resolved: list[str]  # Successfully handled by salesperson

    # Progress tracking (coach agent populates later)
    stage_progress: CoreStageProgress

    # Session metadata
    session_id: str
    user_id: str
