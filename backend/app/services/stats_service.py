"""User stats computation service for dashboard metrics."""

from datetime import UTC, date, datetime, timedelta

from app.models.evaluation import Evaluation
from app.models.stats import COREStageStats, RecentSessionActivity, UserStatsResponse
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.session_repository import SessionRepository

CORE_STAGES = ["CONNECT", "OBSERVE", "RECOMMEND", "EXECUTE"]
WEEKLY_GOAL = 7
RECENT_ACTIVITY_LIMIT = 5
MASTERY_WINDOW_DAYS = 30


def _compute_streak(session_dates: list[date]) -> tuple[int, int]:
    """Compute current and longest streak from a list of session dates.

    A streak counts consecutive calendar days (UTC) with at least one session.
    A one-day grace period applies — a streak is still active if the last session
    was yesterday.

    Returns:
        (current_streak, longest_streak)
    """
    if not session_dates:
        return 0, 0

    unique_dates = sorted(set(session_dates))

    # Longest streak: single forward pass
    longest = 1
    run = 1
    for i in range(1, len(unique_dates)):
        if unique_dates[i] == unique_dates[i - 1] + timedelta(days=1):
            run += 1
            if run > longest:
                longest = run
        else:
            run = 1

    # Current streak: walk backwards from today (or yesterday as grace day)
    date_set = set(unique_dates)
    today = datetime.now(UTC).date()
    if today in date_set:
        anchor = today
    elif today - timedelta(days=1) in date_set:
        anchor = today - timedelta(days=1)
    else:
        return 0, longest

    current = 0
    check = anchor
    while check in date_set:
        current += 1
        check -= timedelta(days=1)

    return current, longest


async def get_user_stats(
    user_id: str,
    session_repository: SessionRepository,
    evaluation_repository: EvaluationRepository,
) -> UserStatsResponse:
    """Compute all dashboard stats for a user from Firestore session/evaluation data."""
    # Fetch raw data — both calls are independent
    all_sessions = await session_repository.list_all_completed_by_user(user_id)
    all_evaluations = await evaluation_repository.list_by_user(user_id, limit=200)

    # Build evaluation lookup for O(1) joins
    eval_by_session: dict[str, Evaluation] = {e.session_id: e for e in all_evaluations}

    # ── Streak ──────────────────────────────────────────────────────────────────
    session_dates = [s.started_at.date() for s in all_sessions]
    current_streak, longest_streak = _compute_streak(session_dates)

    # ── This week ───────────────────────────────────────────────────────────────
    now = datetime.now(UTC)
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    sessions_this_week = [s for s in all_sessions if s.started_at >= week_start]

    weekly_scores = [
        eval_by_session[s.session_id].final_score
        for s in sessions_this_week
        if s.session_id in eval_by_session
    ]
    avg_score_this_week = (
        round(sum(weekly_scores) / len(weekly_scores), 1) if weekly_scores else None
    )

    # ── CORE mastery ────────────────────────────────────────────────────────────
    cutoff_current = now - timedelta(days=MASTERY_WINDOW_DAYS)
    cutoff_previous = now - timedelta(days=MASTERY_WINDOW_DAYS * 2)

    current_evals = [e for e in all_evaluations if e.created_at >= cutoff_current]
    previous_evals = [
        e for e in all_evaluations if cutoff_previous <= e.created_at < cutoff_current
    ]

    core_mastery: list[COREStageStats] = []
    for stage in CORE_STAGES:
        current_scores = [
            e.scorecard.stage_scores[stage].score
            for e in current_evals
            if stage in e.scorecard.stage_scores
        ]
        prev_scores = [
            e.scorecard.stage_scores[stage].score
            for e in previous_evals
            if stage in e.scorecard.stage_scores
        ]

        current_avg = round(sum(current_scores) / len(current_scores), 1) if current_scores else 0.0
        prev_avg = round(sum(prev_scores) / len(prev_scores), 1) if prev_scores else None
        delta = round(current_avg - prev_avg, 1) if prev_avg is not None else None

        core_mastery.append(COREStageStats(stage=stage, mastery_pct=current_avg, delta=delta))

    # ── Recent activity ─────────────────────────────────────────────────────────
    # Last N sessions that have a scored evaluation
    scored = [s for s in all_sessions if s.session_id in eval_by_session][:RECENT_ACTIVITY_LIMIT]
    recent_activity: list[RecentSessionActivity] = []
    for s in scored:
        ev = eval_by_session[s.session_id]
        recent_activity.append(
            RecentSessionActivity(
                session_id=s.session_id,
                persona_name=s.selected_persona,
                started_at=s.started_at,
                score=round(ev.final_score) if ev.final_score is not None else None,
                grade=ev.grade.value if ev.grade is not None else None,
            )
        )

    return UserStatsResponse(
        current_streak=current_streak,
        longest_streak=longest_streak,
        sessions_this_week=len(sessions_this_week),
        weekly_goal=WEEKLY_GOAL,
        avg_score_this_week=avg_score_this_week,
        core_mastery=core_mastery,
        recent_activity=recent_activity,
        total_sessions=len(all_sessions),
    )
