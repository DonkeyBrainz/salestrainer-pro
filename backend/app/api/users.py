"""User-facing API endpoints (stats, profile)."""

from fastapi import APIRouter

from app.core.dependencies import (
    CurrentUserDep,
    EvaluationRepositoryDep,
    SessionRepositoryDep,
)
from app.models.stats import UserStatsResponse
from app.services.stats_service import get_user_stats

router = APIRouter(prefix="/api/v1/users")


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_my_stats(
    current_user: CurrentUserDep,
    session_repository: SessionRepositoryDep,
    evaluation_repository: EvaluationRepositoryDep,
) -> UserStatsResponse:
    """Return aggregated dashboard stats for the authenticated user.

    Computes streak, weekly session count, CORE stage mastery averages (with
    30-day delta), and recent activity from Firestore sessions + evaluations.
    """
    return await get_user_stats(
        user_id=current_user.user_id,
        session_repository=session_repository,
        evaluation_repository=evaluation_repository,
    )
