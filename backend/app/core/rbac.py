"""Role-based access control for store/regional/national visibility.

Extends the ad-hoc admin-email allowlist in app.api.admin with a data-driven
role system (User.role / store_id / region) for managers and regional
directors viewing their own org's performance.
"""

from typing import Annotated

from fastapi import Depends

from app.core.dependencies import CurrentUserDep, StoreRepositoryDep
from app.core.exceptions import ForbiddenError
from app.models.user import User


async def require_manager_or_above(user: CurrentUserDep) -> User:
    """Verify user has manager, regional_director, or admin privileges.

    Raises:
        ForbiddenError: If user is a plain agent.
    """
    from app.api.admin import ADMIN_EMAILS

    if user.role in ("manager", "regional_director") or user.email in ADMIN_EMAILS:
        return user
    raise ForbiddenError("Manager access required")


async def get_visible_store_ids(
    user: Annotated[User, Depends(require_manager_or_above)],
    store_repository: StoreRepositoryDep,
) -> list[str]:
    """Resolve the set of store_ids the current user is allowed to view.

    - admin: every store
    - regional_director: every store in their region
    - manager: their own store only
    """
    from app.api.admin import ADMIN_EMAILS

    if user.email in ADMIN_EMAILS:
        stores = await store_repository.list_all()
        return [s.store_id for s in stores]

    if user.role == "regional_director":
        if not user.region:
            return []
        stores = await store_repository.list_by_region(user.region)
        return [s.store_id for s in stores]

    if user.role == "manager":
        return [user.store_id] if user.store_id else []

    return []


VisibleStoreIdsDep = Annotated[list[str], Depends(get_visible_store_ids)]
