"""Sessions API endpoints for viewing session history."""

from fastapi import APIRouter, HTTPException, status

from app.agents.personas import get_persona
from app.core.dependencies import (
    CurrentUserDep,
    EvaluationRepositoryDep,
    SessionRepositoryDep,
    TranscriptRepositoryDep,
)
from app.models.session import (
    Session,
    SessionDetailResponse,
    SessionListResponse,
    SessionSummary,
    SessionType,
)

router = APIRouter(prefix="/api/v1/sessions")


def _session_to_summary(session: "Session", has_evaluation: bool = False) -> SessionSummary:
    """Convert Session model to SessionSummary.

    Sessions store the persona *id* (a stable slug); the archive display
    needs the human name, so it's resolved here rather than in every caller.
    Evaluation-mode identity redaction only applies to the *live* run — once
    a session is filed, showing the real name is exactly what "declassified"
    means.
    """
    persona = get_persona(session.selected_persona) if session.selected_persona else None
    return SessionSummary(
        session_id=session.session_id,
        session_type=session.session_type,
        status=session.status,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration=session.duration,
        selected_persona=session.selected_persona,
        persona_name=persona.name if persona else None,
        difficulty=session.difficulty,
        message_count=session.message_count,
        grade=session.grade,
        score=session.score,
        has_evaluation=has_evaluation,
        hints_used=session.hints_used,
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    current_user: CurrentUserDep,
    session_repository: SessionRepositoryDep,
    evaluation_repository: EvaluationRepositoryDep,
    limit: int = 20,
    offset: int = 0,
    session_type: SessionType | None = None,
) -> SessionListResponse:
    """List sessions for authenticated user with pagination.

    Args:
        current_user: Authenticated user from JWT token
        session_repository: Session repository dependency
        evaluation_repository: Evaluation repository dependency
        limit: Maximum number of sessions to return (default: 20)
        offset: Number of sessions to skip (default: 0)
        session_type: Optional filter by session type (training/evaluation)

    Returns:
        Paginated list of session summaries with evaluation flags
    """
    # Get paginated sessions
    sessions, total_count = await session_repository.list_by_user_with_pagination(
        user_id=current_user.user_id,
        limit=limit,
        offset=offset,
        session_type=session_type,
    )

    # Check which sessions have evaluations and get grades/scores
    session_summaries = []
    for session in sessions:
        evaluation = await evaluation_repository.get_by_session_id(session.session_id)
        has_evaluation = evaluation is not None

        # Use grade/score from evaluation if available, otherwise fall back to session
        grade = evaluation.grade if evaluation else session.grade
        score = evaluation.final_score if evaluation else session.score

        # Round score to whole number
        if score is not None:
            score = round(score)

        summary = _session_to_summary(session, has_evaluation)
        summary.grade = grade
        summary.score = score
        session_summaries.append(summary)

    # Calculate if there are more results
    has_more = (offset + limit) < total_count

    return SessionListResponse(
        sessions=session_summaries,
        total=total_count,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: str,
    current_user: CurrentUserDep,
    session_repository: SessionRepositoryDep,
    transcript_repository: TranscriptRepositoryDep,
    evaluation_repository: EvaluationRepositoryDep,
) -> SessionDetailResponse:
    """Get complete session details with transcript and evaluation.

    Args:
        session_id: Session ID to retrieve
        current_user: Authenticated user from JWT token
        session_repository: Session repository dependency
        transcript_repository: Transcript repository dependency
        evaluation_repository: Evaluation repository dependency

    Returns:
        Complete session with transcript and evaluation

    Raises:
        404: Session not found
        403: Session belongs to another user
    """
    # Get session
    session = await session_repository.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Verify session belongs to current user
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this session",
        )

    # Get transcript
    transcript = await transcript_repository.get_by_session_id(session_id)
    transcript_data = {
        "messages": [msg.model_dump() for msg in transcript.messages] if transcript else [],
        "total_messages": transcript.total_messages if transcript else 0,
    }

    # Get evaluation (may be None)
    evaluation = await evaluation_repository.get_by_session_id(session_id)
    evaluation_data = evaluation.model_dump() if evaluation else None

    # Create session summary with evaluation data if available
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
