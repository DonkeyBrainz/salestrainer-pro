from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class TranscriptMessage(BaseModel):
    """Individual message in conversation."""

    message_id: str
    role: MessageRole
    text: str
    timestamp: datetime
    is_final: bool = True
    audio_length_ms: int | None = None
    confidence: float | None = None
    internal_reasoning: str | None = None  # Agent's internal reasoning (ASSISTANT only)


class Transcript(BaseModel):
    """Full conversation transcript."""

    transcript_id: str
    session_id: str
    user_id: str
    messages: list[TranscriptMessage] = []
    total_messages: int = 0
    total_words: int = 0
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TranscriptCreate(BaseModel):
    """Create transcript (with buffered messages)."""

    session_id: str
    user_id: str
    messages: list[TranscriptMessage]


class TranscriptResponse(BaseModel):
    """API response model."""

    transcript_id: str
    session_id: str
    messages: list[TranscriptMessage]
    total_messages: int
    started_at: datetime
    ended_at: datetime | None = None
