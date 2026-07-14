# Provider-Agnostic Voice Pipeline: Persona Voice Mapping + OpenAI Realtime + Nova Sonic Adapters

## Context

Follow-up to the eval harness work on `feat/agent-hardening`. The harness made the turn-based LLM
calls provider-pluggable, but each persona's `voice_name` ("puck", "aoede", ...) is a Gemini Live
prebuilt-voice ID — switching speech-to-speech providers would break voice casting. The realistic
S2S candidates to test against are **OpenAI Realtime** (gpt-realtime, 10 voices incl.
Realtime-exclusive cedar/marin) and **Amazon Nova 2 Sonic** (Bedrock, ~16 voices, cheapest per
minute); both use named prebuilt voices, so a per-provider persona→voice dictionary works. User
confirmed: `voices: dict[str, str]` on each persona + `resolve_voice()` helper, voice casts for
gemini/openai/nova now, AND working streaming adapters for both new providers so they can actually
be tested end-to-end through the existing WebSocket relay.

Goal: make the SalesTrainer Pro speech-to-speech pipeline provider-agnostic. Three live providers
(gemini / openai / nova) selectable at runtime, each with per-persona voice casting, all pluggable
into the existing WebSocket relay with zero frontend changes (browser still sends 16kHz PCM16 in,
plays 24kHz PCM16 out; same JSON message vocabulary).

Confirmed decisions (not re-litigated): `voices: dict[str, str]` on CustomerPersona keyed by
provider; `resolve_voice()` helper with per-provider defaults; both OpenAI Realtime and Nova Sonic
adapters implemented as working streaming providers.

---

## Phase 0 — Ground truth (verified in repo)

- `CustomerPersona` (`app/agents/state.py:106-155`, pydantic v2, `frozen=True`) has
  `voice_name: str` at line 135. Consumed in exactly one production place:
  `app/api/ws/gemini_relay.py:218` -> `_run_with_reconnection(voice_name=...)` (line 298) ->
  `gemini_service.connect_live(voice_name=...)` (line 345). No API/frontend exposure.
- `GeminiLiveSession.receive()` (`app/services/gemini_service.py:328-439`) yields dict events with
  `type` in: `audio` (bytes in `audio_data`), `internal_reasoning`, `input_transcription`,
  `output_transcription` (both with `text` + `finished`), `session_resumption_update`
  (`new_handle`, `resumable`), `go_away` (`time_left`), `end`. `send_audio(bytes)` and
  `send_text(str)` are the inputs. **This dict vocabulary is the adapter contract** — the relay
  (`_relay_gemini_to_client`, gemini_relay.py:565-699) consumes exactly these keys.
- Relay reconnection (`_run_with_reconnection`, gemini_relay.py:293-435): reconnects only when
  `_should_reconnect` (set by `go_away`) or `_resumption_handle` (set by
  `session_resumption_update`) — both Gemini-only signals. Non-Gemini providers never emit them,
  so the loop degrades naturally to "connect once, fail closed" (see Phase 5 for the v1 stance).
- WS route: `app/api/websocket.py` `/ws/gemini/live`, constructs `GeminiWebSocketRelay` per
  connection with `get_gemini_service` DI.
- Provider abstraction: `app/llm_providers/base.py` (turn-based `LLMProvider` Protocol; docstring
  explicitly reserves a sibling `LLMStreamProvider`), `gemini.py` (`GeminiProvider`). Eval harness
  registry pattern: `backend/evals/run.py:42-54` (`PROVIDERS: dict[str, type]` + `build_provider`).
- Settings (`app/config.py`): `gemini_api_key`, `gemini_live_model`
  (`gemini-2.5-flash-native-audio-preview-12-2025`), `gemini_live_temperature: 0.5`. No
  OpenAI/AWS settings exist.
- `voice_name` usages to migrate: `state.py:135`, 10 blocks in `personas.py` (lines 43, 77, 109,
  142, 181, 214, 257, 290, 323, 362), relay lines 218/298/312/345, gemini_service (param — keep),
  tests: `tests/unit/test_agent_state.py:64,70,85,103,119,136`. (`test_user_repository.py`
  references are the unrelated removed user-level voice pref — leave alone.)
- Deps: `websockets>=12.0` is **dev/e2e only** (pyproject optional-deps) — must become a runtime
  dep for the OpenAI adapter. No numpy, no openai, no AWS SDKs installed.
