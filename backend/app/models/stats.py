"""Pydantic models for user stats and dashboard data."""

from datetime import datetime

from pydantic import BaseModel


class COREStageStats(BaseModel):
    stage: str  # "CONNECT" | "OBSERVE" | "RECOMMEND" | "EXECUTE"
    mastery_pct: float  # average stage score across last 30 days (0–100)
    delta: float | None = None  # change vs previous 30 days; None if no prior data


class RecentSessionActivity(BaseModel):
    session_id: str
    persona_name: str | None = None
    started_at: datetime
    score: int | None = None
    grade: str | None = None


class UserStatsResponse(BaseModel):
    current_streak: int
    longest_streak: int
    sessions_this_week: int
    weekly_goal: int
    avg_score_this_week: float | None = None
    core_mastery: list[COREStageStats]
    recent_activity: list[RecentSessionActivity]
    total_sessions: int
