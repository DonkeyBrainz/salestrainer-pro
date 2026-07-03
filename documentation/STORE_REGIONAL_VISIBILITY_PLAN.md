# Manager/Regional/National Visibility for Agent Performance

## Context

SalesTrainer Pro currently only supports a single-user view: `GET /api/v1/users/me/stats` computes streak/weekly/CORE-mastery/recent-activity for the authenticated agent from their own `sessions` + `evaluations` Firestore docs (`backend/app/services/stats_service.py`). There is no concept of stores, regions, or roles anywhere in the codebase — the `User` model (`backend/app/models/user.py`) has only `email`/`name`/`preferences`, and the only access-control precedent is a hardcoded admin-email allowlist in `backend/app/api/admin.py`.

The user wants store managers and regional directors to see how "their" agents are performing, plus a national rollup — modeled on a real org: 3 TX stores (Houston, Dallas, Austin), 7 NC stores (incl. Kinston), 2 SC stores (12 stores total), each with up to 8 agents + 2 managers.

Decisions confirmed with the user:
- **Role model**: 3-tier role field (`agent` / `manager` / `regional_director`) on `User`; national/org-wide view reuses the existing admin allowlist.
- **Store management**: one-time seed script for the 12 fixed stores, no CRUD API for now.
- **Rollup content**: leaderboard + aggregate stats (not aggregate-only).

## Data Model Changes

**`backend/app/models/user.py`** — add to `User` (and `UserCreate`/Firestore doc):
```python
role: Literal["agent", "manager", "regional_director"] = "agent"
store_id: str | None = None   # required for agent/manager
region: str | None = None     # required for regional_director; derived from store for agent/manager via the stores lookup, not stored redundantly on the user doc
```
National/org-wide visibility reuses the existing `require_admin` (admin-email allowlist) rather than adding a 4th role — revisit if a non-technical "national director" business role is wanted later.

**New `stores` Firestore collection** (new `backend/app/models/store.py` + `backend/app/repositories/store_repository.py`, following the existing repository pattern in `user_repository.py`/`session_repository.py`):
```python
class Store(BaseModel):
    store_id: str
    name: str          # "Houston", "Kinston"
    region: str         # "TX", "NC", "SC"
```
Seeded once via a scratchpad script (not a repo script) for the 12 fixed stores — no CRUD API for now (revisit if the store roster changes often).

**Denormalize `store_id` onto `Session` documents at creation time** (`backend/app/repositories/session_repository.py::create`, `backend/app/models/session.py`): look up the creating user's `store_id` and stamp it onto the session doc. This is the key design choice — it lets store/region rollups query `sessions.where("store_id", "in", [...])` directly instead of fanning out per-user queries, and mirrors how `evaluations` already joins back to `sessions` via `session_id` in `stats_service.py`. Region rollups then query for all `store_id`s in that region (TX has 3, NC has 7, SC has 2 — all well under Firestore's 30-value `in`-query limit); national queries all 12.

**New Firestore composite indexes** (`terraform/firestore.tf`, following the pattern just added for `evaluations_user_created`):
- `sessions`: `store_id` ASC + `started_at` DESC (for store/region rollup queries ordered by recency)
- Confirm whether `evaluations` also needs a `session_id`-based lookup at scale, or whether the existing per-session `get_by_session_id` join (already used in `stats_service.py`) is fine for the expected volume (~12 stores × 10 people × handful of sessions/day — small enough that in-memory joins after an `in`-query are fine, no new evaluations index needed).

Apply via scoped `terraform plan -target=... && terraform apply <planfile>` per this repo's standing rule — never a blanket apply.

## RBAC

**New `backend/app/core/rbac.py`** (or extend `dependencies.py`), following the `require_admin` pattern in `admin.py`:
- `require_manager_or_above(user) -> User`: role must be `manager` or `regional_director`, or fall back to `require_admin`'s allowlist.
- A scope resolver, e.g. `get_visible_store_ids(user, store_repository) -> list[str]`: agent → `[]` (no rollup access), manager → `[user.store_id]`, regional_director → all `store_id`s in `user.region`, admin → all stores.

## New Aggregation Service

**New `backend/app/services/org_stats_service.py`**, sibling to `stats_service.py`, reusing its math (grade thresholds, `CORE_STAGES`, averaging patterns) but grouped:
- `get_store_stats(store_id, session_repository, evaluation_repository, user_repository) -> StoreStatsResponse`
- `get_region_stats(region, store_repository, ...) -> RegionStatsResponse` (aggregates per-store, plus a store-by-store breakdown)
- `get_national_stats(...)` (aggregates per-region, plus region-by-region breakdown)

Each level returns, per the "leaderboard + aggregate" decision: total sessions, avg score, active-agent count, and a per-agent leaderboard (name, sessions, avg score, current streak) sorted by avg score descending. Region view nests store breakdowns; national nests region breakdowns.

New response models in `backend/app/models/stats.py` (or a new `org_stats.py`): `AgentLeaderboardEntry`, `StoreStatsResponse`, `RegionStatsResponse`, `NationalStatsResponse` — mirroring the camelCase-alias convention already used in `UserStatsResponse`/`UserMetricsResponse`.

## New API Endpoints

New `backend/app/api/organizations.py` (registered in `main.py` alongside the other routers):
- `GET /api/v1/stores/{store_id}/stats` — `require_manager_or_above`, 403 if requester's visible store_ids don't include `store_id`
- `GET /api/v1/regions/{region}/stats` — same guard, region-scoped
- `GET /api/v1/organization/stats` — admin-only (national rollup)
- `GET /api/v1/stores` — list stores (for a manager/director's own UI navigation; filtered to visible scope)

## Frontend (follow-up, not detailed here)

A new dashboard view analogous to `UserStatsDashboard.tsx` but rendering the leaderboard + store/region breakdown; out of scope for this plan unless requested — flagged as a likely next step once the backend is in place.

## Verification

1. `uv run pytest` — add unit tests for `org_stats_service` (store/region/national aggregation math) and RBAC scope resolution (agent gets 403, manager sees only their store, regional director sees their region's stores, admin sees all).
2. `uv run mypy app/` and `uv run ruff check .` clean.
3. Manually seed 2-3 test users with `manager`/`regional_director` roles plus a couple of stores, verify `GET /api/v1/stores/{id}/stats` and `/regions/{region}/stats` against real Firestore data (reusing the existing seeded demo sessions from the previous conversation where possible).
4. Confirm the new `sessions` composite index reaches `READY` and is actually query-usable (per the `project_terraform_state_drift` memory caveat: `READY` in `gcloud firestore indexes composite list` doesn't guarantee immediate usability — poll with a real query before declaring done).
