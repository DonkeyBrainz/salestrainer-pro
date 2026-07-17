# Backend — SalesTrainer Pro

FastAPI (Python 3.13+, `uv`) backend for real-time speech-to-speech sales roleplay. Multi-provider live voice (Gemini / OpenAI Realtime / Nova Sonic), OAuth+JWT auth, Firestore persistence, LangGraph coach/customer agents, optional RAG, Langfuse tracing.

## Run

```bash
uv sync                                   # add --extra nova for Nova Sonic
cp .env.example .env                      # fill secrets — source of truth is app/config.py
uv run uvicorn app.main:app --reload --port 8000
```

Swagger at `/docs`. See root `CLAUDE.md` for the full command reference (test/lint/type-check).

## Architecture

The client streams 16kHz PCM over `WS /ws/gemini/live`. The route resolves a live provider from `app/llm_providers/registry.py` (`LIVE_PROVIDERS`, gated by `Settings.live_provider_allowlist`), and `app/api/ws/gemini_relay.py` bridges the browser socket to the provider's bidirectional stream. In `training` mode the coach agent pushes turn-by-turn hints back down the same socket; `evaluation` mode is silent and scored post-session.

Live voice = one-shot persona prompt only. The LangGraph mood/analysis graph is analytics-only and never feeds the live persona — see `app/agents/`.

Key subsystems:
- **`app/llm_providers/`** — provider adapters behind a registry. Live speech-to-speech: `gemini_live`, `openai_realtime`, `nova_sonic`. Text/ASR (eval + coach): `gemini`, `bedrock_text` (Nova/Voxtral via Bedrock Converse), `voxtral`, `nova`. Shared: `streaming.py` (LiveEvent vocabulary), `audio.py`, `voices.py`, `aws_credentials.py`.
- **`app/agents/`** — `customer_agent.py` (persona graph, mood ladder, objection injection), `coach/` (`analyzer`, `scorer`, `hints`), `personas.py`, `prompts.py`, `state.py`.
- **`app/services/`** — auth, session, customer/coach agent orchestration, `rag_service`, `objection_service`, org/user stats.
- **`app/repositories/`** — Firestore data access (`base.py` + user/token/session/transcript/evaluation/store).
- **`app/data/`** — `core_system.py` (C.O.R.E. = Connect, Observe, Recommend, Execute), `objections.py`.
- **`app/core/`** — infra (exceptions, logging, middleware, DI, RBAC, session). See `core/README.md`.

## Routes

Registered in `app/main.py`:

```
/health                                   health
/auth/*                                   Google OAuth + JWT (login/callback/refresh/me/logout)
/api/v1/* (gemini)                        Gemini proxy
/personas, /products, /sessions, /users   core resources
/organizations, /admin                    org/admin (RBAC-gated, manager+)
WS /ws/gemini/live?token=&mode=&provider= real-time voice
```

`mode` = `training` | `evaluation`. `provider` optional (`gemini` | `openai` | `nova`), defaults to `Settings.live_provider`.

## Errors

All handlers in `app/main.py`. Custom exceptions inherit `app.core.exceptions.AppError` (code + HTTP status + details) and serialize to:

```json
{ "error": { "code": "NOT_FOUND", "message": "...", "details": [], "requestId": "..." } }
```

WebSocket failures use custom close codes (4001–4005).

## Tracing

Langfuse wraps `GeminiProvider._generate`. `get_settings()` mirrors `LANGFUSE_*` from Settings into `os.environ` (the SDK reads env directly). Init failure is non-fatal — the app runs untraced.

## Deployment

```bash
docker build -t salestrainer-backend .
docker run -p 8000:8000 --env-file .env salestrainer-backend
```

Production runs `LIVE_PROVIDER=nova` for latency (needs `uv sync --extra nova` + AWS creds with `bedrock:InvokeModel*`). Provider trade-offs are benched by the voice eval suite — see `evals/README.md`.
