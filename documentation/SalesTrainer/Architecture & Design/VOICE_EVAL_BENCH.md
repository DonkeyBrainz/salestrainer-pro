---
tags: [#architecture, #testing, #voice, #evaluation]
---

# Voice Eval Bench — Speech-to-Speech Model Evaluation

**Status:** Live and validated (2026-07-13) · **Suite:** `--suite voice` in `backend/evals/`
**Verified providers:** Gemini Live, Amazon Nova 2 Sonic · OpenAI Realtime wired but unverified (no API key yet)

---

## 1. Why this bench exists

The text eval harness (customer/coach suites) tests conversational *behavior* through turn-based
text LLMs — it never touches the models the product actually ships for voice roleplay. Live voice
quality is a different axis entirely: does the model **hear** the user correctly (ASR front-end),
how fast does it **start speaking** (turn-taking latency), does the **spoken reply** stay in
persona, and what does a session actually **cost** in audio tokens.

This bench evaluates exactly that: **real speech audio in, real speech audio out**, through the
same `LLMStreamProvider` adapters production uses. Nothing is text-shortcut — `send_text()` would
bypass ASR/VAD/turn-taking, which is precisely what's under test.

---

## 2. How the bench works (pipeline)

```
scenario YAML                 evals/scenarios/voice/*.yaml
     │  salesperson_text per turn + expectations
     ▼
TTS fixture synthesis         evals/audio/tts.py
     │  Gemini TTS (voice "kore") → 24kHz PCM16 → downsample 16kHz
     │  → +1s silence tail (triggers server VAD) → cached by content hash
     │    in evals/fixtures/audio/ (re-runs cost $0 in TTS)
     ▼
live session driver           evals/runners/voice_runner.py
     │  build_live_provider(name) → connect_live(system_instruction, voice)
     │    - system prompt: build_customer_prompt(persona, connect-time state)
     │      (same one-shot prompt production uses at connect)
     │    - voice: resolve_voice(persona, provider) from the persona voice map
     │  per turn: stream fixture PCM in 100ms chunks via send_audio()
     │  → consume LiveEvents until "end" (60s turn timeout, 30s connect
     │    timeout, 2s grace drain for late transcriptions)
     ▼
capture (VoiceTurnRecord)     evals/report/models.py
     │  input_transcription  = provider's OWN ASR of our audio (ground truth
     │                         for comprehension — no extra ASR service)
     │  response_text        = model's spoken words (output_transcription)
     │  first_audio_ms       = send-complete → first audio chunk
     │  output audio         = bytes, duration, peak amplitude
     │  usage                = billed tokens (new "usage" LiveEvent, all 3
     │                         adapters) → real $/run in reports
     │  WAV artifact         = evals/results/audio/<run>/<scenario>/turnN.wav
     ▼
deterministic checks          evals/checks/voice_checks.py   (hard pass/fail)
LLM judges (opt-in)           evals/judge/  (soft 1-5 scores, never gate)
     ▼
report                        RunReport JSON + console table + --compare diff
```

---

## 3. What is tested, and what "pass" means

### 3.1 Scenarios (`evals/scenarios/voice/`)

Each scenario probes one audio-specific failure mode, using existing personas:

| Scenario | Persona | Probes | Turns |
|---|---|---|---|
| `first_timer_greeting_comprehension` | anxious_first_timer (Jennifer) | Baseline: hears a greeting, replies in character, promptly, audibly | 2 |
| `practical_family_numbers_comprehension` | practical_family | **Numbers**: prices/sizes/years are where ASR slips ("four hundred eighty five thousand") | 2 |
| `wealthy_skeptic_stays_in_character` | wealthy_skeptic | **Character under pressure**: pushy pitch must get a skeptical spoken reply, never assistant-speak | 2 |
| `retiree_multi_turn_context` | lifestyle_retiree | **Session context**: turn 3 only makes sense if turns 1-2 were retained | 3 |
| `minimalist_long_utterance` | urban_minimalist | **Endurance**: ~25s monologue tests VAD endpointing + sustained ASR | 2 |

### 3.2 Deterministic checks (hard gate, per turn)

| Check | Measures | Expected (default) |
|---|---|---|
| `asr_comprehension` | Word-error-rate between the script and the provider's own transcription of our audio | WER ≤ `max_wer` (0.5) |
| `forbid_phrases` | Spoken reply must not contain "as an AI", "language model", etc. | zero hits |
| `first_audio_latency` | Wall time from send-complete to first output audio chunk | ≤ `max_first_audio_ms` (25s; 45s for the long utterance) |
| `spoke_audibly` | Output audio duration + peak amplitude (catches silent/empty turns) | ≥ `min_output_audio_ms` (300ms) and peak ≥ 100 |
| `scenario_completed` | Session opened, every turn reached `end` (connect 30s / turn 60s timeouts) | no timeout/error |

**Threshold philosophy:** budgets are **regression tripwires calibrated from observed provider
baselines + margin, not UX targets**. Important nuance: the bench streams input audio *faster than
realtime*, so the model still has to "listen through" the whole utterance + 1s silence tail before
replying — `first_audio_ms` therefore scales with utterance length and is larger than the
conversational latency a user would feel. Compare providers against each other and against their
own history, not against an absolute "good" number. (The original 10s default failed every Gemini
scenario; budgets were recalibrated to 25s/45s after the first baseline run.)

### 3.3 LLM judges (soft signal, never affects pass/fail)

- **Transcript judge** (`--judge`, runs on Gemini regardless of provider under test):
  `persona_consistency`, `stays_in_character`, `conversational_naturalness`,
  `comprehension_grounding` (does the reply engage with what was actually said, per the
  "[model heard: …]" lines). 1-5 with mandatory rationale, temperature 0.
- **Audio judge** (`--audio-judge`): sends the saved WAVs to multimodal `gemini-3.5-flash` with
  the persona sheet — the only layer that hears **prosody**: `vocal_naturalness`,
  `tone_matches_persona`, `speech_clarity`, `pacing`.
- **Human ears**: every turn's output audio is saved as a WAV artifact. The ultimate audio judge
  is listening; the bench makes every run auditable.

---

## 4. Baseline results (2026-07-13, first validated runs)

5 scenarios, 11 spoken turns each way:

| | Pass | Avg scenario latency | Avg WER | Avg time-to-first-audio | Audio tokens | Est. cost/run |
|---|---|---|---|---|---|---|
| **Gemini** `gemini-2.5-flash-native-audio-preview-12-2025` | 5/5 | 40.7s | 0.10 | 11.0s | 10,205 | ~$0.040 |
| **Nova 2 Sonic** `amazon.nova-2-sonic-v1:0` | 5/5 | 14.6s | 0.10 | **1.9s** | 14,155 | ~$0.083 |

Judge scores (Gemini run, transcript + audio): 4.4–5.0 across all dimensions.

**Findings:**
- Comprehension is identical (WER 0.10 both) — the differentiator is **turn-taking speed**:
  Nova starts speaking ~5.7x sooner (1.9s vs 11s). This is the metric users feel.
- Nova is more verbose (≈4.4x the completion tokens) → ~2x cost per run despite identical
  $3/$12-per-1M speech-token rates. Both are pennies per suite run.
- Both models stayed fully in character under pressure, handled spoken numbers, and tracked
  3-turn context.
- **Known Nova transcript quirk:** later-turn `output_transcription` events carry a literal
  `{ "interrupted" : true }` marker plus repeated prior-turn text. The audio is what to trust;
  verify by ear whether it's a transcript-only artifact (likely) before treating it as an
  adapter bug. WER/forbid checks are unaffected (they read `input_transcription`/current text).
- Two bugs the first live runs surfaced (both fixed): Nova Sonic's adapter lacked the
  boto3→env credential bootstrap (its first real connection hung — now shared via
  `app/llm_providers/aws_credentials.py`), and the runner needed a connect timeout so a hung
  handshake fails one scenario, not the suite.
- Interactive listening bench (side-by-side players + transcripts + metrics) can be regenerated
  from any two run JSONs — script pattern in the 2026-07-13 session; WAVs live under
  `backend/evals/results/audio/<run_id>/`.

**Pricing reference** (verified against provider pricing pages 2026-07):
Gemini native audio $3.00/$12.00 per 1M speech tokens in/out (output includes thinking tokens);
Nova 2 Sonic $3.00/$12.00; Nova Sonic v1 $3.40/$13.60 (why the default was bumped to v2);
Gemini text-eval model $0.30/$2.50; Nova Lite (text evals) $0.06/$0.24.

### 4.1 Run history log

Append a row per bench run (or per meaningful pair of runs) so pass-rate/latency/WER trends are
visible as scenarios are added and models are swapped in or out. Pull the numbers straight from
the run's `RunReport` JSON in `evals/results/` — don't hand-estimate. `Δ` notes what changed
*about the bench itself* since the previous row for that provider (new scenario, model swap,
prompt change), not what changed in the persona's answers.

| Date | Run ID | Provider | Model | Scenarios | Pass | Avg WER | Avg TTFA | Tokens (in/out) | Δ since last row |
|---|---|---|---|---|---|---|---|---|---|
| 2026-07-13 | `run-voice-gemini` / `run-voice-nova` | Gemini | `gemini-2.5-flash-native-audio-preview-12-2025` | 5 | 5/5 | 0.10 | 11.0s | 10,205 / — | First validated baseline (see §4 narrative) |
| 2026-07-13 | `run-voice-gemini` / `run-voice-nova` | Nova 2 Sonic | `amazon.nova-2-sonic-v1:0` | 5 | 5/5 | 0.10 | 1.9s | 14,155 / — | First validated baseline |
| 2026-07-16 | `run-20260716-183756-b2cb92` | Nova 2 Sonic | `amazon.nova-2-sonic-v1:0` | 6 | 5/6 | 0.107 | 1.82s | 12,188 / 4,498 | Nova prompt hardened against role-reversal ("how can I help you") + premature budget/name disclosure (`build_live_system_instruction` in `app/agents/prompts.py`); added `guarded_disclosure_low_regard` scenario + `forbid_regex` check — both new checks pass. `retiree_multi_turn_context` turn1 ASR comprehension failed (WER over threshold; not a character/disclosure regression). |
| 2026-07-16 | `run-20260716-184222-26add9` | Gemini | `gemini-2.5-flash-native-audio-preview-12-2025` | 6 | 5/6 | 0.119 | 7.16s | 10,908 / 890 | Same scenario-set bump (unaffected by the Nova-only prompt guardrails). `minimalist_long_utterance` turn0 failed first-audio-latency + spoke-audibly. |
| 2026-07-16 | — | — | — | — | — | — | — | — | `AUDIO_JUDGE_MODEL` in `evals/judge/audio_judge.py` bumped `gemini-2.5-flash` → `gemini-3.5-flash` (2.5-flash retired for new API keys, see commit `456f515`; judge was still pinned to the retired model even though `coach_model`/`gemini_model` had already moved). No bench run needed for this row — config-only fix, next `--audio-judge` run will pick it up. |
| 2026-07-16 | `run-20260716-202142-205e2e` | Nova 2 Sonic | `amazon.nova-2-sonic-v1:0` | 6 | 5/6 | 0.112 | 1.89s | 12,194 / 4,364 | Fixed the transcript-corruption bug found while preparing to switch production traffic to Nova: `nova_sonic.py` was forwarding every `textOutput` event verbatim, so (a) Nova's barge-in marker (`{ "interrupted" : true }`, embedded directly in a `textOutput.content` field per AWS's own reference client) leaked into live transcripts and Firestore, and (b) both the SPECULATIVE and non-speculative assistant passes got concatenated into duplicated text. Now tracks `generationStage` from `contentStart` (only speculative-pass assistant text is kept, matching AWS's reference) and strips the interruption marker. Verified clean against this run's raw `response_text` — no marker leakage, no duplication. `retiree_multi_turn_context` turn1 ASR-comprehension failure is the same pre-existing, unrelated WER miss seen in the prior row. |
| 2026-07-16 | — | — | — | — | — | — | — | — | **Production switch**: `LIVE_PROVIDER=nova` (was `gemini`) in the Cloud Run deploy workflow, `gemini` kept in `LIVE_PROVIDER_ALLOWLIST` as a fallback. Backend Docker image now installs the `nova` extra so the Bedrock SDK ships in the production image. New least-privilege AWS IAM user (`salestrainer-pro-bedrock`, `bedrock:InvokeModel*` scoped to `amazon.nova-2-sonic-v1:0` in us-east-1 only) with its access key in GCP Secret Manager (`aws-bedrock-access-key-id`/`aws-bedrock-secret-access-key`). Driven by the ~4x TTFA win documented above; the prompt-hardening and transcript-quirk fixes in the two rows before this one were the gating work before flipping the default. |

---

## 5. Running the bench

```bash
cd backend

# Gemini (GEMINI_API_KEY in .env — also required for TTS fixtures + judges)
uv run python -m evals.run --suite voice --provider gemini

# With judges
uv run python -m evals.run --suite voice --provider gemini --judge --audio-judge

# Nova (AWS creds via ~/.aws or env; nova extra is opt-in — keep it OUT of the
# default dev env or test_nova_sonic's "SDK absent" test breaks)
uv sync --extra nova
uv run python -m evals.run --suite voice --provider nova
uv sync --dev   # restore

# OpenAI (once OPENAI_API_KEY is set)
uv run python -m evals.run --suite voice --provider openai

# Filter, compare, name the report
uv run python -m evals.run --suite voice --provider nova --tags voice:comprehension
uv run python -m evals.run --suite voice --provider nova --compare evals/results/run-voice-gemini.json
```

Outputs: JSON report in `evals/results/`, WAVs in `evals/results/audio/<run_id>/` (both
gitignored). TTS fixtures cache in `evals/fixtures/audio/` (gitignored).
`--suite all` deliberately **excludes** voice — audio runs bill real tokens and take minutes;
they run only when explicit. Cost guardrail: a full 5-scenario run ≈ $0.04–0.09/provider.

---

## 6. Plugging in new providers / models as they release

### 6.1 New model on an existing provider — config only, no code

Model IDs live in `app/config.py` and can be overridden per run:

```bash
# One-off bench of a new model id
uv run python -m evals.run --suite voice --provider nova --model amazon.nova-3-sonic-v1:0  # label only; see note

# Permanent switch: edit the setting
#   gemini_live_model / openai_realtime_model / nova_sonic_model  (voice)
#   gemini_model / nova_model / voxtral_model                     (text evals)
```

Note: for the voice suite the model actually used comes from the provider's Settings field
(`_VOICE_MODEL_LABEL` in `evals/run.py` maps provider→setting); change the setting (or env var,
e.g. `NOVA_SONIC_MODEL=...`) to bench a new model id.

### 6.2 New speech-to-speech provider — implement the protocol, register, cast voices

The contract is `LLMStreamProvider` / `LiveSession` (`app/llm_providers/streaming.py`) — a
`connect_live()` async context manager and four session methods (`send_audio`, `send_text`,
`receive`, `close`). `receive()` must yield the shared **LiveEvent vocabulary**:

| Event `type` | Required? | The bench uses it for |
|---|---|---|
| `audio` (24kHz PCM16 out) | yes | artifacts, first-audio latency, audibility |
| `input_transcription` | yes | WER comprehension checks |
| `output_transcription` | yes | forbid-phrases, judges |
| `end` (turn boundary) | yes | turn loop |
| `usage` `{prompt/completion/total_tokens, detail}` | strongly recommended | cost accounting |
| `internal_reasoning`, `go_away`, `session_resumption_update` | optional (Gemini-only today) | ignored by the bench |

Checklist (mirrors how `nova_sonic.py` / `openai_realtime.py` were added):

1. **Adapter** `app/llm_providers/<name>.py` — translate the vendor's stream into LiveEvents.
   Input audio arrives as 16kHz PCM16 mono (resample with `PcmResampler` if the vendor needs
   another rate — OpenAI upsamples to 24k). Raise the `app.core.exceptions` taxonomy.
   Don't discard the vendor's usage/token events — map them to the `usage` LiveEvent.
2. **Register** in `LIVE_PROVIDERS` (`app/llm_providers/registry.py`) — this makes it available
   to BOTH the production WebSocket relay (`?provider=<name>`, gated by
   `live_provider_allowlist`) and the bench (`--suite voice --provider <name>`).
3. **Settings** in `app/config.py` — API key, model id, temperature.
4. **Voice casting** — add a `<name>` key to every persona's `voices` dict
   (`app/agents/personas.py`) and a default in `DEFAULT_VOICES`
   (`app/llm_providers/voices.py`). `tests/unit/test_persona_voices.py` enforces completeness.
5. **Model label** — add to `_VOICE_MODEL_LABEL` in `evals/run.py` so reports name the model.
6. **Unit tests** — mock the vendor transport, script server events, assert each LiveEvent
   translation row (pattern: `tests/unit/test_openai_realtime.py`, `test_nova_sonic.py`).
7. **Bench it** — `--suite voice --provider <name>`, listen to the WAVs, then
   `--compare` against the current best run.

### 6.3 New text-eval provider (customer/coach suites)

Implement `LLMProvider` (`complete` / `complete_structured`), register in `PROVIDERS` in
`evals/run.py`. Bedrock text models are one-liners: subclass `BedrockTextProvider`
(`app/llm_providers/bedrock_text.py`) with a model default — see `voxtral.py` (3 lines of logic).

### 6.4 New scenarios / checks

- Scenario: drop a YAML in `evals/scenarios/voice/` (schema: `VoiceScenario` in
  `evals/scenarios/types.py`). Keep suites small — audio runs cost money and minutes.
- Check: pure function of `(VoiceTurnTrigger, VoiceTurnRecord) → CheckResult | None` in
  `evals/checks/voice_checks.py`, added to the tuple in `run_voice_checks`.

---

## 7. Known limitations / deliberate scope cuts

- **OpenAI Realtime unverified live** — adapter fully unit-tested against scripted events, but
  no `OPENAI_API_KEY` has been set; first live run may surface GA event-name drift (the adapter
  accepts GA + beta names defensively).
- **Barge-in / interruption scenarios** are v2 — needs mid-response audio injection, and Nova's
  `END_TURN` vs `INTERRUPTED` currently collapse to the same `end` event.
- **Mood drift never reaches the live voice model** (any provider): production builds the system
  prompt once per connection; LangGraph mood/regard updates are analytics-only mid-session. The
  bench therefore asserts consistency with connect-time persona state only.
- **Usage accumulation is heuristic**: OpenAI reports per-response usage (sum), Nova reports
  cumulative session totals (monotone-delta detection in `voice_runner._accumulate_usage`).
  Verified plausible on live runs; per-provider exactness should be re-checked when instrumenting
  real billing.
- **Live voice is nondeterministic** — same scenario can vary run to run (one Gemini run produced
  an empty turn). Treat single-run failures as signals to re-run, not verdicts; trends across
  runs are the real data.
- Cosmetic: awscrt prints a harmless `InvalidStateError` traceback during Nova stream teardown.

---

## 8. File map

| Path | Role |
|---|---|
| `backend/evals/scenarios/voice/*.yaml` + `scenarios/types.py` | Scenario scripts + schema |
| `backend/evals/audio/tts.py` | TTS fixture synthesis + cache + WAV writer |
| `backend/evals/runners/voice_runner.py` | Live-session driver (timeouts, capture, artifacts) |
| `backend/evals/checks/voice_checks.py` | WER + deterministic checks |
| `backend/evals/judge/rubric.py`, `judge.py`, `audio_judge.py` | Transcript + audio judges |
| `backend/evals/report/models.py` | `VoiceTurnRecord`, `ScenarioResult.voice_turns` |
| `backend/evals/run.py` | CLI: `--suite voice`, `--audio-judge`, provider/model wiring |
| `backend/app/llm_providers/streaming.py` | LiveEvent vocabulary (incl. `usage`) |
| `backend/app/llm_providers/registry.py` | `LIVE_PROVIDERS` (shared with production relay) |
| `backend/app/llm_providers/voices.py` + `app/agents/personas.py` | Persona→voice casting |
