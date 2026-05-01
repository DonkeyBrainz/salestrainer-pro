# Plan: Fix Report Card Issues + Add Session History

Three problems to address, split into focused PRs.

---

## PR 1: Fix transcript not rendering in report card

### Root Cause

The backend evaluate handler at `gemini_relay.py:467` closes the WebSocket with code 1000 after sending `evaluation_result`. On the frontend, `websocketService.handleClose()` fires with code 1000 (line 344), which sets state to DISCONNECTED. This triggers the `onclose` flow. While `useWebSocket.disconnect()` is not called directly by handleClose, the VoiceSession unmount cleanup at line 117-123 calls `disconnect()`, which calls `setMessages([])` at `useWebSocket.ts:190`, wiping the transcript before ReportCard can render.

Additionally, the `Transcript` component accumulates messages from real-time transcription chunks, but the `evaluation_result` message arrives on the WebSocket and the close happens in quick succession. Even if messages aren't explicitly cleared, the component may unmount before the overlay renders.

### Fix

**`frontend/src/hooks/useWebSocket.ts`**:
- Do NOT clear `messages` in `disconnect()`. Instead, only clear them when a new `connect()` is called.
- Move `setMessages([])` from `disconnect` to the beginning of `connect`.

This is safe because:
- `disconnect` is called on unmount (VoiceSession leaves the page) and the component tree is destroyed anyway.
- `disconnect` is called on "End Session" button, after which the user sees the DISCONNECTED welcome screen -- empty messages is fine since Transcript only renders when `isConnected || messages.length > 0`, and the welcome screen takes precedence.
- The important case: evaluate flow sends `evaluation_result` then closes the WS. Messages must survive for ReportCard.

### Files

| File | Change |
|------|--------|
| `frontend/src/hooks/useWebSocket.ts` | Move `setMessages([])` from `disconnect` to `connect` |

---

## PR 2: Improve evaluation accuracy (coach analysis detecting techniques)

### Root Cause

The evaluation scorecard is built from `stage_progress` (`coach_agent_service.py:215`), which is updated only by `_apply_stage_updates` based on what the LLM analyzer detected during real-time coaching turns. Several issues compound:

1. **Conversation history truncated to last 4 turns** (`prompts.py:165`): The analyzer only sees the last 4 exchanges when analyzing each message. If a non-business greet happened in the first message but the analyzer runs on message 5+, it won't see it.

2. **No evaluation-time re-analysis**: `generate_evaluation()` at `coach_agent_service.py:197` just reads the final `stage_progress` state. It never re-analyzes the full transcript. If real-time detection missed something, the evaluation misses it too.

3. **Per-turn analysis only**: Each `analyze_turn` call analyzes only the current salesperson message. Techniques that span multiple turns (rapport building over several exchanges) may not be detected on any single turn.

### Fix: Add a full-transcript re-analysis pass at evaluation time

Before building the scorecard, run a second LLM analysis pass over the full conversation transcript. This "evaluation analysis" prompt asks the LLM to review the entire conversation and identify all completed checklist items, overriding the real-time stage_progress where items were missed.

**`backend/app/agents/coach/prompts.py`**:
- Add `EVALUATION_ANALYSIS_PROMPT` template that takes the full transcript and asks for a comprehensive review of all stage items completed.

**`backend/app/agents/coach/analyzer.py`**:
- Add `analyze_full_transcript()` method that sends the full conversation to the LLM with the evaluation prompt. Returns the same `CoachAnalysis` structure.

**`backend/app/services/coach_agent_service.py`**:
- In `generate_evaluation()`, call `analyzer.analyze_full_transcript()` before building the scorecard.
- Merge the full-transcript results into `stage_progress`: if the re-analysis detects an item that real-time missed, mark it as completed.
- This ensures the scorecard reflects what actually happened, not just what was caught in real-time.

### Files

| File | Change |
|------|--------|
| `backend/app/agents/coach/prompts.py` | Add `EVALUATION_ANALYSIS_PROMPT` + `build_evaluation_prompt()` |
| `backend/app/agents/coach/analyzer.py` | Add `analyze_full_transcript()` method |
| `backend/app/services/coach_agent_service.py` | Call full-transcript analysis in `generate_evaluation()`, merge results into stage_progress |
| `backend/tests/unit/test_coach_agent_service.py` | Add test for full-transcript merge logic |

