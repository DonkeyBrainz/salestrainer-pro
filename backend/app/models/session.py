from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class SessionType(str, Enum):
    TRAINING = "training"
    EVALUATION = "evaluation"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Difficulty(str, Enum):
    HIGH_REGARD = "high_regard"
    MEDIUM_REGARD = "medium_regard"
    LOW_REGARD = "low_regard"
    NO_REGARD = "no_regard"


class Session(BaseModel):
    session_id: str
    user_id: str
    session_type: SessionType
    status: SessionStatus
    selected_persona: str | None = None
    difficulty: Difficulty
    system_instruction: str | None = None
    agent_state_snapshot: str | None = None  # JSON serialized agent state
    # Product context (for RAG filtering and analytics)
    product_category: str | None = None
    product_type: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration: int | None = None
    grade: str | None = None
    score: int | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    deleted_at: datetime | None = None


class SessionCreate(BaseModel):
    user_id: str
    session_type: SessionType = SessionType.TRAINING
    difficulty: Difficulty = Difficulty.MEDIUM_REGARD
    selected_persona: str | None = None
    system_instruction: str | None = None
    # Product selection (drives RAG filtering)
    product_category: str | None = None
    product_type: str | None = None


class SessionUpdate(BaseModel):
    status: SessionStatus | None = None
    ended_at: datetime | None = None
    duration: int | None = None
    message_count: int | None = None
    grade: str | None = None
    score: int | None = None
    agent_state_snapshot: str | None = None  # JSON serialized agent state


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    session_type: SessionType
    status: SessionStatus
    difficulty: Difficulty
    product_category: str | None = None
    product_type: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration: int | None = None
    message_count: int = 0


class SessionSummary(BaseModel):
    """Lightweight session model for list views."""

    session_id: str
    session_type: SessionType
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None = None
    duration: int | None = None
    selected_persona: str | None = None
    difficulty: Difficulty
    product_category: str | None = None
    product_type: str | None = None
    message_count: int = 0
    grade: str | None = None
    score: int | None = None
    has_evaluation: bool = False


class SessionListResponse(BaseModel):
    """Paginated session list response."""

    sessions: list[SessionSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


class SessionDetailResponse(BaseModel):
    """Complete session detail with transcript and evaluation."""

    session: SessionSummary
    transcript: dict[str, Any]
    evaluation: dict[str, Any] | None = None
