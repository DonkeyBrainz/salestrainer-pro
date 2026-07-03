"""Store/regional/national visibility endpoints for managers and directors."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.admin import require_admin
from app.core.dependencies import (
    EvaluationRepositoryDep,
    SessionRepositoryDep,
    StoreRepositoryDep,
    UserRepositoryDep,
)
from app.core.exceptions import ForbiddenError
from app.core.rbac import VisibleStoreIdsDep, require_manager_or_above
from app.models.org_stats import (
    NationalStatsResponse,
    RegionStatsResponse,
    StoreListEntry,
    StoreStatsResponse,
)
from app.models.user import User
from app.services.org_stats_service import get_national_stats, get_region_stats, get_store_stats

router = APIRouter(prefix="/api/v1")


@router.get("/stores", response_model=list[StoreListEntry])
async def list_visible_stores(
    visible_store_ids: VisibleStoreIdsDep,
    store_repository: StoreRepositoryDep,
) -> list[StoreListEntry]:
    """List the stores the current manager/director/admin can view."""
    stores = await store_repository.list_all()
    visible = set(visible_store_ids)
    return [
        StoreListEntry(store_id=s.store_id, name=s.name, region=s.region)
        for s in stores
        if s.store_id in visible
    ]


@router.get("/stores/{store_id}/stats", response_model=StoreStatsResponse)
async def get_store_stats_endpoint(
    store_id: str,
    user: Annotated[User, Depends(require_manager_or_above)],
    visible_store_ids: VisibleStoreIdsDep,
    store_repository: StoreRepositoryDep,
    user_repository: UserRepositoryDep,
    session_repository: SessionRepositoryDep,
    evaluation_repository: EvaluationRepositoryDep,
) -> StoreStatsResponse:
    """Get rollup + agent leaderboard for a single store."""
    if store_id not in visible_store_ids:
        raise ForbiddenError("You do not have access to this store")

    return await get_store_stats(
        store_id, store_repository, user_repository, session_repository, evaluation_repository
    )


@router.get("/regions/{region}/stats", response_model=RegionStatsResponse)
async def get_region_stats_endpoint(
    region: str,
    user: Annotated[User, Depends(require_manager_or_above)],
    visible_store_ids: VisibleStoreIdsDep,
    store_repository: StoreRepositoryDep,
    user_repository: UserRepositoryDep,
    session_repository: SessionRepositoryDep,
    evaluation_repository: EvaluationRepositoryDep,
) -> RegionStatsResponse:
    """Get rollup + store breakdown + leaderboard for a region.

    Requires regional_director (of that region) or admin -- a store manager's
    visible_store_ids never covers a whole region, so they're rejected here.
    """
    region_stores = await store_repository.list_by_region(region)
    if not region_stores or not all(s.store_id in visible_store_ids for s in region_stores):
        raise ForbiddenError("You do not have access to this region")

    return await get_region_stats(
        region, store_repository, user_repository, session_repository, evaluation_repository
    )


@router.get("/organization/stats", response_model=NationalStatsResponse)
async def get_organization_stats_endpoint(
    admin: Annotated[User, Depends(require_admin)],
    store_repository: StoreRepositoryDep,
    user_repository: UserRepositoryDep,
    session_repository: SessionRepositoryDep,
    evaluation_repository: EvaluationRepositoryDep,
) -> NationalStatsResponse:
    """Get org-wide rollup + per-region breakdown + leaderboard (admin only)."""
    return await get_national_stats(
        store_repository, user_repository, session_repository, evaluation_repository
    )
