# Plan: Populate Dashboard Stats with Real User Data

## Context

The `design_handoff_sales_trainer/arena.jsx` prototype shows a stats panel with hardcoded values (14-day streak, 5/7 sessions, CORE mastery percentages, recent activity). The production frontend (`frontend/`) has none of this — the `HomePage.tsx` is just 3 mode cards with no user progress data. This plan wires real data from Firestore into those dashboard widgets.

All session and evaluation data already exists in Firestore; we just need to compute aggregates (streak, weekly counts, per-stage averages, delta trends) and expose them through a new endpoint.

---

## What Gets Built

### Backend: 4 files touched/created

**1. `backend/app/models/stats.py`** _(new)_

```python
class COREStageStats(BaseModel):
    stage: str          # "CONNECT" | "OBSERVE" | "RECOMMEND" | "EXECUTE"
    mastery_pct: float  # average stage score across last 30 days (0–100)
    delta: float | None # vs previous 30 days; None if insufficient history

class RecentSessionActivity(BaseModel):
    session_id: str
    persona_name: str | None
    started_at: datetime
    score: int | None
    grade: str | None

class UserStatsResponse(BaseModel):
    current_streak: int
    longest_streak: int
    sessions_this_week: int
    weekly_goal: int            # hardcoded 7 for now
    avg_score_this_week: float | None
    core_mastery: list[COREStageStats]  # always 4 entries, ordered C-O-R-E
    recent_activity: list[RecentSessionActivity]  # last 4 scored sessions
    total_sessions: int
```

**2. `backend/app/repositories/session_repository.py`** _(add one method)_

Add `list_all_completed_by_user(user_id: str) -> list[Session]`:
- Queries Firestore `where user_id == X`, filters to `COMPLETED` + `is_deleted=False` in Python (consistent with existing pattern — avoids composite index).

**3. `backend/app/services/stats_service.py`** _(new)_

Single function `get_user_stats(user_id, session_repo, evaluation_repo) -> UserStatsResponse`:

- **Streak**: fetch all completed sessions → extract `.started_at.date()` → count consecutive calendar days backwards from today (or yesterday as grace day). Also compute `longest_streak` in a single pass.
- **This week**: count completed sessions with `started_at >= Monday 00:00 UTC` of current week.
- **Avg score this week**: average the `final_score` from matching evaluations (using an `eval_by_session_id` dict built from `evaluation_repo.list_by_user(user_id, limit=200)`).
- **CORE mastery**: from all evaluations, split into current 30d vs previous 30d windows. Average `scorecard.stage_scores[stage].score` per stage per window. Delta = current_avg − prev_avg (None if no previous data).
- **Recent activity**: last 4 completed sessions that have an evaluation; pull persona, timestamp, score, grade from joined data.

**4. `backend/app/api/users.py`** _(new)_

```python
router = APIRouter(prefix="/api/v1/users")

@router.get("/me/stats", response_model=UserStatsResponse)
async def get_my_stats(
    current_user: CurrentUserDep,
    session_repository: SessionRepositoryDep,
    evaluation_repository: EvaluationRepositoryDep,
) -> UserStatsResponse:
    return await get_user_stats(current_user.user_id, session_repository, evaluation_repository)
```

Register in `backend/app/main.py` (import + `app.include_router(users_router, tags=["Users"])`).

---

### Frontend: 4 files touched/created

**5. `frontend/src/types/stats.ts`** _(new)_

TypeScript interfaces mirroring the backend response models.

**6. `frontend/src/services/statsService.ts`** _(new)_

```ts
export async function fetchUserStats(accessToken: string): Promise<UserStatsResponse>
```
Follows the same pattern as `sessionService.ts` (uses `VITE_API_BASE_URL`).

**7. `frontend/src/components/UserStatsDashboard.tsx`** _(new)_

Renders real data from `UserStatsResponse` with the Arena visual language (adapted to Tailwind):
- **Streak card**: count + "days" label + dot row (7 dots, filled = days this week had sessions) + footnote
- **This week card**: `sessions_this_week / weekly_goal` + mini bar chart for the 7-day window + avg score footnote
- **CORE mastery**: 4 skill bars (C/O/R/E) with fill width = `mastery_pct`, delta badge colored green/red/gray
- **Recent activity**: last 4 rows — persona name, relative time, score chip (color by grade: A→green, B→sage, C→yellow, D/F→red)
- Shows skeleton/loading state while fetching; shows nothing (no empty state flash) if zero sessions yet

**8. `frontend/src/pages/HomePage.tsx`** _(modify)_

Add `<UserStatsDashboard />` above the 3 mode cards. Fetch stats with `useEffect` + `useState` using the auth token from `useAuth()`. Two-column layout on large screens: stats panel left, mode cards right.

---

### Tests

**`backend/tests/unit/services/test_stats_service.py`** _(new)_

Unit tests (pure Python, no Firestore) for:
- Streak: zero sessions → 0/0, consecutive days → correct count, gap in middle → streak resets, yesterday-only → streak = 1
- Longest streak computed correctly across multi-gap history
- Weekly sessions: sessions before Monday don't count
- CORE mastery delta: None when no previous period data; correct sign when previous data exists

---

## Critical Files

| File | Action |
|------|--------|
| `backend/app/models/stats.py` | Create |
| `backend/app/services/stats_service.py` | Create |
| `backend/app/api/users.py` | Create |
| `backend/app/repositories/session_repository.py` | Add method |
| `backend/app/main.py` | Add import + include_router |
| `frontend/src/types/stats.ts` | Create |
| `frontend/src/services/statsService.ts` | Create |
| `frontend/src/components/UserStatsDashboard.tsx` | Create |
| `frontend/src/pages/HomePage.tsx` | Modify |

---

## Verification

1. `cd backend && uv run pytest tests/unit/services/test_stats_service.py -v`
2. `cd backend && uv run pytest` — full suite green
3. `cd backend && uv run mypy app/` — no type errors
4. `cd backend && uv run ruff check .` — lint clean
5. `GET /api/v1/users/me/stats` with valid auth token → correct shape
6. Frontend: log in → stats panel shows real values
7. Complete a session → dashboard updates