- Conventions: Python 3.11, uv, ruff line-length 100, mypy strict, pydantic v2, unittest.mock-heavy
  tests in `backend/tests/unit`, 80% coverage gate.

---

## Phase 1 — Persona `voices` field + `resolve_voice` (behavior-preserving)

### 1a. Model change (`app/agents/state.py`)
Replace `voice_name: str` with:

```python
voices: dict[str, str] = Field(
    ..., description="Provider-keyed voice IDs, e.g. {'gemini': 'puck', 'openai': 'cedar', 'nova': 'matthew'}"
)
```

Decision: **remove `voice_name` outright** (no deprecation shim). It is server-internal with a
single consumer; grep shows a fully enumerable migration surface. Keeping both invites drift.

### 1b. Voice resolution helper (`app/llm_providers/voices.py`, new)

```python
DEFAULT_VOICES: dict[str, str] = {"gemini": "aoede", "openai": "marin", "nova": "matthew"}

def resolve_voice(persona: CustomerPersona, provider: str) -> str:
    """Persona-mapped voice for provider, falling back to the provider default."""
```

Falls back to `DEFAULT_VOICES[provider]`; raise `ValueError`/`KeyError` for an unknown provider
(programming error, should never reach production because the registry gates provider names).

### 1c. Voice cast — all 10 personas (openai/nova IDs to verify against current docs at implementation time)

Temperament mapping used: puck = playful/energetic male, aoede = warm female, kore = steady/
practical female, charon = gruff/deep male, zephyr = brisk/bright.

| Persona | gemini (existing) | openai | nova |
|---|---|---|---|
| optimistic_renovator (Marcus, upbeat contractor) | puck | verse (bright male) | carlos |
| anxious_first_timer (Jennifer, nervous teacher) | aoede | coral (warm female) | tiffany |
| practical_family (steady pragmatist) | kore | marin (even female) | amy |
| urban_minimalist (crisp, design-minded) | aoede | shimmer (light female) | tiffany |
| privacy_remote_worker (reserved male) | puck | echo (measured male) | matthew |
| scaling_investor (composed, analytical) | aoede | sage (calm female) | amy |
| wealthy_skeptic (gruff, dismissive) | charon | ash (deep male) | matthew |
| landlord_investor (brisk, transactional) | zephyr | cedar (direct male) | carlos |
| school_obsessed_parent (earnest, focused) | kore | marin | amy |
| lifestyle_retiree (mellow, unhurried) | charon | ballad (low-key male) | matthew |

Nova's roster is small (matthew/tiffany/amy/lupe/carlos/...), so duplication is expected. VERIFY
at implementation time (context7 / provider docs): exact OpenAI Realtime voice list
(alloy/ash/ballad/coral/echo/sage/shimmer/verse/cedar/marin as of last check) and current Nova 2
Sonic voiceIds.

### 1d. Migration edits
- `app/agents/personas.py`: each of the 10 persona blocks: `voice_name="puck"` ->
  `voices={"gemini": "puck", "openai": "verse", "nova": "carlos"}` (per table).
- `app/api/ws/gemini_relay.py:218`: `voice_name=persona.voice_name` ->
  `voice=resolve_voice(persona, <provider name>)` (final form lands in Phase 5; during Phase 1 it
  can be `resolve_voice(persona, "gemini")` to stay behavior-preserving).
- `tests/unit/test_agent_state.py`: update 5 persona constructions + the line-70 assertion
  (`assert persona.voices["gemini"] == "leda"`).
- `GeminiService.connect_live(voice_name=...)` signature is untouched (it is the Gemini SDK-facing
  parameter, correctly provider-specific).

### 1e. Tests (new `tests/unit/test_persona_voices.py`)
- Every persona in `PERSONAS` has a non-empty voice for every provider in the live registry
  (import `LIVE_PROVIDERS` keys once Phase 5 lands; until then assert against
  `{"gemini", "openai", "nova"}`). This is the eval-harness coverage tie-in (item 6): pure pytest,
  no LLM, runs in CI, and unblocks future audio-level evals by guaranteeing casting completeness.
- `resolve_voice` returns mapped voice; falls back to `DEFAULT_VOICES` for a synthetic persona with
  a missing key; errors on unknown provider.

