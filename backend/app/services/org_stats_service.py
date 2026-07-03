"""Store/regional/national rollup stats for manager and director dashboards.

Reuses stats_service.get_user_stats per agent (streak, weekly avg score,
total sessions) rather than re-deriving the scoring/streak math in bulk --
the org is small enough (a few hundred agents at most) that per-agent
Firestore reads are cheap, and this keeps a single source of truth for how
an individual agent's stats are computed.
"""

import asyncio
from datetime import UTC, datetime

from app.core.exceptions import NotFoundError
from app.models.org_stats import (
    AgentLeaderboardEntry,
    CoreBreakdown,
    NationalStatsResponse,
    OrgRollup,
    RegionStatsResponse,
    RegionSummary,
    StoreStatsResponse,
    StoreSummary,
)
from app.models.stats import UserStatsResponse
from app.models.store import Store
from app.models.user import User
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.store_repository import StoreRepository
from app.repositories.user_repository import UserRepository
from app.services.stats_service import get_user_stats

LOW_ACTIVITY_DAYS = 5
LOW_SCORE_THRESHOLD = 55.0


def _core_breakdown(stats: UserStatsResponse) -> CoreBreakdown | None:
    if not stats.core_mastery:
        return None
    by_stage = {s.stage: s.mastery_pct for s in stats.core_mastery}
    return CoreBreakdown(
        connect=by_stage.get("CONNECT", 0.0),
        observe=by_stage.get("OBSERVE", 0.0),
        recommend=by_stage.get("RECOMMEND", 0.0),
        execute=by_stage.get("EXECUTE", 0.0),
    )


def _score_trend(stats: UserStatsResponse) -> list[float]:
    """Last up to 5 scored sessions, oldest first (recent_activity is newest-first)."""
    scored = [a.score for a in stats.recent_activity if a.score is not None]
    return [float(s) for s in reversed(scored)]


def _weekly_delta(trend: list[float]) -> float | None:
    if len(trend) < 2:
        return None
    return round(trend[-1] - trend[0], 1)


def _flag(stats: UserStatsResponse, trend: list[float]) -> str | None:
    """Reason this agent needs attention, checked in priority order."""
    if stats.total_sessions == 0:
        return "No sessions logged yet"

    if stats.recent_activity:
        days_inactive = (datetime.now(UTC) - stats.recent_activity[0].started_at).days
        if days_inactive >= LOW_ACTIVITY_DAYS:
            return f"Low activity — {days_inactive} days inactive"

    if stats.avg_score_this_week is not None and stats.avg_score_this_week < LOW_SCORE_THRESHOLD:
        return "Below 55 threshold"

    if len(trend) >= 3 and trend[-1] < trend[-2] < trend[-3]:
        return "Declining trend"

    return None


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

    entries = []
    for user, stats in zip(users, all_stats, strict=True):
        trend = _score_trend(stats)
        entries.append(
            AgentLeaderboardEntry(
                user_id=user.user_id,
                name=user.name,
                store_id=user.store_id,
                store_name=(
                    store_by_id[user.store_id].name if user.store_id in store_by_id else None
                ),
                total_sessions=stats.total_sessions,
                sessions_this_week=stats.sessions_this_week,
                avg_score=stats.avg_score_this_week,
                current_streak=stats.current_streak,
                core=_core_breakdown(stats),
                score_trend=trend,
                weekly_delta=_weekly_delta(trend),
                last_active_at=(
                    stats.recent_activity[0].started_at if stats.recent_activity else None
                ),
                flag=_flag(stats, trend),
            )
        )
    return _sort_leaderboard(entries)


def _sort_leaderboard(entries: list[AgentLeaderboardEntry]) -> list[AgentLeaderboardEntry]:
    """Sort by avg_score descending, unscored agents last."""
    return sorted(entries, key=lambda e: (e.avg_score is None, -(e.avg_score or 0.0)))


def _rollup(entries: list[AgentLeaderboardEntry]) -> OrgRollup:
    """Aggregate a leaderboard into a scope-level rollup."""
    total_sessions = sum(e.total_sessions for e in entries)
    sessions_this_week = sum(e.sessions_this_week for e in entries)
    scored = [e.avg_score for e in entries if e.avg_score is not None]
    avg_score = round(sum(scored) / len(scored), 1) if scored else None
    deltas = [e.weekly_delta for e in entries if e.weekly_delta is not None]
    avg_score_delta = round(sum(deltas) / len(deltas), 1) if deltas else None
    active_agent_count = sum(1 for e in entries if e.total_sessions > 0)
    return OrgRollup(
        total_sessions=total_sessions,
        sessions_this_week=sessions_this_week,
        avg_score=avg_score,
        avg_score_delta=avg_score_delta,
        active_agent_count=active_agent_count,
    )


async def _all_store_avg_scores(
    store_repository: StoreRepository,
    user_repository: UserRepository,
    session_repository: SessionRepository,
    evaluation_repository: EvaluationRepository,
) -> dict[str, float | None]:
    """Avg score per store org-wide, for store-rank comparisons.

    Recomputes per-agent stats for every store rather than reusing
    get_store_stats, to avoid the cost of building a full leaderboard
    (CORE breakdown, trend, flags) for stores we only need one number from.
    """
    stores = await store_repository.list_all()

    async def _avg_for(store: Store) -> tuple[str, float | None]:
        users = await user_repository.list_by_store_ids([store.store_id])
        stats = await asyncio.gather(
            *(get_user_stats(u.user_id, session_repository, evaluation_repository) for u in users)
        )
        scores = [s.avg_score_this_week for s in stats if s.avg_score_this_week is not None]
        avg = round(sum(scores) / len(scores), 1) if scores else None
        return store.store_id, avg

    results = await asyncio.gather(*(_avg_for(s) for s in stores))
    return dict(results)


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
    rollup = _rollup(leaderboard)

    all_avgs = await _all_store_avg_scores(
        store_repository, user_repository, session_repository, evaluation_repository
    )
    store_rank = None
    if rollup.avg_score is not None:
        better = sum(
            1
            for sid, avg in all_avgs.items()
            if sid != store_id and avg is not None and avg > rollup.avg_score
        )
        store_rank = better + 1

    manager_name = next((u.name for u in users if u.role == "manager"), None)

    return StoreStatsResponse(
        store_id=store.store_id,
        store_name=store.name,
        region=store.region,
        manager_name=manager_name,
        rollup=rollup,
        leaderboard=leaderboard,
        store_rank=store_rank,
        store_count=len(all_avgs),
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
        StoreSummary(
            store_id=r.store_id,
            store_name=r.store_name,
            manager_name=r.manager_name,
            rollup=r.rollup,
        )
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
