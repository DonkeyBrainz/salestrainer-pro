# Agentic Engineering Deep Dive

> **Audience:** AI engineers studying or defending this system's design.
> **Ground truth:** every claim below is traceable to a file in `backend/app/`. When docs and code disagree, the code wins.
> **Last verified against code:** 2026-07-02

---

## 1. The Honest Architecture

Marketing version: "two LangGraph agents power the roleplay." Engineering version: there are **three separate LLM surfaces**, and only one of them is on the audio path.

| Surface | Model (config key) | Invoked | Output used for | Latency budget |
|---|---|---|---|---|
| **Live voice persona** | `gemini_live_model` (native-audio Live API), temp 0.5 | Continuous bidirectional stream | The actual roleplay the user hears | Real-time; nothing else may block it |
| **Customer agent graph** (LangGraph) | `gemini_model` (2.5 Flash) | Once per salesperson turn | Mood/regard **analytics only** | Off audio path, fire-and-forget |
| **Coach analyzer** | `coach_model` (2.5 Flash), temp 0.1 | Once per salesperson turn (throttled) | Stage checklist, hints, evaluation input | Off audio path, throttled to ≥10s |

The critical, non-obvious fact (`app/agents/prompts.py`, `gemini_relay.py`):

- The live persona's behavior is governed **entirely by one system prompt** built by `build_customer_prompt()` and passed to `connect_live()` at connect time. It is never injected mid-session; since 2026-07-05 it *is* rebuilt from current agent state on reconnect (`_current_system_instruction()`), so a resumed session gets fresh mood/objection context.
- The LangGraph `CustomerAgentGraph` *does* run every turn — but in voice mode its text-generation node is **skipped entirely** (the relay passes `generate_response=False`; before 2026-07-05 the reply was generated and discarded), and its updated mood is **never pushed back** into the live Gemini session. The mood machine feeds only the post-session analytics snapshot.

**Why this is a strong design, not an accident:** the Gemini Live API owns the conversation loop; injecting per-turn state would require either a text-turn nudge (audible artifact risk) or reconnect-with-new-prompt (latency spike, resumption complexity). Instead, dynamism is delegated to the prompt itself — rule 2 of `CUSTOMER_SYSTEM_PROMPT` instructs the model to shift mood in response to treatment ("Rudeness... you are genuinely offended... A real customer never rewards someone who insults them with a sale"). The model performs the mood arc; the state machine measures it. One mechanism acts, the other audits.

**Consequence for maintainers:** to change what the live customer *does*, edit `prompts.py`. To change what the post-session report *says*, edit `_analyze_input` / `_update_mood` in `customer_agent.py`. Fixing one never fixes the other.

---

## 2. The Customer Agent Graph (LangGraph)

`app/agents/customer_agent.py` — a five-node `StateGraph` over `CustomerAgentState`:

```
START → analyze_input → update_mood → check_objection ─┬─(inject)──→ inject_objection ─┐
                                                       └─(respond)─────────────────────┴→ generate_response → END
```

Design fingerprint: **deterministic rules everywhere except the final node.** Only `generate_response` calls an LLM. Everything upstream is keyword matching, enum arithmetic, and seeded-by-config probability:

- `_analyze_input`: regex/keyword detection of greeting, question, pushiness, concern-acknowledgment, and disrespect (whole-word insult set + phrase list — whole-word matching specifically to avoid "hello"→"hell" false positives).
- `_update_mood`: moves `Mood` along a 5-step ladder (`FRUSTRATED → ... → READY_TO_BUY`) with per-difficulty tuning from `DIFFICULTY_CONFIG` (`state.py`). Disrespect is a two-step drop plus a regard hit, deliberately overriding any concurrent positive signal.
- `_route_objection`: conditional edge. Deterministic early injection (turns 2–4 for medium/low/no-regard personas), then probabilistic behavior-responsive injection gated on negative mood (20%→70% by difficulty).
- `_inject_objection`: difficulty decides *which* objection — hard personas draw the hardest pending objection first (`objection_priority: "hardest"`).

**Difficulty as data, not prompts.** `DIFFICULTY_CONFIG` is a plain dict: `mood_improve_chance`, `mood_worsen_steps`, `mood_decay_chance`, `objection_inject_chance`, `objection_priority`. Four difficulty tiers are four rows of numbers.

