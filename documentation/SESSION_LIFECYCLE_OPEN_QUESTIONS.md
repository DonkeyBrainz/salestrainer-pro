# Session Lifecycle — Open Questions

**Status:** Resolved · **Raised:** 2026-07-15 · **Resolved:** 2026-07-16 · **Branch:** `feat/agent-hardening`
**Context:** A live practice session with the Jennifer persona on the deployed build did not appear
in session history. Root cause found and fixed; Q1–Q4 below were decided as part of the Voiceprint
frontend redesign's backend workstream (B1–B3).

---

## Background — why practice sessions vanished

A session is only ever stamped `COMPLETED` when the client explicitly asks for an evaluation:

```
frontend/src/components/VoiceSession.tsx:641
  onEvaluate={mode === AppMode.EVALUATION ? handleEvaluate : undefined}
```

Training mode passes `undefined`, so there is **no Finish & Eval affordance in live practice at
all**. `sendControl('evaluate')` never fires, `_conversation_ended_naturally` stays `False`
(`backend/app/api/ws/gemini_relay.py:532` is the only place it is set), and the websocket teardown
in the `finally` block (`gemini_relay.py:291`) persists the session through the status ternary at
`gemini_relay.py:1123`, which stamps it `ABANDONED`.

The history list then filtered those rows out — so the transcript, messages, and agent state
snapshot were all written to Firestore, but the session was invisible in the UI.

**Fixed 2026-07-15:** `list_by_user` and `list_by_user_with_pagination` in
`backend/app/repositories/session_repository.py` no longer exclude `ABANDONED`; they only exclude
deleted sessions. Full backend suite passes (741 passed, 7 skipped, 81% coverage). No test had
locked in the old filtering behavior.

---

## Q1 — The status chip will read "ABANDONED" on every practice session

`SessionCard.tsx:148` renders a status pill for any session where `status !== 'completed'`. Since
*every* training session is currently `abandoned`, that pill is now about to appear on every card in
history. It is accurate to the enum but reads like an error when it actually means "a normal
practice rep that nobody asked to grade."

Options:
- **Relabel in the UI** — map `abandoned` → "No eval" / "Practice". Cheap, cosmetic, no semantic change.
- **Fix at the source** — see Q2.

**Resolved 2026-07-16:** Fixed at the source (Q2), and the archive UI was rebuilt (Voiceprint
redesign, Phase 5) to drop the status chip entirely — `HistoryPage.tsx`'s session log table
communicates state through the Mode badge (Practice/Assessment) and Score column instead
(`—` for an unscored row). `SessionCard.tsx` and its status pill are no longer part of the archive
flow; the file is kept only because the internal `AdminPage.tsx` persona-QA view still uses it.

## Q2 — Should a training-mode disconnect be an "abandonment" at all?

Today `COMPLETED` really means *"the user waited for the evaluation"*, which is much narrower than
the word implies. A user who does a full, productive 20-minute roleplay and closes the tab is
recorded identically to one who drops out after ten seconds.

Deciding this touches `_persist_conversation` and the meaning of `SessionStatus`. It is the more
honest model but the bigger call. Possibly training sessions need their own terminal status, or
`ABANDONED` should be reserved for sessions below some message-count / duration floor.

**Resolved 2026-07-16 (Backend B1):** Went with the message-count floor. In
`gemini_relay.py:_persist_conversation`, a training-mode session that disconnects with
`>= MIN_MESSAGES_FOR_TRAINING_COMPLETION` (4) buffered messages is now stamped `COMPLETED`;
`ABANDONED` is reserved for genuine below-floor false starts. Evaluation mode is unchanged — it
still only completes via the explicit `evaluate` control, since ending an assessment without
grading really is an abandonment. No new terminal status was introduced. Regression-tested in
`tests/integration/test_websocket_endpoints.py::TestConversationPersistence::test_training_session_completes_with_enough_messages`.

The evaluation's grade/score are now also written back onto the session doc itself
(`SessionService.record_evaluation_result`, called right after `generate_evaluation` succeeds) —
archive list/detail reads still join against the evaluation repository at read time as before, but
`list_all_completed_by_user` (streaks/stats) reads the session doc directly, so this keeps that
path honest too.

## Q3 — Practice reps do not count toward streaks or dashboard stats

`list_all_completed_by_user` (`session_repository.py`) still requires `status == COMPLETED`, and it
feeds streak and dashboard stats computation. Given Q1/Q2 — that no training session is ever
`COMPLETED` — **live practice currently contributes nothing to a user's streak or stats.**

This was deliberately left unchanged when the history filter was fixed, because "should a practice
rep count as a rep" is a product question, not a bug. But it is very likely not the intended
behavior and should be resolved alongside Q2.

**Resolved 2026-07-16:** Direct consequence of the Q2 fix — training sessions that clear the
message floor are `COMPLETED`, so `list_all_completed_by_user` now picks them up automatically and
they count toward streaks and `core_mastery`/`avg_score_this_week` once graded. No change was
needed in `stats_service.py` itself, since it already joins against the evaluation repository
independently rather than trusting the session doc's own `grade`/`score` fields.

## Q4 — Should Training mode get a Finish & Eval affordance?

Independently of the status semantics: should live practice let the user opt into an evaluation at
the end? This is the feature-shaped version of the problem, and it would make `COMPLETED` reachable
from training mode for the first time.

**Resolved 2026-07-16:** No — decided against adding an explicit "Finish & Eval" control to Live
Practice. Training mode still ends purely by disconnect ("End session" in the Voiceprint UI); the
message-count floor from Q2 is what makes that disconnect land as `COMPLETED`. Training sessions
still get evaluated regardless — `_persist_conversation` unconditionally calls
`coach_agent_service.generate_evaluation(...)` whenever agent state exists, for both session modes
(verified in Backend B2) — so no user-facing affordance was needed to make grading happen; it was
already happening, it just wasn't being surfaced or counted correctly.

---

## Unverified

- **The Jennifer session was never confirmed present in Firestore.** The code path says it must be
  there with `status=abandoned`, but a read-only query against `salescoach-494901` was not run, so
  this remains inference rather than observation. Lower priority now that the root cause is fixed
  and covered by tests, but a query for sessions started in the last 48h (status, persona, message
  count) would still settle it definitively.
- Whether any *other* consumers rely on abandoned sessions being hidden from `list_by_user`. Only
  the two list methods were audited.
