"""Data modules for sales training content."""

from app.data.core_system import (
    CORE_FULL_CONTEXT,
    CORE_STAGES,
    CUSTOMER_MOTIVATORS,
    get_stage_content,
    get_stage_requirements,
)
from app.data.objections import (
    ALL_OBJECTIONS,
    OBJECTIONS_BY_CATEGORY,
    ObjectionCategory,
    ObjectionEntry,
    get_objection_texts,
    get_objections_by_category,
    get_objections_by_difficulty,
)

__all__ = [
    # C.O.R.E. system
    "CORE_FULL_CONTEXT",
    "CORE_STAGES",
    "CUSTOMER_MOTIVATORS",
    "get_stage_content",
    "get_stage_requirements",
    # Objections
    "ALL_OBJECTIONS",
    "OBJECTIONS_BY_CATEGORY",
    "ObjectionCategory",
    "ObjectionEntry",
    "get_objection_texts",
    "get_objections_by_category",
    "get_objections_by_difficulty",
]