---

## PR 3: Add session history page with past reports

### Backend: REST endpoints for sessions and evaluations

**New file: `backend/app/api/sessions.py`**

Three authenticated endpoints:

1. `GET /api/v1/sessions` -- List user's past sessions
   - Uses `CurrentUserDep` for auth
   - Uses `SessionRepositoryDep` to call `list_by_user(user_id)`
   - Returns list of `SessionResponse` (session_id, type, status, difficulty, persona, started_at, ended_at, duration, message_count, grade, score)

2. `GET /api/v1/sessions/{session_id}/evaluation` -- Get evaluation for a session
   - Uses `CurrentUserDep` for auth
   - Uses `EvaluationRepositoryDep` to call `get_by_session_id(session_id)`
   - Returns full evaluation data (scorecard, strengths, improvements, etc.)
   - 404 if no evaluation exists

3. `GET /api/v1/sessions/{session_id}/transcript` -- Get transcript for a session
   - Uses `CurrentUserDep` for auth
   - Uses `TranscriptRepositoryDep` to call `get_by_session_id(session_id)`
   - Returns transcript messages
   - 404 if no transcript exists

**Modify: `backend/app/models/session.py`**
- Add `grade` and `score` fields to `SessionResponse` (currently missing, but present on `Session` model)
- Add `selected_persona` field to `SessionResponse`

**Modify: `backend/app/main.py`**
- Import and register the new sessions router

### Frontend: History page and navigation

**New file: `frontend/src/services/sessionService.ts`**
- `fetchSessions()`: GET /api/v1/sessions (authenticated)
- `fetchEvaluation(sessionId)`: GET /api/v1/sessions/{id}/evaluation
- `fetchTranscript(sessionId)`: GET /api/v1/sessions/{id}/transcript

**New file: `frontend/src/pages/HistoryPage.tsx`**
- Lists past sessions in a table/card layout
- Each row shows: date, mode (training/evaluation), persona, difficulty, duration, grade/score
- Clicking a row navigates to `/history/{sessionId}`

**New file: `frontend/src/pages/SessionDetailPage.tsx`**
- Fetches evaluation + transcript for a session
- Reuses `ReportCard` component (refactored to accept data as props, not just overlay)
- Shows transcript below or alongside the report

**Modify: `frontend/src/App.tsx`**
- Add `/history` route -> HistoryPage
- Add `/history/:sessionId` route -> SessionDetailPage

**Modify: `frontend/src/pages/HomePage.tsx`**
- Add a third card or link: "Session History" that navigates to `/history`

**Modify: `frontend/src/components/VoiceSession.tsx`**
- After evaluation completes and user clicks "Done" on ReportCard, navigate to `/history` or back to home (instead of just clearing)

### Frontend types

**Modify: `frontend/src/types/index.ts`**
- Add `SessionSummary` type matching backend `SessionResponse`
- Add `TranscriptMessage` type for transcript data

### Files

| File | Change |
|------|--------|
| `backend/app/api/sessions.py` | New: 3 REST endpoints |
| `backend/app/models/session.py` | Add grade/score/persona to SessionResponse |
| `backend/app/main.py` | Register sessions router |
| `backend/tests/unit/test_sessions_api.py` | New: endpoint tests |
| `frontend/src/services/sessionService.ts` | New: API client functions |
| `frontend/src/types/index.ts` | Add SessionSummary, TranscriptMessage types |
| `frontend/src/pages/HistoryPage.tsx` | New: session list page |
| `frontend/src/pages/SessionDetailPage.tsx` | New: session detail with report + transcript |
| `frontend/src/App.tsx` | Add /history routes |
| `frontend/src/pages/HomePage.tsx` | Add session history card |
| `frontend/src/components/ReportCard.tsx` | Refactor to work as both overlay and inline |

---

## Execution Order

1. **PR 1** (transcript fix) -- single-line move, no risk, immediate fix
2. **PR 2** (evaluation accuracy) -- backend-only, improves scoring
3. **PR 3** (session history) -- largest scope, full-stack feature