Exit criteria: full existing suite green, mypy/ruff green, Gemini path byte-identical behavior.

---

## Phase 2 — `LLMStreamProvider` protocol + Gemini wrapper

### 2a. `app/llm_providers/streaming.py` (new)

```python
LiveEvent = dict[str, Any]  # same vocabulary GeminiLiveSession already emits

@runtime_checkable
class LiveSession(Protocol):
    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> None: ...
    async def send_text(self, text: str) -> None: ...
    def receive(self) -> AsyncGenerator[LiveEvent, None]: ...
    async def close(self) -> None: ...

@runtime_checkable
class LLMStreamProvider(Protocol):
    name: str
    def connect_live(
        self,
        *,
        system_instruction: str | None = None,
        voice: str | None = None,
        resumption_handle: str | None = None,   # Gemini-only; others ignore it
    ) -> AbstractAsyncContextManager[LiveSession]: ...
```

Notes:
- Keep `LiveEvent` as a plain dict (matching today's relay) rather than dataclasses — drop-in
  compatibility is the whole point; a typed event model is a later refactor.
- Event vocabulary documented in the module docstring: required for all providers = `audio`,
  `input_transcription`, `output_transcription`, `end`; optional/provider-specific =
  `internal_reasoning`, `session_resumption_update`, `go_away`. Relay already treats the optional
  ones as optional.
- `resumption_handle` stays in the signature (relay passes it unconditionally); non-Gemini
  providers accept and ignore it.
- Error contract: adapters raise the existing `app.core.exceptions` taxonomy
  (`InvalidRequestError`, `RateLimitError`, `ServiceUnavailableError`, `InternalError`) so the
  relay's handlers in `handle_connection` work unchanged.

### 2b. `GeminiLiveProvider` (`app/llm_providers/gemini_live.py`, new — keep separate from turn-based `gemini.py`)
Thin adapter: `__init__(settings)` constructs/receives a `GeminiService`; `connect_live(...)`
delegates to `GeminiService.connect_live(system_instruction=..., voice_name=voice,
resumption_handle=...)` and yields the existing `GeminiLiveSession` (which already satisfies the
`LiveSession` protocol structurally — verify `receive()`'s AsyncGenerator return matches; no
rewrite of gemini_service.py). `name = "gemini"`.

### 2c. Registry (`app/llm_providers/registry.py` or in `__init__.py`)

```python
LIVE_PROVIDERS: dict[str, Callable[[Settings], LLMStreamProvider]] = {
    "gemini": GeminiLiveProvider,
    # "openai": OpenAIRealtimeProvider,   (Phase 4)
    # "nova": NovaSonicProvider,          (Phase 6)
}
def build_live_provider(name: str, settings: Settings) -> LLMStreamProvider: ...
```

Mirrors `evals/run.py` `PROVIDERS`/`build_provider` exactly (same error style for unknown names).

### 2d. Tests
- `tests/unit/test_stream_protocol.py`: `GeminiLiveSession` satisfies `LiveSession` (isinstance on
  runtime_checkable protocol); `GeminiLiveProvider.connect_live` forwards args to a mocked
  `GeminiService.connect_live` (assert voice/system_instruction/resumption passthrough).
- Existing `test_gemini_service.py`, `test_gemini_live_session.py`, `test_gemini_relay.py` stay
  green untouched.

---

## Phase 3 — Audio resampler utility

`app/llm_providers/audio.py` (new): dependency-free int16 PCM linear-interpolation resampler.
Do NOT use `audioop` (removed in 3.13 — avoid the trap) or numpy (not a dep).

```python
class PcmResampler:
    """Streaming linear resampler for 16-bit mono PCM (e.g. 16000 -> 24000)."""
    def __init__(self, src_rate: int, dst_rate: int) -> None: ...
    def process(self, chunk: bytes) -> bytes: ...   # stateful: carries fractional position + last sample across chunks
```

Implementation: `array('h')` decode, linear interpolation at ratio src/dst, carry the last input
sample and fractional read position between `process()` calls so chunk boundaries are seamless.
Handle odd-length chunk guard (raise or buffer the stray byte — pick raise `InvalidRequestError`
since browser frames are always even).

Tests (`tests/unit/test_audio_resampler.py`): identity when rates equal; 16k->24k output length =
ceil(n*1.5) within rounding across multi-chunk streams (total sample count invariant vs. one-shot
processing of the concatenated input); constant signal stays constant; sine-wave smoke (no numpy —
generate with `math.sin`, assert max sample-to-sample delta stays bounded); statefulness: splitting
input into chunks yields byte-identical output to one-shot.

---

## Phase 4 — OpenAI Realtime adapter (`app/llm_providers/openai_realtime.py`)

Dependency: raw `websockets` client (move `websockets>=12.0` from dev extras to runtime
`dependencies` in pyproject) — lighter than pulling the openai SDK for one WS session, and the
event protocol is small. VERIFY at implementation time (context7: openai realtime docs): current
WS URL (`wss://api.openai.com/v1/realtime?model=...`), auth headers (`Authorization: Bearer` +
whether the beta header `OpenAI-Beta: realtime=v1` is still required for GA), exact event names
and session.update schema shape (fields moved between beta and GA).

### Settings additions (`app/config.py`)
```python
openai_api_key: str = ""
openai_realtime_model: str = "gpt-realtime"          # verify current model id
openai_realtime_voice_default: str | None = None      # optional; DEFAULT_VOICES covers it
openai_realtime_temperature: float = 0.8              # verify allowed range (0.6-1.2 in beta)
```

### Session lifecycle (`OpenAIRealtimeProvider.connect_live` -> `OpenAIRealtimeSession`)
1. Open WS with auth headers; on HTTP 401/403 -> `InvalidRequestError`, 429 -> `RateLimitError`,
   5xx/handshake failure -> `ServiceUnavailableError`.
2. Send `session.update` with: `instructions` = system_instruction, `voice` = voice,
   `input_audio_format`/`output_audio_format` = `pcm16` (24kHz), `input_audio_transcription`
   enabled (model `gpt-4o-transcribe` or `whisper-1` — verify current recommendation), server VAD
   turn detection (`turn_detection: {"type": "server_vad"}`) so the model handles turn-taking like
   Gemini Live does.
3. `send_audio(pcm16_16k)`: run through `PcmResampler(16000, 24000)` (one instance per session),
   base64-encode, send `input_audio_buffer.append`. (Server VAD -> no manual commit needed; verify.)
4. `send_text(text)`: `conversation.item.create` (user message) + `response.create`.
5. `receive()` — event translation table (names to verify):

| OpenAI event | LiveEvent emitted |
|---|---|
| `response.output_audio.delta` (base64) | `{"type": "audio", "audio_data": b64decode(...), "text": None}` |
| `conversation.item.input_audio_transcription.completed` (or `.delta` if streaming transcripts available) | `{"type": "input_transcription", "text": ..., "finished": True, "audio_data": None}` |
| `response.output_audio_transcript.delta` | `{"type": "output_transcription", "text": ..., "finished": False, "audio_data": None}` |
| `response.output_audio_transcript.done` | (nothing extra, or finished-marker — relay only concatenates chunks, so deltas suffice) |
| `response.done` | `{"type": "end", "audio_data": None, "text": None}` |
| `error` event | raise mapped exception (rate-limit vs invalid vs internal by error code) |
| everything else (`session.created`, `input_audio_buffer.speech_started`, `response.created`, ...) | ignored (debug-log) |

Never emits `session_resumption_update` / `go_away` / `internal_reasoning` — relay treats them as
optional. Output audio is 24kHz pcm16 = what the browser already plays; confirm at implementation
time, no outbound resampling expected.

6. `close()`: idempotent WS close.

Timing note for `input_transcription`: OpenAI delivers the user transcript on `...completed`
(async, may arrive after response audio started). The relay accumulates
`_pending_user_transcription` and flushes on `end`, so a whole-utterance single event is fine —
but note ordering: if `completed` arrives after `response.done`, the user turn flushes one turn
late. Mitigation (implement): on receiving `input_audio_transcription.completed`, emit the
`input_transcription` event immediately; acceptable v1 quirk if it trails the assistant text in
transcript ordering. Flag for manual verification.

### Tests (`tests/unit/test_openai_realtime.py`)
Mock the websockets client (AsyncMock with scripted recv sequence): session.update sent with
correct instructions/voice/formats; audio append is base64 of resampled input; each translation
row above; error event mapping; close idempotency. No network.

---

## Phase 5 — Relay integration (provider selection)

### Settings + route
- `app/config.py`: `live_provider: str = "gemini"` (server default),
  `live_provider_allowlist: list[str] = ["gemini"]` (which providers clients may request;
  operators add "openai"/"nova" once keys are configured).
- `app/api/websocket.py`: add `provider: str | None = Query(None)`. Resolution:
  `requested = provider or settings.live_provider`; reject with WS close 4004 if not in
  `LIVE_PROVIDERS` or not in allowlist. Build via `build_live_provider(requested, settings)`
  through a new `get_live_provider` factory in `app/core/dependencies.py` (mirrors
  `get_gemini_service`; gemini keeps reusing the existing cached GeminiService inside its
  provider to avoid double clients).

### `gemini_relay.py` generalization (keep file name and class name aliases; renaming the ws route is out of scope)
- Constructor: `gemini_service: GeminiService` -> `live_provider: LLMStreamProvider` (plus a
  `provider_name` attr from `live_provider.name` for logging/voice resolution). Update
  `websocket.py` construction and `app/api/ws/__init__.py` export accordingly (keep
  `GeminiWebSocketRelay` name to limit churn; optionally alias `LiveWebSocketRelay = ...` — naming
  cleanup is cosmetic, defer).
- Line 218 area: `voice=resolve_voice(persona, self.live_provider.name)`.
- Line 343: `self.gemini_service.connect_live(...)` -> `self.live_provider.connect_live(
  system_instruction=..., voice=..., resumption_handle=...)`.
- `_relay_gemini_to_client` / `_relay_client_to_gemini`: no logic changes — event vocabulary is
  identical; only log wording ("Gemini" -> provider name) if desired.

### Reconnection semantics for non-Gemini providers (v1 stance — document in code)
- `_run_with_reconnection` reconnects only on `go_away`/resumption-handle presence, which
  non-Gemini adapters never produce -> a mid-session OpenAI/Nova drop surfaces as
  `ServiceUnavailableError`/`InternalError` and closes the browser socket with the existing error
  JSON. Conversation context is server-side per session and would be lost on reconnect anyway.
- Optional small improvement (in scope, cheap): allow one fresh-session reconnect for non-Gemini
  providers by setting `self._should_reconnect = True` when the provider session ends with a
  retryable error; the loop already rebuilds `system_instruction` from live agent state
  (`_current_system_instruction`) on reconnect, so the persona resumes with current mood/regard —
  audio conversation history is lost. Accept and log this. Decide during implementation; default
  to the simpler fail-closed if it complicates tests.

### Tests
- `test_gemini_relay.py`: update construction to inject a fake `LLMStreamProvider`; all existing
  assertions stay valid (event vocabulary unchanged).
- New relay tests: provider query param selection, allowlist rejection (close 4004), voice
  resolution per provider name.

---

## Phase 6 — Nova Sonic adapter (`app/llm_providers/nova_sonic.py`) — riskiest, do LAST

Dependency decision: **`aws-sdk-bedrock-runtime` (experimental Smithy Python client)** — it is the
only Python path that supports `InvokeModelWithBidirectionalStream` HTTP/2 duplex streaming;
aiobotocore/botocore cannot do bidirectional streaming, so there is no real tradeoff despite the
"experimental" label. Consequences to plan for:
- Pin the version in pyproject; expect API churn.
- mypy strict: package ships without stubs — add a `[[tool.mypy.overrides]]`
  `ignore_missing_imports = true` block for `aws_sdk_bedrock_runtime.*` / `smithy_*` rather than
  scattering `# type: ignore`.
- VERIFY at implementation time (context7 / AWS docs + amazon-nova-samples repo): exact client
  construction (region, credential resolution via default chain), event class names, the current
  Nova 2 Sonic model id (`amazon.nova-sonic-v1:0` vs a v2 id), voiceId list, and sample-rate
  configs.

### Settings additions
```python
aws_region: str = "us-east-1"                 # credentials via default AWS chain (env/instance role)
nova_sonic_model: str = "amazon.nova-sonic-v1:0"   # verify current id for "Nova 2 Sonic"
```

### Session lifecycle (`NovaSonicSession`)
Nova's protocol is event-scripted JSON over the bidirectional stream:
1. `sessionStart` (inference config: temperature etc.).
2. `promptStart` — includes `audioOutputConfiguration` with `voiceId` = resolved voice,
   sampleRate 24000, LPCM; and text/audio input configs.
3. System prompt: `contentStart(TEXT, role=SYSTEM)` + `textInput(system_instruction)` +
   `contentEnd`.
4. Audio input: one long-lived `contentStart(AUDIO)` then `audioInput` events per chunk
   (base64 LPCM 16kHz mono — browser format matches, **no resampling inbound**).
5. `send_audio(chunk)` -> base64 `audioInput`. `send_text` -> text content block (verify mid-
   session text injection support; if unsupported, raise `InvalidRequestError` — relay's text path
   is secondary).
6. `receive()` translation:

| Nova event | LiveEvent |
|---|---|
| `audioOutput` (base64, 24kHz) | `audio` |
| `textOutput` with role USER (ASR of user speech) | `input_transcription` (finished=True) |
| `textOutput` with role ASSISTANT | `output_transcription` |
| `contentEnd` with stopReason END_TURN / `completionEnd` | `end` |
| `modelStreamErrorException` / validation errors | mapped exceptions |

7. `close()`: send `contentEnd`/`promptEnd`/`sessionEnd` then close stream; idempotent, tolerant
   of already-broken streams.
Concurrency shape: the smithy client separates an input-writer and an output-reader; wrap with an
internal `asyncio.Queue` + writer task so `send_audio`/`receive` present the same simple surface
as the other adapters.
Output is 24kHz -> browser playback unchanged. No resumption/go_away/internal_reasoning events.

### Tests (`tests/unit/test_nova_sonic.py`)
Mock the smithy stream objects (AsyncMock): assert event script order
(sessionStart -> promptStart(voiceId) -> system text block), base64 audio chunk encoding,
each translation row, clean shutdown sequence, error mapping. No AWS calls.

---

## Phase 7 — Verification & definition of done

Without API keys (CI-provable):
- `uv run pytest` green including new suites (protocol conformance, resampler, both adapter suites
  with mocked transports, persona-voice coverage, relay provider-selection); coverage >= 80%.
- `uv run mypy` strict green (with the scoped AWS-SDK override) and `uv run ruff check` green.
- Gemini path regression: existing `test_gemini_relay.py` / `test_gemini_service.py` /
  `test_gemini_live_session.py` pass with no assertion changes beyond constructor injection.

With keys (manual, post-merge checklist — real e2e cannot be automated here):
- One voice session per provider (`?provider=gemini|openai|nova`): hear persona voice, see
  user + assistant transcriptions stream, coach hints fire, evaluation completes.
- OpenAI: confirm output sample rate is 24kHz (playback pitch check) and input-transcription
  ordering quirk is acceptable.
- Nova: confirm voiceIds and model id; validate barge-in behavior parity.

Sequencing summary (each phase leaves the suite green):
1. Phase 1 (voices field + resolve_voice + migrations) — behavior-preserving.
2. Phase 2 (protocol + GeminiLiveProvider + registry) — behavior-preserving.
3. Phase 3 (resampler) — standalone.
4. Phase 4 (OpenAI adapter) + Phase 5 (relay/provider switch) — first real second provider.
5. Phase 6 (Nova) — experimental SDK, isolated behind the same protocol.
6. Phase 7 verification.

Key risks:
- Nova smithy client instability / missing stubs (mitigated: last phase, version pin, scoped mypy
  override, adapter fully mockable).
- OpenAI Realtime beta->GA event renames (mitigated: verify names via context7 before coding;
  translation table centralizes them in one dict).
- Transcription timing differences vs Gemini (relay's accumulate-and-flush-on-end design absorbs
  most of it; noted quirks above).
- `websockets` moving to runtime deps — trivial but must not be forgotten.

## Critical Files for Implementation
- /home/mowgli/ai-ml-sales-coach/backend/app/api/ws/gemini_relay.py
- /home/mowgli/ai-ml-sales-coach/backend/app/agents/state.py
- /home/mowgli/ai-ml-sales-coach/backend/app/agents/personas.py
- /home/mowgli/ai-ml-sales-coach/backend/app/llm_providers/base.py (sibling streaming.py/voices.py/adapters land beside it)
- /home/mowgli/ai-ml-sales-coach/backend/app/config.py
