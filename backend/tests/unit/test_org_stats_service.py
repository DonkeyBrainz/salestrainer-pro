"""Unit tests for org_stats_service (store/regional/national rollups)."""

from datetime import UTC, datetime

import pytest

from app.core.exceptions import NotFoundError
from app.models.stats import UserStatsResponse
from app.models.store import Store
from app.models.user import User
from app.services import org_stats_service


def make_user(user_id: str, name: str, store_id: str) -> User:
    return User(
        user_id=user_id,
        email=f"{user_id}@example.com",
        name=name,
        role="agent",
        store_id=store_id,
        created_at=datetime.now(UTC),
    )


def make_stats(total_sessions: int, avg_score: float | None, streak: int) -> UserStatsResponse:
    return UserStatsResponse(
        current_streak=streak,
        longest_streak=streak,
        sessions_this_week=total_sessions,
        weekly_goal=7,
        avg_score_this_week=avg_score,
        core_mastery=[],
        recent_activity=[],
        total_sessions=total_sessions,
    )


ALL_STORES = [
    Store(store_id="houston", name="Houston", region="TX"),
    Store(store_id="dallas", name="Dallas", region="TX"),
    Store(store_id="kinston", name="Kinston", region="NC"),
]

USERS_BY_STORE = {
    "houston": [make_user("u1", "Alice", "houston"), make_user("u2", "Bob", "houston")],
    "dallas": [make_user("u3", "Carl", "dallas")],
    "kinston": [make_user("u4", "Dana", "kinston")],
}

STATS_BY_USER = {
    "u1": make_stats(total_sessions=5, avg_score=90.0, streak=3),
    "u2": make_stats(total_sessions=0, avg_score=None, streak=0),
    "u3": make_stats(total_sessions=2, avg_score=70.0, streak=1),
    "u4": make_stats(total_sessions=4, avg_score=80.0, streak=2),
}


class MockStoreRepo:
    async def get_by_id(self, store_id: str) -> Store | None:
        return next((s for s in ALL_STORES if s.store_id == store_id), None)

    async def list_all(self) -> list[Store]:
        return ALL_STORES

    async def list_by_region(self, region: str) -> list[Store]:
        return [s for s in ALL_STORES if s.region == region]


class MockUserRepo:
    async def list_by_store_ids(self, store_ids: list[str]) -> list[User]:
        users: list[User] = []
        for store_id in store_ids:
            users.extend(USERS_BY_STORE.get(store_id, []))
        return users


@pytest.fixture(autouse=True)
def patch_get_user_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_user_stats(
        user_id: str, session_repository: object, evaluation_repository: object
    ) -> UserStatsResponse:
        return STATS_BY_USER[user_id]

    monkeypatch.setattr(org_stats_service, "get_user_stats", fake_get_user_stats)


class TestGetStoreStats:
    async def test_leaderboard_sorted_by_avg_score(self) -> None:
        result = await org_stats_service.get_store_stats(
            "houston",
            MockStoreRepo(),
            MockUserRepo(),
            object(),
            object(),  # type: ignore[arg-type]
        )
        assert result.store_name == "Houston"
        assert result.region == "TX"
        assert [e.user_id for e in result.leaderboard] == ["u1", "u2"]

    async def test_rollup_aggregates_sessions_and_active_count(self) -> None:
        result = await org_stats_service.get_store_stats(
            "houston",
            MockStoreRepo(),
            MockUserRepo(),
            object(),
            object(),  # type: ignore[arg-type]
        )
        assert result.rollup.total_sessions == 5
        assert result.rollup.avg_score == 90.0  # only u1 has a score; u2 excluded
        assert result.rollup.active_agent_count == 1  # only u1 has sessions > 0

    async def test_unknown_store_raises_not_found(self) -> None:
        with pytest.raises(NotFoundError):
            await org_stats_service.get_store_stats(
                "nope",
                MockStoreRepo(),
                MockUserRepo(),
                object(),
                object(),  # type: ignore[arg-type]
            )


class TestGetRegionStats:
    async def test_combines_stores_in_region(self) -> None:
        result = await org_stats_service.get_region_stats(
            "TX",
            MockStoreRepo(),
            MockUserRepo(),
            object(),
            object(),  # type: ignore[arg-type]
        )
        assert {s.store_id for s in result.stores} == {"houston", "dallas"}
        assert result.rollup.total_sessions == 5 + 2
        # combined leaderboard sorted desc by avg score: u1 (90), u3 (70), u2 (None)
        assert [e.user_id for e in result.leaderboard] == ["u1", "u3", "u2"]

    async def test_unknown_region_raises_not_found(self) -> None:
        with pytest.raises(NotFoundError):
            await org_stats_service.get_region_stats(
                "ZZ",
                MockStoreRepo(),
                MockUserRepo(),
                object(),
                object(),  # type: ignore[arg-type]
            )


class TestGetNationalStats:
    async def test_combines_all_regions(self) -> None:
        result = await org_stats_service.get_national_stats(
            MockStoreRepo(),
            MockUserRepo(),
            object(),
            object(),  # type: ignore[arg-type]
        )
        assert {r.region for r in result.regions} == {"TX", "NC"}
        assert result.rollup.total_sessions == 5 + 2 + 4
        assert len(result.leaderboard) == 4
