"""Store/regional/national rollup stats for manager and director dashboards.

Reuses stats_service.get_user_stats per agent (streak, weekly avg score,
total sessions) rather than re-deriving the scoring/streak math in bulk --
the org is small enough (a few hundred agents at most) that per-agent
Firestore reads are cheap, and this keeps a single source of truth for how
an individual agent's stats are computed.
"""

import asyncio

from app.core.exceptions import NotFoundError
from app.models.org_stats import (
    AgentLeaderboardEntry,
    NationalStatsResponse,
    OrgRollup,
    RegionStatsResponse,
    RegionSummary,
    StoreStatsResponse,
    StoreSummary,
)
from app.models.store import Store
from app.models.user import User
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.store_repository import StoreRepository
from app.repositories.user_repository import UserRepository
from app.services.stats_service import get_user_stats


async def _leaderboard_entries(
    users: list[User],
    session_repository: SessionRepository,
    evaluation_repository: EvaluationRepository,
    store_by_id: dict[str, Store],
) -> list[AgentLeaderboardEntry]:
    """Build a sorted leaderboard for the given users."""
    all_stats = await asyncio.gather(
        *(get_user_stats(u.user_id, session_repository, evaluation_repository) for u in users)
    )

    entries = [
        AgentLeaderboardEntry(
            user_id=user.user_id,
            name=user.name,
            store_id=user.store_id,
            store_name=store_by_id[user.store_id].name if user.store_id in store_by_id else None,
            total_sessions=stats.total_sessions,
            avg_score=stats.avg_score_this_week,
            current_streak=stats.current_streak,
        )
        for user, stats in zip(users, all_stats, strict=True)
    ]
    return _sort_leaderboard(entries)


def _sort_leaderboard(entries: list[AgentLeaderboardEntry]) -> list[AgentLeaderboardEntry]:
    """Sort by avg_score descending, unscored agents last."""
    return sorted(entries, key=lambda e: (e.avg_score is None, -(e.avg_score or 0.0)))


def _rollup(entries: list[AgentLeaderboardEntry]) -> OrgRollup:
    """Aggregate a leaderboard into a scope-level rollup."""
    total_sessions = sum(e.total_sessions for e in entries)
    scored = [e.avg_score for e in entries if e.avg_score is not None]
    avg_score = round(sum(scored) / len(scored), 1) if scored else None
    active_agent_count = sum(1 for e in entries if e.total_sessions > 0)
    return OrgRollup(
        total_sessions=total_sessions,
        avg_score=avg_score,
        active_agent_count=active_agent_count,
    )


async def get_store_stats(
    store_id: str,
    store_repository: StoreRepository,
    user_repository: UserRepository,
    session_repository: SessionRepository,
    evaluation_repository: EvaluationRepository,
) -> StoreStatsResponse:
    """Compute rollup + leaderboard for a single store."""
    store = await store_repository.get_by_id(store_id)
    if store is None:
        raise NotFoundError(f"Store '{store_id}' not found")

    users = await user_repository.list_by_store_ids([store_id])
    leaderboard = await _leaderboard_entries(
        users, session_repository, evaluation_repository, {store_id: store}
    )
    return StoreStatsResponse(
        store_id=store.store_id,
        store_name=store.name,
        region=store.region,
        rollup=_rollup(leaderboard),
        leaderboard=leaderboard,
    )


async def get_region_stats(
    region: str,
    store_repository: StoreRepository,
    user_repository: UserRepository,
    session_repository: SessionRepository,
    evaluation_repository: EvaluationRepository,
) -> RegionStatsResponse:
    """Compute rollup + per-store breakdown + combined leaderboard for a region."""
    stores = await store_repository.list_by_region(region)
    if not stores:
        raise NotFoundError(f"No stores found for region '{region}'")

    store_results = await asyncio.gather(
        *(
            get_store_stats(
                s.store_id,
                store_repository,
                user_repository,
                session_repository,
                evaluation_repository,
            )
            for s in stores
        )
    )

    combined_leaderboard = _sort_leaderboard(
        [entry for result in store_results for entry in result.leaderboard]
    )
    store_summaries = [
        StoreSummary(store_id=r.store_id, store_name=r.store_name, rollup=r.rollup)
        for r in store_results
    ]
    return RegionStatsResponse(
        region=region,
        rollup=_rollup(combined_leaderboard),
        stores=store_summaries,
        leaderboard=combined_leaderboard,
    )


async def get_national_stats(
    store_repository: StoreRepository,
    user_repository: UserRepository,
    session_repository: SessionRepository,
    evaluation_repository: EvaluationRepository,
) -> NationalStatsResponse:
    """Compute rollup + per-region breakdown + combined leaderboard for the org."""
    stores = await store_repository.list_all()
    regions = sorted({s.region for s in stores})

    region_results = await asyncio.gather(
        *(
            get_region_stats(
                r, store_repository, user_repository, session_repository, evaluation_repository
            )
            for r in regions
        )
    )

    combined_leaderboard = _sort_leaderboard(
        [entry for result in region_results for entry in result.leaderboard]
    )
    region_summaries = [
        RegionSummary(region=r.region, rollup=r.rollup, stores=r.stores) for r in region_results
    ]
    return NationalStatsResponse(
        rollup=_rollup(combined_leaderboard),
        regions=region_summaries,
        leaderboard=combined_leaderboard,
    )
