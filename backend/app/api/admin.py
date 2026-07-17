"""Admin API endpoints for metrics and monitoring.

These endpoints are restricted to admin users only.
"""

import re
from collections import Counter, defaultdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud.firestore import AsyncClient
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.core.dependencies import (
    EvaluationRepositoryDep,
    SessionRepositoryDep,
    TranscriptRepositoryDep,
    get_current_user,
)
from app.core.exceptions import ForbiddenError
from app.models.session import (
    SessionDetailResponse,
    SessionListResponse,
    SessionSummary,
    SessionType,
)
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# Admin user emails (configure in settings later)
ADMIN_EMAILS = [
    "user@example.com",
    "miklpuerto69@gmail.com",
]


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Verify user has admin privileges.

    Args:
        user: Current authenticated user

    Returns:
        User if they are an admin

    Raises:
        ForbiddenError: If user is not an admin
    """
    if user.email not in ADMIN_EMAILS:
        raise ForbiddenError("Admin access required")
    return user


# Response models
class PersonaMetrics(BaseModel):
    """Metrics for a single persona."""

    persona_id: str = Field(serialization_alias="personaId")
    sessions: int
    message_count: int = Field(serialization_alias="messageCount")
    volunteer_score: float = Field(serialization_alias="volunteerScore")
    first_message_volunteer_rate: float = Field(serialization_alias="firstMessageVolunteerRate")
    sales_mode_violations: int = Field(serialization_alias="salesModeViolations")
    volunteer_categories: dict[str, int] = Field(serialization_alias="volunteerCategories")

    model_config = {"populate_by_name": True}


class DifficultyMetrics(BaseModel):
    """Metrics grouped by difficulty level."""

    difficulty: str
    sessions: int
    message_count: int = Field(serialization_alias="messageCount")
    volunteer_score: float = Field(serialization_alias="volunteerScore")
    first_message_volunteer_rate: float = Field(serialization_alias="firstMessageVolunteerRate")

    model_config = {"populate_by_name": True}


class PersonaMetricsResponse(BaseModel):
    """Response for persona metrics endpoint."""

    total_sessions: int = Field(serialization_alias="totalSessions")
    total_transcripts: int = Field(serialization_alias="totalTranscripts")
    by_persona: list[PersonaMetrics] = Field(serialization_alias="byPersona")
    by_difficulty: list[DifficultyMetrics] = Field(serialization_alias="byDifficulty")

    model_config = {"populate_by_name": True}


class UserMetrics(BaseModel):
    """Metrics for a single user."""

    user_id: str = Field(serialization_alias="userId")
    user_name: str = Field(serialization_alias="userName")
    user_email: str = Field(serialization_alias="userEmail")
    total_sessions: int = Field(serialization_alias="totalSessions")
    total_transcripts: int = Field(serialization_alias="totalTranscripts")
    total_messages: int = Field(serialization_alias="totalMessages")
    avg_messages_per_session: float = Field(serialization_alias="avgMessagesPerSession")
    avg_session_duration_minutes: float = Field(serialization_alias="avgSessionDurationMinutes")
    session_breakdown: dict[str, int] = Field(serialization_alias="sessionBreakdown")
    persona_usage: dict[str, int] = Field(serialization_alias="personaUsage")
    last_active: str | None = Field(serialization_alias="lastActive")

    model_config = {"populate_by_name": True}


class UserMetricsResponse(BaseModel):
    """Response for user metrics endpoint."""

    total_users: int = Field(serialization_alias="totalUsers")
    active_users_7d: int = Field(serialization_alias="activeUsers7d")
    active_users_30d: int = Field(serialization_alias="activeUsers30d")
    users: list[UserMetrics]

    model_config = {"populate_by_name": True}


# Volunteer behavior patterns
VOLUNTEER_PATTERNS = {
    "name": [r"(?i)I'm (\w+)", r"(?i)my name is (\w+)"],
    "needs": [r"(?i)I'm looking for", r"(?i)I need", r"(?i)we're looking for"],
    "personal": [r"(?i)my (?:husband|wife|kids|family)", r"(?i)we (?:just|recently) moved"],
    "budget": [r"(?i)budget|between \$?\d+|under \$?\d+"],
    "enthusiasm": [r"(?i)(?:so|really|very) excited", r"!$"],
}


@router.get("/personas/metrics", response_model=PersonaMetricsResponse)
async def get_persona_metrics(
    admin: Annotated[User, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PersonaMetricsResponse:
    """Get metrics for all personas across all users.

    Includes:
    - Volunteer behavior scores
    - Sales mode violation counts
    - Session counts
    - Message counts

    Args:
        admin: Authenticated admin user
        settings: Application settings

    Returns:
        Persona metrics response
    """
    db = AsyncClient(project=settings.gcp_project_id, database=settings.firestore_database)

    # Get all sessions
    sessions_collection = db.collection("sessions")
    sessions = []
    async for doc in sessions_collection.where("is_deleted", "==", False).stream():
        session_data = doc.to_dict()
        session_data["session_id"] = doc.id
        sessions.append(session_data)

    # Get all transcripts
    transcripts_collection = db.collection("transcripts")
    transcripts = []
    async for doc in transcripts_collection.stream():
        transcript_data = doc.to_dict()
        transcript_data["transcript_id"] = doc.id
        transcripts.append(transcript_data)

    # Map sessions to transcripts
    session_map = {s["session_id"]: s for s in sessions}
    for transcript in transcripts:
        session_id = transcript.get("session_id")
        if session_id in session_map:
            transcript["session"] = session_map[session_id]

    # Analyze by persona and difficulty
    by_persona: dict[str, Any] = defaultdict(
        lambda: {
            "sessions": 0,
            "message_count": 0,
            "first_message_volunteers": 0,
            "volunteer_events": defaultdict(int),
            "total_volunteer_score": 0,
        }
    )

    by_difficulty: dict[str, Any] = defaultdict(
        lambda: {
            "sessions": 0,
            "message_count": 0,
            "first_message_volunteers": 0,
            "total_volunteer_score": 0,
        }
    )

    for transcript in transcripts:
        session = transcript.get("session")
        if not session:
            continue

        messages = transcript.get("messages", [])
        persona = session.get("selected_persona") or "unknown"
        difficulty = session.get("difficulty") or "unknown"

        by_persona[persona]["sessions"] += 1
        by_difficulty[difficulty]["sessions"] += 1

        # Check first customer message
        first_customer_msg = None
        for msg in messages:
            if msg.get("role") in ["assistant", "model"]:
                first_customer_msg = msg.get("text", "")
                break

        if first_customer_msg:
            first_msg_score = 0
            for category, patterns in VOLUNTEER_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, first_customer_msg):
                        first_msg_score += 1
                        by_persona[persona]["volunteer_events"][category] += 1
                        break

            if first_msg_score > 0:
                by_persona[persona]["first_message_volunteers"] += 1
                by_difficulty[difficulty]["first_message_volunteers"] += 1

        # Count all customer messages and calculate scores
        for msg in messages:
            if msg.get("role") in ["assistant", "model"]:
                customer_text = msg.get("text", "")
                by_persona[persona]["message_count"] += 1
                by_difficulty[difficulty]["message_count"] += 1

                msg_score = 0
                for category, patterns in VOLUNTEER_PATTERNS.items():
                    for pattern in patterns:
                        if re.search(pattern, customer_text):
                            msg_score += 1
                            break

                by_persona[persona]["total_volunteer_score"] += msg_score
                by_difficulty[difficulty]["total_volunteer_score"] += msg_score

    # Format response
    persona_metrics = []
    for persona_id, stats in by_persona.items():
        avg_score = (
            stats["total_volunteer_score"] / stats["message_count"]
            if stats["message_count"] > 0
            else 0
        )
        first_msg_rate = (
            stats["first_message_volunteers"] / stats["sessions"] * 100
            if stats["sessions"] > 0
            else 0
        )

        persona_metrics.append(
            PersonaMetrics(
                persona_id=persona_id,
                sessions=stats["sessions"],
                message_count=stats["message_count"],
                volunteer_score=round(avg_score, 2),
                first_message_volunteer_rate=round(first_msg_rate, 1),
                sales_mode_violations=0,  # TODO: Implement sales mode detection
                volunteer_categories=dict(stats["volunteer_events"]),
            )
        )

    difficulty_metrics = []
    for difficulty, stats in by_difficulty.items():
        avg_score = (
            stats["total_volunteer_score"] / stats["message_count"]
            if stats["message_count"] > 0
            else 0
        )
        first_msg_rate = (
            stats["first_message_volunteers"] / stats["sessions"] * 100
            if stats["sessions"] > 0
            else 0
        )

        difficulty_metrics.append(
            DifficultyMetrics(
                difficulty=difficulty,
                sessions=stats["sessions"],
                message_count=stats["message_count"],
                volunteer_score=round(avg_score, 2),
                first_message_volunteer_rate=round(first_msg_rate, 1),
            )
        )

    # Sort by volunteer score
    persona_metrics.sort(key=lambda x: x.volunteer_score, reverse=True)
    difficulty_metrics.sort(key=lambda x: x.volunteer_score, reverse=True)

    return PersonaMetricsResponse(
        total_sessions=len(sessions),
        total_transcripts=len(transcripts),
        by_persona=persona_metrics,
        by_difficulty=difficulty_metrics,
    )


@router.get("/users/metrics", response_model=UserMetricsResponse)
async def get_user_metrics(
    admin: Annotated[User, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserMetricsResponse:
    """Get metrics for all users.

    Includes:
    - Session counts
    - Message counts
    - Persona usage
    - Activity patterns

    Args:
        admin: Authenticated admin user
        settings: Application settings

    Returns:
        User metrics response
    """
    from datetime import UTC, datetime, timedelta

    db = AsyncClient(project=settings.gcp_project_id, database=settings.firestore_database)

    # Get all users
    users_collection = db.collection("users")
    users = []
    async for doc in users_collection.stream():
        user_data = doc.to_dict()
        user_data["user_id"] = doc.id
        users.append(user_data)

    # Get all sessions
    sessions_collection = db.collection("sessions")
    sessions = []
    async for doc in sessions_collection.where("is_deleted", "==", False).stream():
        session_data = doc.to_dict()
        sessions.append(session_data)

    # Get all transcripts
    transcripts_collection = db.collection("transcripts")
    transcripts = []
    async for doc in transcripts_collection.stream():
        transcript_data = doc.to_dict()
        transcripts.append(transcript_data)

    # Group by user
    sessions_by_user = defaultdict(list)
    for session in sessions:
        user_id = session.get("user_id")
        if user_id:
            sessions_by_user[user_id].append(session)

    transcripts_by_session = {}
    for transcript in transcripts:
        session_id = transcript.get("session_id")
        if session_id:
            transcripts_by_session[session_id] = transcript

    # Calculate user metrics
    user_metrics_list = []
    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    active_7d = 0
    active_30d = 0

    for user in users:
        user_id = user["user_id"]
        user_sessions = sessions_by_user.get(user_id, [])

        # Get transcripts for this user's sessions
        user_transcripts = []
        for session in user_sessions:
            session_id = session.get("session_id")
            if session_id in transcripts_by_session:
                user_transcripts.append(transcripts_by_session[session_id])

        # Calculate stats
        total_messages = sum(len(t.get("messages", [])) for t in user_transcripts)
        avg_messages = total_messages / len(user_transcripts) if user_transcripts else 0

        # Session breakdown
        session_breakdown = Counter(s.get("session_type") or "unknown" for s in user_sessions)

        # Persona usage
        persona_usage = Counter(s.get("selected_persona") or "unknown" for s in user_sessions)

        # Duration
        total_duration = sum(s.get("duration", 0) for s in user_sessions if s.get("duration"))
        session_count_with_duration = sum(1 for s in user_sessions if s.get("duration"))
        avg_duration = (
            total_duration / session_count_with_duration / 60
            if session_count_with_duration > 0
            else 0
        )

        # Last active
        last_active = None
        if user_sessions:
            last_session = max(
                user_sessions,
                key=lambda s: s.get("started_at", datetime.min.replace(tzinfo=UTC)),
            )
            last_active_dt = last_session.get("started_at")
            if last_active_dt:
                last_active = (
                    last_active_dt.isoformat()
                    if isinstance(last_active_dt, datetime)
                    else str(last_active_dt)
                )

                # Count active users
                if isinstance(last_active_dt, datetime):
                    if last_active_dt >= seven_days_ago:
                        active_7d += 1
                    if last_active_dt >= thirty_days_ago:
                        active_30d += 1

        user_metrics_list.append(
            UserMetrics(
                user_id=user_id,
                user_name=user.get("name", "Unknown"),
                user_email=user.get("email", "unknown"),
                total_sessions=len(user_sessions),
                total_transcripts=len(user_transcripts),
                total_messages=total_messages,
                avg_messages_per_session=round(avg_messages, 1),
                avg_session_duration_minutes=round(avg_duration, 1),
                session_breakdown=dict(session_breakdown),
                persona_usage=dict(persona_usage),
                last_active=last_active,
            )
        )

    # Sort by total sessions (most active first)
    user_metrics_list.sort(key=lambda x: x.total_sessions, reverse=True)

    return UserMetricsResponse(
        total_users=len(users),
        active_users_7d=active_7d,
        active_users_30d=active_30d,
        users=user_metrics_list,
    )


def _session_to_summary(session: Any, has_evaluation: bool = False) -> SessionSummary:
    """Convert Session model to SessionSummary for admin views."""
    return SessionSummary(
        session_id=session.session_id,
        session_type=session.session_type,
        status=session.status,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration=session.duration,
        selected_persona=session.selected_persona,
        difficulty=session.difficulty,
        message_count=session.message_count,
        grade=session.grade,
        score=session.score,
        has_evaluation=has_evaluation,
    )


@router.get("/users/{user_id}/sessions", response_model=SessionListResponse)
async def get_user_sessions(
    user_id: str,
    admin: Annotated[User, Depends(require_admin)],
    session_repository: SessionRepositoryDep,
    evaluation_repository: EvaluationRepositoryDep,
    limit: int = 20,
    offset: int = 0,
    session_type: SessionType | None = None,
) -> SessionListResponse:
    """Get sessions for a specific user (admin only).

    Args:
        user_id: Target user ID
        admin: Authenticated admin user
        session_repository: Session repository dependency
        evaluation_repository: Evaluation repository dependency
        limit: Maximum number of sessions to return
        offset: Number of sessions to skip
        session_type: Optional session type filter

    Returns:
        Paginated list of session summaries
    """
    sessions, total_count = await session_repository.list_by_user_with_pagination(
        user_id=user_id,
        limit=limit,
        offset=offset,
        session_type=session_type,
    )

    session_summaries = []
    for session in sessions:
        evaluation = await evaluation_repository.get_by_session_id(session.session_id)
        has_evaluation = evaluation is not None

        grade = evaluation.grade if evaluation else session.grade
        score = evaluation.final_score if evaluation else session.score
        if score is not None:
            score = round(score)

        summary = _session_to_summary(session, has_evaluation)
        summary.grade = grade
        summary.score = score
        session_summaries.append(summary)

    has_more = (offset + limit) < total_count

    return SessionListResponse(
        sessions=session_summaries,
        total=total_count,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: str,
    admin: Annotated[User, Depends(require_admin)],
    session_repository: SessionRepositoryDep,
    transcript_repository: TranscriptRepositoryDep,
    evaluation_repository: EvaluationRepositoryDep,
) -> SessionDetailResponse:
    """Get session detail for any session (admin only, no ownership check).

    Args:
        session_id: Session ID to retrieve
        admin: Authenticated admin user
        session_repository: Session repository dependency
        transcript_repository: Transcript repository dependency
        evaluation_repository: Evaluation repository dependency

    Returns:
        Complete session with transcript and evaluation
    """
    session = await session_repository.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    transcript = await transcript_repository.get_by_session_id(session_id)
    transcript_data = {
        "messages": [msg.model_dump() for msg in transcript.messages] if transcript else [],
        "total_messages": transcript.total_messages if transcript else 0,
    }

    evaluation = await evaluation_repository.get_by_session_id(session_id)
    evaluation_data = evaluation.model_dump() if evaluation else None

    session_summary = _session_to_summary(session, has_evaluation=evaluation is not None)
    if evaluation:
        session_summary.grade = evaluation.grade
        session_summary.score = (
            round(evaluation.final_score) if evaluation.final_score is not None else None
        )

    return SessionDetailResponse(
        session=session_summary,
        transcript=transcript_data,
        evaluation=evaluation_data,
    )
