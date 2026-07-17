# SalesTrainer Pro

Universal sales-training platform for real-time voice roleplay against AI customer personas across any industry (real estate, SaaS, insurance, automotive, B2B/B2C). Reps practice live conversations and get scored against the **C.O.R.E. Selling System**, with turn-by-turn coaching hints and post-session evaluation.

## Monorepo layout

| Path | What | Stack |
|------|------|-------|
| [`frontend/`](frontend/README.md) | Voice roleplay SPA + manager/admin dashboards | React 19, TypeScript, Vite |
| [`backend/`](backend/README.md) | API, auth, real-time speech relay, coach/eval agents | FastAPI, Python 3.13, `uv` |
| [`terraform/`](terraform/README.md) | GCP infrastructure as code | Terraform, Cloud Run/Firestore |
| [`.github/workflows/`](.github/workflows/README.md) | CI + Cloud Run deploys | GitHub Actions (WIF, keyless) |

## Stack

- **Frontend** — React 19 + Vite SPA. WebSocket audio (16 kHz capture / 24 kHz playback), Google OAuth, dashboards.
- **Backend** — FastAPI. Google OAuth + JWT, Firestore persistence, LangGraph coach agents, RAG over Firestore vector indexes, Langfuse LLM tracing, and an eval harness.
- **Real-time voice** — Multi-provider speech-to-speech relay behind one WebSocket. Providers: **Gemini Live** (local default), **Amazon Nova Sonic** (production default), **OpenAI Realtime**. Selectable per-session via `?provider=`, gated by `LIVE_PROVIDER_ALLOWLIST`.
- **Infra** — GCP Cloud Run (`salestrainer-pro-backend` / `salestrainer-pro-frontend`), Firestore Native, Secret Manager, Artifact Registry. Project `salescoach-494901`, region `us-central1`.

## Quickstart (local)

Backend and frontend run as two processes. See the subdir READMEs for env vars and detail.

```bash
# Backend  -> http://localhost:8000  (Swagger at /docs)
cd backend && uv sync && cp .env.example .env   # fill in credentials
uv run uvicorn app.main:app --reload --port 8000

# Frontend -> http://localhost:3000  (Vite proxies API + WS to :8000)
cd frontend && npm install && npm run dev
```

Local default live-voice provider is Gemini (needs `GEMINI_API_KEY`); Nova/OpenAI require their respective credentials.

## Deploy / architecture

Merges to `main` trigger path-filtered GitHub Actions that build a Docker image, push to Artifact Registry, and `gcloud run deploy` — backend and frontend independently. Auth is keyless via Workload Identity Federation (no long-lived SA keys). Runtime config (secrets, env, provider allowlist, CORS/OAuth redirect) is set on the deploy command, not baked into the image; Terraform only bootstraps the service shell + IAM and deliberately ignores CI-managed fields. See [`.github/workflows/README.md`](.github/workflows/README.md) and [`terraform/README.md`](terraform/README.md).

Request path at runtime: browser ⇄ frontend (Cloud Run) ⇄ backend WebSocket relay ⇄ live-voice provider, with coach hints streamed back on the same socket and transcripts/evaluations written to Firestore.