**Why rules + LLM-at-the-edge beats LLM-everywhere here:**

1. **Reproducible difficulty.** "No-regard customers resist mood improvement 70% of the time" is a testable spec. An LLM judging its own mood cannot be tuned to a number, and difficulty calibration is the product's core promise (a training curriculum must be *consistently* hard).
2. **Zero added latency/cost** on the analysis path. Mood updates are microseconds, not model calls; the graph already spends its one LLM call on response generation.
3. **Unit-testable without mocks doing the thinking.** The mood ladder, decay, and objection routing have exact expected outputs.
4. **Auditable failure.** When a customer sours unexpectedly, you read a keyword list, not a chain-of-thought.

The accepted cost: keyword detection is brittle (sarcasm, indirect rudeness, and creative insults pass through). That's acceptable because this signal only feeds analytics — the *live* reaction to nuanced disrespect is handled by the LLM through the prompt, which is exactly the layer that's good at nuance.

---

## 3. Memory: Four Tiers, Each Scoped Deliberately

There is no single "memory." There are four, with different owners and lifetimes:

| Tier | What | Where | Lifetime | Loss impact |
|---|---|---|---|---|
| 1. Gemini Live server-side context | Audio conversation state | Google's side, referenced by **resumption handle** | Session + reconnect window | Voice loses conversational context; mitigated by resumption |
| 2. LangGraph checkpoint | `CustomerAgentState` per `thread_id` (= session_id) | `MemorySaver` — **in-process RAM** | Process lifetime | Mood/objection trajectory resets; roleplay unaffected |
| 3. Relay instance buffers | `_message_buffer`, `_agent_state`, pending transcriptions, `_analysis_cache`, `_resumption_handle` | `GeminiWebSocketRelay` object | WebSocket connection | Transcript gap if crash before persist |
| 4. Firestore | `sessions`, `transcripts` (+ per-message `internal_reasoning`), `evaluations`, serialized agent-state snapshot | Durable | Forever | Actual data loss |

Key mechanics:

- **Resumption handles** (`gemini_relay.py`): Gemini Live periodically emits `session_resumption_update`; the relay stores the latest handle and, on Gemini-side disconnect, reconnects with it — the *voice model's* memory survives the reconnect even though the system prompt is not rebuilt. Client sees a `session_resumed` event.
- **Write-at-end persistence**: `_persist_conversation()` flushes the message buffer and agent-state snapshot to Firestore at evaluation or disconnect — not per-turn. One Firestore write burst per session instead of N.
- **The relay is the true state owner.** `_agent_state` is threaded through `process_message()` and back; `stage_progress` is explicitly preserved across LangGraph invocations (`preserved_progress` dance in `gemini_relay.py`) because the graph doesn't manage that field — the *coach* does. Two writers, one field, ownership resolved by convention and a restore step.

**Why `MemorySaver` (in-proc) instead of a Redis/Firestore checkpointer:** the WebSocket already pins a session to one Cloud Run instance for its whole life — there is no cross-instance handoff to survive. A durable checkpointer would add a network round-trip per turn to protect state that (a) is redundantly held in the relay object anyway and (b) is snapshotted to Firestore at session end. Distributed checkpointing is the right call only when sessions migrate between workers; here they can't.

**Why there is no long-term user memory** (no embedding of past sessions, no cross-session persona adaptation): evaluation is deliberately per-session — the product measures *this conversation* against the C.O.R.E. rubric. Cross-session memory would contaminate difficulty calibration (a persona that "remembers" you is a different difficulty every time) and turn a scoring instrument into a moving target. History lives in Firestore for the *human* to review (`GET /api/v1/sessions`), not for the model to condition on.

---

## 4. "Tools": Orchestrated Context Injection, Not Function Calling

**This system uses zero LLM tool/function calling.** No `tools=` parameter, no tool-use loop, no agent deciding what to retrieve. What look like tools — RAG retrieval, objection lookup — are **orchestrator-invoked, pre-prompt context injection** (`coach/analyzer.py::analyze`):

```
per turn:
  objection_context = objection_service.detect_objection(last_customer_msg)   # keyword lookup
  product_context   = rag_service.<retrieve variant>(salesperson_message, ...)  # vector search
  prompt = build_coach_prompt(..., product_context, objection_context)
  response = one Gemini call → JSON
```

