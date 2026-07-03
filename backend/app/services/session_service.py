from datetime import UTC, datetime

from app.models.session import (
    Session,
    SessionCreate,
    SessionStatus,
    SessionUpdate,
)
from app.models.transcript import (
    Transcript,
    TranscriptCreate,
    TranscriptMessage,
)
from app.repositories.session_repository import SessionRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.repositories.user_repository import UserRepository


class SessionService:
    """Service for managing training/evaluation sessions."""

    def __init__(
        self,
        session_repository: SessionRepository,
        transcript_repository: TranscriptRepository,
        user_repository: UserRepository,
    ) -> None:
        self.session_repo = session_repository
        self.transcript_repo = transcript_repository
        self.user_repo = user_repository

    async def start_session(self, session_create: SessionCreate) -> Session:
        """Create new session and return session object.

        Looks up the creating user's store_id so it can be denormalized onto
        the session doc for store/regional/national rollup queries.
        """
        user = await self.user_repo.get_by_id(session_create.user_id)
        store_id = user.store_id if user else None
        session = await self.session_repo.create(session_create, store_id=store_id)
        return session

    async def end_session(
        self,
        session_id: str,
        messages: list[TranscriptMessage],
        status: SessionStatus = SessionStatus.COMPLETED,
        agent_state_snapshot: str | None = None,
    ) -> None:
        """Update session with final stats and save transcript.

        Args:
            session_id: The session to end.
            messages: Conversation messages to save as transcript.
            status: Final session status.
            agent_state_snapshot: Optional JSON serialized agent state.
        """
        # Get session to calculate duration
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Calculate metadata
        ended_at = datetime.now(UTC)
        duration = int((ended_at - session.started_at).total_seconds())

        # Update session
        session_update = SessionUpdate(
            status=status,
            ended_at=ended_at,
            duration=duration,
            message_count=len(messages),
            agent_state_snapshot=agent_state_snapshot,
        )
        await self.session_repo.update(session_id, session_update)

        # Save transcript
        transcript_create = TranscriptCreate(
            session_id=session_id,
            user_id=session.user_id,
            messages=messages,
        )
        await self.transcript_repo.create(transcript_create)

    async def get_session(self, session_id: str) -> Session | None:
        """Get session by ID."""
        return await self.session_repo.get_by_id(session_id)

    async def get_transcript(self, session_id: str) -> Transcript | None:
        """Get transcript for session."""
        return await self.transcript_repo.get_by_session_id(session_id)
