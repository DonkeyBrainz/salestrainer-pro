"""Unit tests for stats_service computation logic."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.stats import UserStatsResponse
from app.services.stats_service import _compute_streak, get_user_stats

# =============================================================================
# _compute_streak
# =============================================================================


class TestComputeStreak:
    def test_no_sessions(self) -> None:
        current, longest = _compute_streak([])
        assert current == 0
        assert longest == 0

    def test_single_session_today(self) -> None:
        today = datetime.now(UTC).date()
        current, longest = _compute_streak([today])
        assert current == 1
        assert longest == 1

    def test_single_session_yesterday_grace(self) -> None:
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        current, longest = _compute_streak([yesterday])
        assert current == 1
        assert longest == 1

    def test_single_session_two_days_ago_no_streak(self) -> None:
        two_days_ago = datetime.now(UTC).date() - timedelta(days=2)
        current, longest = _compute_streak([two_days_ago])
        assert current == 0
        assert longest == 1

    def test_consecutive_days_including_today(self) -> None:
        today = datetime.now(UTC).date()
        dates = [today - timedelta(days=i) for i in range(5)]
        current, longest = _compute_streak(dates)
        assert current == 5
        assert longest == 5

    def test_gap_resets_current_streak(self) -> None:
        today = datetime.now(UTC).date()
        # Sessions today and 3 days ago but not yesterday or 2 days ago
        dates = [today, today - timedelta(days=3)]
        current, longest = _compute_streak(dates)
        assert current == 1
        assert longest == 1

    def test_longest_streak_separate_from_current(self) -> None:
        today = datetime.now(UTC).date()
        # Longer streak 2 weeks ago, but broken. Only yesterday + today active.
        old_streak = [today - timedelta(days=14 + i) for i in range(7)]
        recent = [today, today - timedelta(days=1)]
        current, longest = _compute_streak(old_streak + recent)
        assert current == 2
        assert longest == 7

    def test_duplicate_dates_collapsed(self) -> None:
        today = datetime.now(UTC).date()
        # Multiple sessions on same day count as one
        dates = [today, today, today - timedelta(days=1), today - timedelta(days=1)]
        current, longest = _compute_streak(dates)
        assert current == 2
        assert longest == 2

    def test_streak_only_yesterday(self) -> None:
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        prior = yesterday - timedelta(days=1)
        current, longest = _compute_streak([yesterday, prior])
        assert current == 2
        assert longest == 2


# =============================================================================
# get_user_stats (integration with mocked repos)
# =============================================================================


class MockSession:
    def __init__(
        self,
        session_id: str,
        started_at: datetime,
        selected_persona: str | None = None,
    ) -> None:
        self.session_id = session_id
        self.started_at = started_at
        self.selected_persona = selected_persona


class MockStageScore:
    def __init__(self, score: float) -> None:
        self.score = score


class MockScorecard:
    def __init__(self, stage_scores: dict[str, MockStageScore]) -> None:
        self.stage_scores = stage_scores


class MockGrade:
    def __init__(self, value: str) -> None:
        self.value = value


class MockEvaluation:
    def __init__(
        self,
        session_id: str,
        created_at: datetime,
        final_score: float,
        grade_value: str,
        stage_scores: dict[str, float] | None = None,
    ) -> None:
        self.session_id = session_id
        self.created_at = created_at
        self.final_score = final_score
        self.grade = MockGrade(grade_value)
        scores = stage_scores or {"CONNECT": 80.0, "OBSERVE": 70.0, "RECOMMEND": 60.0, "EXECUTE": 50.0}
        self.scorecard = MockScorecard({k: MockStageScore(v) for k, v in scores.items()})


class MockSessionRepo:
    def __init__(self, sessions: list[MockSession]) -> None:
        self._sessions = sessions

    async def list_all_completed_by_user(self, user_id: str) -> list[MockSession]:
        return self._sessions


class MockEvalRepo:
    def __init__(self, evaluations: list[MockEvaluation]) -> None:
        self._evaluations = evaluations

    async def list_by_user(self, user_id: str, limit: int = 50) -> list[MockEvaluation]:
        return self._evaluations


@pytest.mark.asyncio
class TestGetUserStats:
    async def test_empty_user(self) -> None:
        result = await get_user_stats("u1", MockSessionRepo([]), MockEvalRepo([]))  # type: ignore[arg-type]
        assert isinstance(result, UserStatsResponse)
        assert result.current_streak == 0
        assert result.longest_streak == 0
        assert result.sessions_this_week == 0
        assert result.total_sessions == 0
        assert result.avg_score_this_week is None
        assert len(result.core_mastery) == 4
        assert all(s.mastery_pct == 0.0 for s in result.core_mastery)
        assert all(s.delta is None for s in result.core_mastery)

    async def test_weekly_sessions_counted(self) -> None:
        now = datetime.now(UTC)
        monday = now - timedelta(days=now.weekday())
        # 2 sessions this week, 1 last week
        sessions = [
            MockSession("s1", monday + timedelta(hours=1)),
            MockSession("s2", monday + timedelta(hours=10)),
            MockSession("s3", monday - timedelta(days=7)),
        ]
        result = await get_user_stats("u1", MockSessionRepo(sessions), MockEvalRepo([]))  # type: ignore[arg-type]
        assert result.sessions_this_week == 2
        assert result.total_sessions == 3

    async def test_core_mastery_averages(self) -> None:
        now = datetime.now(UTC)
        evals = [
            MockEvaluation("s1", now - timedelta(days=1), 80.0, "B", {"CONNECT": 90.0, "OBSERVE": 70.0, "RECOMMEND": 60.0, "EXECUTE": 50.0}),
            MockEvaluation("s2", now - timedelta(days=5), 70.0, "C", {"CONNECT": 80.0, "OBSERVE": 80.0, "RECOMMEND": 70.0, "EXECUTE": 60.0}),
        ]
        result = await get_user_stats("u1", MockSessionRepo([]), MockEvalRepo(evals))  # type: ignore[arg-type]
        connect = next(s for s in result.core_mastery if s.stage == "CONNECT")
        assert connect.mastery_pct == 85.0  # avg of 90 and 80
        assert connect.delta is None  # no previous period data

    async def test_core_mastery_delta_computed(self) -> None:
        now = datetime.now(UTC)
        # Current period (within 30 days)
        current_evals = [
            MockEvaluation("s1", now - timedelta(days=5), 80.0, "B", {"CONNECT": 80.0, "OBSERVE": 70.0, "RECOMMEND": 60.0, "EXECUTE": 50.0}),
        ]
        # Previous period (31-60 days ago)
        prev_evals = [
            MockEvaluation("s2", now - timedelta(days=45), 60.0, "D", {"CONNECT": 60.0, "OBSERVE": 50.0, "RECOMMEND": 40.0, "EXECUTE": 30.0}),
        ]
        result = await get_user_stats("u1", MockSessionRepo([]), MockEvalRepo(current_evals + prev_evals))  # type: ignore[arg-type]
        connect = next(s for s in result.core_mastery if s.stage == "CONNECT")
        assert connect.mastery_pct == 80.0
        assert connect.delta == 20.0  # 80 - 60

    async def test_recent_activity_uses_evaluation_scores(self) -> None:
        now = datetime.now(UTC)
        sessions = [MockSession("s1", now - timedelta(hours=1), "Jennifer")]
        evals = [MockEvaluation("s1", now - timedelta(hours=1), 91.0, "A")]
        result = await get_user_stats("u1", MockSessionRepo(sessions), MockEvalRepo(evals))  # type: ignore[arg-type]
        assert len(result.recent_activity) == 1
        assert result.recent_activity[0].score == 91
        assert result.recent_activity[0].grade == "A"
        assert result.recent_activity[0].persona_name == "Jennifer"

    async def test_recent_activity_limited_to_four(self) -> None:
        now = datetime.now(UTC)
        sessions = [MockSession(f"s{i}", now - timedelta(hours=i), f"Persona{i}") for i in range(6)]
        evals = [MockEvaluation(f"s{i}", now - timedelta(hours=i), 75.0, "C") for i in range(6)]
        result = await get_user_stats("u1", MockSessionRepo(sessions), MockEvalRepo(evals))  # type: ignore[arg-type]
        assert len(result.recent_activity) == 4
