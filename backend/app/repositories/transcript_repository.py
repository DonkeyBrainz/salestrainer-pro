from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.models.transcript import (
    MessageRole,
    Transcript,
    TranscriptCreate,
    TranscriptMessage,
)
from app.repositories.base import BaseRepository


class TranscriptRepository(BaseRepository):
    """Repository for transcript data access."""

    _collection_name = "transcripts"

    async def create(self, transcript_create: TranscriptCreate) -> Transcript:
        """Create new transcript."""
        transcript_id = str(uuid4())
        now = datetime.now(UTC)

        messages = transcript_create.messages
        total_messages = len(messages)
        total_words = self._calculate_word_count(messages)
        started_at = messages[0].timestamp if messages else now
        ended_at = messages[-1].timestamp if messages else None

        # Serialize messages for Firestore
        messages_data = [msg.model_dump() for msg in messages]

        transcript_data = {
            "transcript_id": transcript_id,
            "session_id": transcript_create.session_id,
            "user_id": transcript_create.user_id,
            "messages": messages_data,
            "total_messages": total_messages,
            "total_words": total_words,
            "started_at": started_at,
            "ended_at": ended_at,
            "created_at": now,
            "updated_at": now,
        }

        await self.collection.document(transcript_id).set(transcript_data)
        return self._doc_to_transcript(transcript_id, transcript_data)

    async def get_by_session_id(self, session_id: str) -> Transcript | None:
        """Get transcript by session ID."""
        query = self.collection.where("session_id", "==", session_id).limit(1)
        docs = query.stream()

        async for doc in docs:
            return self._doc_to_transcript(doc.id, doc.to_dict())
        return None

    async def get_by_id(self, transcript_id: str) -> Transcript | None:
        """Get transcript by ID."""
        doc = await self.collection.document(transcript_id).get()
        if not doc.exists:
            return None

        return self._doc_to_transcript(transcript_id, doc.to_dict())

    def _doc_to_transcript(self, doc_id: str, data: dict[str, Any]) -> Transcript:
        """Convert Firestore document to Transcript model."""
        # Deserialize messages
        messages_data = data.get("messages", [])
        messages = [
            TranscriptMessage(
                message_id=msg["message_id"],
                role=MessageRole(msg["role"]),
                text=msg["text"],
                timestamp=msg["timestamp"],
                is_final=msg.get("is_final", True),
                audio_length_ms=msg.get("audio_length_ms"),
                confidence=msg.get("confidence"),
            )
            for msg in messages_data
        ]

        return Transcript(
            transcript_id=doc_id,
            session_id=data["session_id"],
            user_id=data["user_id"],
            messages=messages,
            total_messages=data.get("total_messages", 0),
            total_words=data.get("total_words", 0),
            started_at=data["started_at"],
            ended_at=data.get("ended_at"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    def _calculate_word_count(self, messages: list[TranscriptMessage]) -> int:
        """Calculate total word count from messages."""
        return sum(len(msg.text.split()) for msg in messages)