**Defense of this choice — the most important pattern in the codebase:**

1. **The retrieval decision is fully determined by session state.** Which property? `persona.property_id`. Which section of the doc? Current C.O.R.E. stage (`EXECUTE → objection_handlers`, `RECOMMEND → agent_talking_points`). When the router is a two-line `if`, giving the LLM a tool-choice loop buys nothing and costs a round-trip.
2. **Bounded latency and cost.** One model call per turn, hard throttled. A tool loop is 2–4 calls with variable depth — unacceptable when the analysis races a live voice conversation.
3. **No tool-loop failure modes.** No malformed tool calls, no infinite loops, no partial tool results mid-generation. Every retrieval is wrapped in its own try/except returning `""` — a failed retrieval degrades the prompt, never the call.
4. **Independently testable retrieval.** `rag_service` methods are plain async functions with exact inputs/outputs; no LLM in the test loop.

**When you'd flip this decision** (know this for the defense): if retrieval needs *reasoning* to route — heterogeneous sources, multi-hop lookups, "search then decide to search again" — orchestration hardcodes what should be learned. This system's knowledge base is one collection with clean metadata; the moment it becomes many collections with ambiguous routing, function calling earns its cost.

---

## 5. Structured Output (Native Mode, migrated 2026-07-05)

The coach's contract (`coach/prompts.py`, `coach/analyzer.py`, `models/coach.py`):

- The analyzer passes `response_schema=CoachAnalysisResponse` + `response_mime_type="application/json"` to `GenerateContentConfig` and consumes `response.parsed` — the SDK guarantees shape and enum validity.
- `CoachAnalysisResponse` is a **dedicated wire model**, not `CoachAnalysis` itself: `confidence` is code-owned (set by the analyzer, never LLM-emitted), and the wire format for `stage_items_completed` is the list-of-objects form the internal model expects.
- Temperature **0.1** for decode stability.
- `_finalize_analysis` keeps only the **semantic** fallbacks: no structured output at all → safe-default `CoachAnalysis` (`intervention_level=NONE, confidence=0.0`); intervention flagged without a hint → `get_intervention_message()` template from `hints.py`.
- Historical note: before the migration the schema was embedded in the prompt text and parsed with fence-stripping + defensive `.get()`s. That entire failure class (malformed JSON, invalid enums, dict-vs-list drift) is gone; the belt-and-suspenders harvest in `_apply_stage_updates` (`coach_agent_service.py` — checklist items taken from both `stage_items_completed` and `techniques_detected`) is retained as cheap insurance against the model populating one field but not the other.

**Defense:** the failure hierarchy is *no hint > wrong hint > crashed session*. Native mode removed the syntactic failure class; the semantic fallbacks (empty hints) still need code, which is why `_finalize_analysis` exists rather than trusting the schema alone.

---

## 6. The RAG Ladder

`app/services/rag_service.py` — one collection (`knowledge_chunks`), four retrieval strategies behind independent feature flags (`config.py`, all default **off** except objection lookup):

| Rung | Flag | Mechanism |
|---|---|---|
| 1. Vector | `rag_enabled` | `find_nearest` (COSINE) on Firestore vector index, metadata pre-filtered |
| 2. Hybrid | `rag_use_hybrid_search` | Vector ‖ in-memory BM25 (k1=1.2, b=0.75) run in parallel (`asyncio.gather`), fused with Reciprocal Rank Fusion (k=60, weights 0.7/0.3) |
| 3. Conversation-aware | `rag_use_conversation_context` | Gemini Flash rewrites the query as a standalone search query from the last 5 turns, then rung 1 |
| 4. LLM re-rank | `rag_use_reranking` | Retrieve `initial_k=10` → Gemini Flash returns top-`final_k=3` indices; falls back to original order on any error |

Supporting facts:
- Embeddings: `gemini-embedding-2` (config) with `output_dimensionality=2048`, cosine distance.
- Chunking: 800 chars, 200 overlap (`chunk_text`).
- Metadata filtering happens **before** vector search (`.where("metadata.category", ...)` then `find_nearest`) — requires composite vector indexes in Firestore (`terraform/firestore.tf`; a metadata-filtered query without the matching composite index fails, which was a real production bug).
- Stage-conditioned `section_type` filter: the coach retrieves objection handlers during EXECUTE and talking points during RECOMMEND — retrieval precision from *session state*, free.

