"""Pydantic models for store/regional/national rollup dashboards."""

from datetime import datetime

from pydantic import BaseModel


class CoreBreakdown(BaseModel):
    connect: float
    observe: float
    recommend: float
    execute: float


class AgentLeaderboardEntry(BaseModel):
    user_id: str
    name: str
    store_id: str | None = None
    store_name: str | None = None
    total_sessions: int
    sessions_this_week: int = 0
    avg_score: float | None = None  # this week's avg score, None if no scored sessions
    current_streak: int
    core: CoreBreakdown | None = None  # last-30-day CORE mastery breakdown
    score_trend: list[float] = []  # up to last 5 scored sessions, oldest first
    weekly_delta: float | None = None  # score_trend[-1] - score_trend[0], None if <2 points
    last_active_at: datetime | None = None
    flag: str | None = None  # reason this agent needs attention, None if not flagged


class OrgRollup(BaseModel):
    total_sessions: int
    sessions_this_week: int = 0
    avg_score: float | None = None  # mean of per-agent avg_score, None if no scored agents
    avg_score_delta: float | None = None  # mean of per-agent weekly_delta, None if none available
    active_agent_count: int  # agents with at least one completed session


class StoreStatsResponse(BaseModel):
    store_id: str
    store_name: str
    region: str
    manager_name: str | None = None
    rollup: OrgRollup
    leaderboard: list[AgentLeaderboardEntry]
    store_rank: int | None = None  # rank among all stores org-wide, 1 = highest avg_score
    store_count: int = 0


class StoreSummary(BaseModel):
    store_id: str
    store_name: str
    manager_name: str | None = None
    rollup: OrgRollup


class RegionStatsResponse(BaseModel):
    region: str
    rollup: OrgRollup
    stores: list[StoreSummary]
    leaderboard: list[AgentLeaderboardEntry]


class RegionSummary(BaseModel):
    region: str
    rollup: OrgRollup
    stores: list[StoreSummary]


class NationalStatsResponse(BaseModel):
    rollup: OrgRollup
    regions: list[RegionSummary]
    leaderboard: list[AgentLeaderboardEntry]


class StoreListEntry(BaseModel):
    store_id: str
    name: str
    region: str
