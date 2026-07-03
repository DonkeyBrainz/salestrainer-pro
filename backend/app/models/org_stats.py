"""Pydantic models for store/regional/national rollup dashboards."""

from pydantic import BaseModel


class AgentLeaderboardEntry(BaseModel):
    user_id: str
    name: str
    store_id: str | None = None
    store_name: str | None = None
    total_sessions: int
    avg_score: float | None = None  # this week's avg score, None if no scored sessions
    current_streak: int


class OrgRollup(BaseModel):
    total_sessions: int
    avg_score: float | None = None  # mean of per-agent avg_score, None if no scored agents
    active_agent_count: int  # agents with at least one completed session


class StoreStatsResponse(BaseModel):
    store_id: str
    store_name: str
    region: str
    rollup: OrgRollup
    leaderboard: list[AgentLeaderboardEntry]


class StoreSummary(BaseModel):
    store_id: str
    store_name: str
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