**Design defenses:**

- **Pre-filter > post-filter.** Filtering after a top-k vector search can return zero in-category results when the corpus is dominated by other categories. Pre-filtering guarantees every candidate is eligible. Cost: composite index per filter combination — paid once in Terraform.
- **In-memory BM25 is correct at this scale.** The keyword search fetches all category-filtered docs and scores in Python — O(N) per query, fine under ~1k chunks per property, zero infra (no Elasticsearch to run). The code comments its own scale assumption. Know the exit: past ~10k chunks, move to a real lexical index.
- **RRF over score blending.** Cosine similarities and BM25 scores live on incomparable scales; rank fusion needs no normalization and is robust to either retriever misfiring.
- **Flags default off; each rung fails open to `""`.** Retrieval quality features are additive and independently kill-switchable in production without deploys. The 2026-06 model retirement incident (`gemini-2.0-flash` 404'd) validated exactly this: re-ranking died silently, retrieval degraded to rung 1/2, sessions kept working.
- **LLM re-rank returns *indices*, not text** (max 50 output tokens, temp 0) — the cheapest possible re-rank contract, immune to the model rewriting chunk content.

---

## 7. Reliability Engineering Around LLM Calls

The per-turn analysis path (`gemini_relay._analyze_and_send_hint`) stacks five guards **before** spending a model call:

1. **Quota fuse:** on a 429 (`RateLimitError`), set `_coach_quota_exhausted` for the session — hints disabled, voice untouched. A per-session circuit breaker with no reset (sessions are short).
2. **Throttle:** hard 10s minimum between analyses. Also a UX decision — hint spam trains no one.
3. **Idempotency cache:** SHA-256 of the message → cached `(analysis, progress, hint)`, FIFO-capped at 50 entries. Repeated phrasings (common in sales practice) cost zero.
4. **Mode gate:** hints ship only in Training mode; Evaluation mode runs the same analysis silently so the scorecard is populated either way.
5. **Blanket non-fatality:** the entire agent-processing block is one try/except logging "Agent processing failed."

**Hardened 2026-07-05:** customer-agent `process_message` and `_analyze_and_send_hint` previously shared one try/except — a mood-update exception silently killed coach hints. They now run in independent exception scopes inside `_process_agents()` (`gemini_relay.py`), with distinct log messages so Cloud Run logs identify which feature degraded. Every LLM feature here still fails silent-and-soft by design; the diagnosis lives in Cloud Run logs (severity ≥ WARNING).

**Scoring is deliberately not an LLM judgment** (`coach/scorer.py`): the LLM contributes only boolean checklist detections; the grade is deterministic arithmetic — weighted stages (CONNECT 15 / OBSERVE 30 / RECOMMEND 30 / EXECUTE 25), motivator bonus (≤ +10), objection penalty (≥ −10), deviation penalty (≥ −15), clamp, threshold to letter grade. Two users with identical checklists get identical grades, every time. LLM-as-judge for the *narrative* feedback (`_generate_llm_feedback`, with template fallback), rules for the *number*. That split — subjective prose from the model, accountable metrics from code — is the evaluation design in one sentence.

---

## 8. Defense Practice Questions

Use these as drills: answer out loud, then check the "strong answer" bullets. The best answers name the trade-off you're accepting, not just the benefit.

### Architecture

**Q1. "Why do you run a LangGraph agent every turn and then throw away its response?"**
Strong answer: the graph's *state transitions* are the product (mood/regard analytics for the report card); its text generation is a vestige of the pre-voice architecture. Voice output must come from the Live model for latency and audio coherence. As of 2026-07-05 the redundant LLM call is gone: the relay passes `generate_response=False` and the `generate_response` node skips the model call in voice mode while keeping turn accounting.

**Q2. "Your persona prompt is frozen at connect time. Isn't the customer static?"**
Strong answer: no — dynamism is delegated to the model via explicit behavioral rules in the prompt ("your mood is dynamic — react to how you're treated"), which LLMs execute well within a session. The alternative (mid-session prompt injection) fights the Live API's design. Since 2026-07-05 the prompt is additionally rebuilt from current agent state on reconnect, so the one moment a new prompt *can* be applied, it is accurate. Accepted limitation: deterministic mood state and live mood can still drift apart mid-connection; they serve different consumers (report vs. roleplay), so drift is tolerable.

**Q3. "Why three models instead of one?"**
Strong answer: three *workloads* — real-time native audio, in-character text generation, low-temperature JSON analysis — with conflicting requirements (latency vs. character vs. determinism). Splitting also isolates failure: a 429 on the coach model cannot touch the voice session. Cost: three quota pools to monitor, model-retirement blast radius (the 2.0-flash retirement hit three config keys at once).

### Memory & State

**Q4. "Your LangGraph checkpointer is in-memory. What happens when Cloud Run restarts mid-session?"**
Strong answer: the WebSocket dies with the instance anyway — durable checkpointing wouldn't save the *connection*. The voice session survives via Gemini's resumption handle on reconnect; the mood trajectory restarts, which degrades only analytics granularity. Transcript loss is the real risk (write-at-end persistence) — the honest trade: per-turn Firestore writes would bound the loss window at higher cost and latency.

**Q5. "Why doesn't the customer remember previous sessions with the same user?"**
Strong answer: per-session isolation is a *feature* of an assessment instrument — repeatable difficulty requires a stateless opponent. Cross-session memory belongs in the *coach's* feedback ("you keep skipping OBSERVE"), which can be computed from Firestore history without contaminating the roleplay. Distinguish memory-for-simulation (harmful here) from memory-for-pedagogy (future work).

**Q6. "Two components write to `stage_progress`. Defend that."**
Strong answer: ownership is resolved by convention — the coach writes it, the relay preserves it across graph invocations (the explicit save/restore in `gemini_relay.py`). It works but is fragile-by-convention; a cleaner design gives the field one owner or a merge function. Admitting this shows you can distinguish "correct today" from "safe under change."

### Tools & RAG

**Q7. "Why didn't you give the coach agent function-calling tools for retrieval?"**
Strong answer: the retrieval decision is fully determined by session state (property_id + current stage), so an LLM tool-choice loop adds a round-trip to make a decision a two-line `if` already makes — pure latency and failure surface with zero routing value. Name the flip condition: heterogeneous sources or multi-hop retrieval where routing needs reasoning.

**Q8. "Defend metadata pre-filtering over post-filtering, and its infrastructure cost."**
Strong answer: post-filtering top-k can starve to zero results for minority categories; pre-filtering guarantees eligible candidates. Cost: a composite vector index per filter shape in Firestore, provisioned in Terraform — and a missing index is a hard query failure (this happened), so index management becomes part of the deploy contract.

**Q9. "Your keyword search loads every document into memory. Seriously?"**
Strong answer: yes — deliberately, with the scale assumption written in the code (<1k docs per category filter). It's O(N) Python over a few hundred chunks, zero infrastructure, and it's behind a flag. The exit ramp (real lexical index) is understood and not yet earned. Engineering maturity is matching solution weight to corpus size, not deploying Elasticsearch for 500 chunks.

**Q10. "Why RRF instead of normalizing and blending scores?"**
Strong answer: cosine similarity and BM25 are on incomparable, corpus-dependent scales; any normalization constant is a magic number that breaks when the corpus shifts. RRF uses only ranks — robust, parameter-light (k=60 is a well-studied default), and degrades gracefully when one retriever misfires.

**Q11. "The LLM re-ranker returns comma-separated indices. Why not scores or rewritten passages?"**
Strong answer: smallest possible output contract — 50 tokens, temp 0, trivially parseable, and the model physically cannot corrupt chunk content because it never reproduces it. Every re-rank failure mode collapses to "use original order."

### Reliability & Evaluation

**Q12. "Every LLM failure here is swallowed and logged. Isn't silent degradation dangerous?"**
Strong answer: it's a ranked failure policy — the voice session is the product; coaching is enhancement. *No hint > wrong hint > dead session.* The genuine cost is observability debt: "nothing happened" requires log archaeology (name the fix: a session-health event surfacing degraded features to the client). Cite the model-retirement incident as the policy working: features degraded for days, zero session outages.

**Q13. "Why is the score computed by arithmetic instead of the LLM that already analyzed the conversation?"**
Strong answer: grades demand consistency, explainability, and monotonicity (more checklist items ⇒ never a lower score) — properties arithmetic guarantees and sampling does not. The LLM is used exactly where its judgment is needed (did a *warm greeting* occur?) and nowhere it isn't (what's 0.3×67+0.15×100?). LLM-as-judge for prose feedback keeps its strengths without letting it touch the number.

