"""Unit tests for role-based access control (store/regional/national visibility)."""

from datetime import UTC, datetime

import pytest

from app.core.exceptions import ForbiddenError
from app.core.rbac import get_visible_store_ids, require_manager_or_above
from app.models.store import Store
from app.models.user import User


def make_user(**overrides: object) -> User:
    defaults: dict[str, object] = {
        "user_id": "u1",
        "email": "agent@example.com",
        "name": "Test Agent",
        "role": "agent",
        "store_id": None,
        "region": None,
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return User(**defaults)  # type: ignore[arg-type]


class MockStoreRepo:
    def __init__(self, stores: list[Store]) -> None:
        self._stores = stores

    async def list_all(self) -> list[Store]:
        return self._stores

    async def list_by_region(self, region: str) -> list[Store]:
        return [s for s in self._stores if s.region == region]


ALL_STORES = [
    Store(store_id="houston", name="Houston", region="TX"),
    Store(store_id="dallas", name="Dallas", region="TX"),
    Store(store_id="austin", name="Austin", region="TX"),
    Store(store_id="kinston", name="Kinston", region="NC"),
]


class TestRequireManagerOrAbove:
    async def test_agent_rejected(self) -> None:
        with pytest.raises(ForbiddenError):
            await require_manager_or_above(make_user(role="agent"))

    async def test_manager_allowed(self) -> None:
        user = make_user(role="manager", store_id="houston")
        result = await require_manager_or_above(user)
        assert result is user

    async def test_regional_director_allowed(self) -> None:
        user = make_user(role="regional_director", region="TX")
        result = await require_manager_or_above(user)
        assert result is user


class TestGetVisibleStoreIds:
    async def test_manager_sees_only_own_store(self) -> None:
        user = make_user(role="manager", store_id="houston")
        result = await get_visible_store_ids(user, MockStoreRepo(ALL_STORES))  # type: ignore[arg-type]
        assert result == ["houston"]

    async def test_manager_without_store_sees_nothing(self) -> None:
        user = make_user(role="manager", store_id=None)
        result = await get_visible_store_ids(user, MockStoreRepo(ALL_STORES))  # type: ignore[arg-type]
        assert result == []

    async def test_regional_director_sees_all_stores_in_region(self) -> None:
        user = make_user(role="regional_director", region="TX")
        result = await get_visible_store_ids(user, MockStoreRepo(ALL_STORES))  # type: ignore[arg-type]
        assert set(result) == {"houston", "dallas", "austin"}

    async def test_regional_director_without_region_sees_nothing(self) -> None:
        user = make_user(role="regional_director", region=None)
        result = await get_visible_store_ids(user, MockStoreRepo(ALL_STORES))  # type: ignore[arg-type]
        assert result == []

    async def test_admin_sees_every_store(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.api.admin.ADMIN_EMAILS", ["boss@example.com"])
        user = make_user(role="agent", email="boss@example.com")
        result = await get_visible_store_ids(user, MockStoreRepo(ALL_STORES))  # type: ignore[arg-type]
        assert set(result) == {"houston", "dallas", "austin", "kinston"}
