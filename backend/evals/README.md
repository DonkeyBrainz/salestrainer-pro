# Agent Eval Harness

Evaluates the **customer agent** (roleplay prospect) and **coach agent**
(hints/feedback) against synthetic scripted scenarios, with pluggable model
providers, plus a **voice suite** that benches the live speech-to-speech
providers with real audio. Distinct from the end-user session grading in
`app/models/evaluation.py` — this harness measures *agent/model* quality
across prompt/model changes.

## Running

```bash
cd backend

# Deterministic checks only (fast, still calls the real model under test)
uv run python -m evals.run --suite customer
uv run python -m evals.run --suite coach
uv run python -m evals.run --suite all

# Filter by tag
uv run python -m evals.run --suite customer --tags behavior:insult

# Add LLM-judge rubric scoring (extra model calls)
uv run python -m evals.run --suite all --judge --judge-model gemini-2.5-pro

# Compare against a previous run (regression diff)
uv run python -m evals.run --suite all --compare evals/results/run-<id>.json
```

Requires `GEMINI_API_KEY` (via `backend/.env`). JSON reports land in
`evals/results/` (gitignored). Exit code is 0 only on a 100% pass rate
(and no regressions when `--compare` is used).

## How it works

- **Scenarios** (`scenarios/customer/*.yaml`, `scenarios/coach/*.yaml`) —
  one YAML per scenario, validated by pydantic models in `scenarios/types.py`.
  Tags use `key:value` form (`stage:connect`, `difficulty:low_regard`,
  `behavior:insult`) and reports slice pass rates by tag.
- **Runners** (`runners/`) — drive the real `CustomerAgentGraph` (checkpointed
  per-scenario `thread_id`, seeded RNG for reproducibility) and the real
  `CoachAnalyzer`, with the provider injected.
- **Deterministic checks** (`checks/`) — hard pass/fail gate: mood-ladder
  transitions, objection-injection timing, forbidden phrases, coach technique
  recall, deviation flagging, intervention severity, stage readiness.
  Scorer arithmetic is *not* re-checked here (covered by
  `tests/unit/test_coach_scorer.py`).
- **LLM judge** (`judge/`, opt-in `--judge`) — soft quality signal on rubric
  dimensions (persona consistency, naturalness, hint actionability, ...),
  scored 1-5 with mandatory rationale at temperature 0. Never affects
  pass/fail.
- **Reports** (`report/`) — console summary + versioned JSON (`RunReport`),
  with `--compare` producing a regression-highlighted diff between runs.

## Plugging in another model

Implement `app.llm_providers.LLMProvider` (two async methods: `complete`,
`complete_structured`; map native token usage to
`{"prompt_tokens", "completion_tokens", "total_tokens"}`), then register it in
`PROVIDERS` in `evals/run.py` and run with `--provider <name>`.

## Voice suite (speech-to-speech bench)

`--suite voice` drives the production `LLMStreamProvider` adapters (gemini /
openai / nova) with **real audio both ways**: scripted salesperson turns are
TTS-synthesized (cached in `fixtures/audio/`), streamed as 16kHz PCM via
`send_audio`, and the model's spoken reply is captured — the provider's own
ASR transcript (WER comprehension checks), time-to-first-audio, audibility,
forbidden phrases, billed audio-token usage, and a per-turn WAV artifact in
`results/audio/<run_id>/`. Optional `--judge` (transcript rubric) and
`--audio-judge` (multimodal Gemini listens to the WAVs: naturalness, tone,
clarity, pacing).

```bash
uv run python -m evals.run --suite voice --provider gemini --judge --audio-judge
uv sync --extra nova && uv run python -m evals.run --suite voice --provider nova && uv sync --dev
```

Voice is never included in `--suite all` (bills real audio tokens; ~$0.04-0.09
per provider per run). New speech-to-speech providers register in
`LIVE_PROVIDERS` (`app/llm_providers/registry.py`) and must emit the LiveEvent
vocabulary in `app/llm_providers/streaming.py` (including the `usage` event).

**Full documentation** — setup, what's tested and expected, baseline results,
and the new-provider checklist: `documentation/VOICE_EVAL_BENCH.md`.

## CI

`tests/integration/test_eval_harness_smoke.py` runs in normal CI with a mocked
provider to protect the harness wiring itself. Real-API harness runs should be
a manual or nightly job that archives the JSON report.