**Q14. "Defend the 10-second hint throttle from first principles."**
Strong answer: three constraints converge — cost (bounds analysis calls per session), UX (a hint the user hasn't finished reading is noise), and pedagogy (coaching interrupts less than it observes). One mechanism, three requirements. Also note what it costs: a brilliant coaching moment 4 seconds after the last hint is lost.

**Q15. "The analysis cache keys on SHA-256 of the message text alone. When is that wrong?"**
Strong answer (updated 2026-07-05): the key now includes the current C.O.R.E. stage (`sha256(f"{stage}|{message}")`), so identical text in a different stage gets a fresh analysis. Turn count is deliberately excluded — including it would make every key unique and defeat the cache. Residual aliasing (same text, same stage, different turn) is accepted: the cache is per-session and capped at 50, and repeated phrasings within a stage are exactly the case the cache exists for.

### Prompt Engineering

**Q16. "Point to a place where you patched model behavior in code instead of the prompt, and justify it."**
Strong answer: `_apply_stage_updates` harvests checklist items from both `techniques_detected` and `stage_items_completed` because the model populates them inconsistently. Prompt-side fixes for output drift are probabilistic; parse-side tolerance is deterministic. Rule of thumb: shape *intent* in the prompt, enforce *structure* in the parser.

**Q17. "Your insult detection is a hardcoded word list. Defend that against 'just ask the LLM.'"**
Strong answer: this signal feeds only the analytics mood ladder, where determinism and testability outrank recall — and the layer that must handle *nuanced* disrespect live (the persona) already uses the LLM via prompt rules. Same requirement, two layers, each solved with the tool that fits: lists where you need repeatability, models where you need judgment.

---

## 9. Weak Points to Own Before Anyone Else Finds Them

An engineer defending this system should volunteer these:

### Fixed (2026-07-05, `feat/agent-hardening`)

1. ~~**Shared try/except couples customer-agent and coach failures**~~ — fixed: `_process_agents()` in `gemini_relay.py` gives each agent its own exception scope with distinct log messages ("Customer agent processing failed" vs "Coach analysis failed").
2. ~~**Redundant LLM call per turn**~~ — fixed: the relay passes `generate_response=False` to `process_message()`, which sets a `_skip_response` runtime state key; the `generate_response` node skips the LLM call (turn accounting still runs).
3. ~~**Cache key ignores conversation position**~~ — fixed: the analysis cache key is now `sha256(f"{current_stage}|{message}")`. Turn count is deliberately excluded — it would make every key unique and defeat the cache (see Q15).
4. ~~**Prompt not rebuilt on resumption**~~ — fixed: `_current_system_instruction()` rebuilds the prompt from `self._persona` + current `_agent_state`; the reconnect loop calls it on every retry, so mood/regard/objection state is fresh ("Rebuilt system instruction on reconnect" in logs).
5. ~~**JSON-in-prompt instead of native structured output**~~ — fixed: the coach analyzer passes `response_schema=CoachAnalysisResponse` (a dedicated wire model, `models/coach.py`) with `response_mime_type="application/json"` and consumes `response.parsed`. Fence-stripping, `json.loads`, dict→list conversion, and enum try/except are gone; `_finalize_analysis` keeps only the *semantic* fallbacks (no output → safe default, intervention without hint → template).
7. ~~**`DEFAULT_COACH_MODEL` hardcodes a model name in code**~~ — fixed: constant removed; `settings.coach_model` (which has its own config default) is the single source.

Same date: lint debt cleared (`ruff check .` green backend-wide) and CI widened from `ruff check app/` to `ruff check .` + `ruff format --check .` so it can't re-accumulate.

### Still open

6. **BM25 scan and analysis cache are per-instance and unbounded-by-corpus respectively** — both fine at current scale, both documented with exit ramps above.

---

## Related Docs

- [AGENT_FLOW.md](AGENT_FLOW.md) — turn-by-turn walkthrough of the same pipeline
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) — `knowledge_chunks` schema and vector indexes
- [SESSION_STATE_RESUMPTION.md](SESSION_STATE_RESUMPTION.md) — reconnect and resumption mechanics
- [API_SPECIFICATION.md](API_SPECIFICATION.md) — WebSocket protocol carrying all of the above
