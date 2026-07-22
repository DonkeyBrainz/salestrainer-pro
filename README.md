# SalesTrainer Pro

> Most training tools look like a settings page with a microphone bolted on. We wanted the opposite: a place you *enter* — the whole product as a drafting table, a blueprint of a training floor where every dashboard is a room you walk into.
Universal sales-training platform for real-time voice roleplay against AI customer personas across any industry (real estate, SaaS, insurance, automotive, B2B/B2C). Reps practice live conversations and get scored against the **C.O.R.E. Selling System**, with turn-by-turn coaching hints and post-session evaluation.

## Monorepo layout

| Path | What | Stack |
|------|------|-------|
| [`frontend/`](frontend/README.md) | Voice roleplay SPA + manager/admin dashboards | React 19, TypeScript, Vite |
| [`backend/`](backend/README.md) | API, auth, real-time speech relay, coach/eval agents | FastAPI, Python 3.13, `uv` |
| [`terraform/`](terraform/README.md) | GCP infrastructure as code | Terraform, Cloud Run/Firestore |
| [`.github/workflows/`](.github/workflows/README.md) | CI + Cloud Run deploys | GitHub Actions (WIF, keyless) |


# The Voiceprint direction — design walkthrough

![The Voiceprint direction — design walkthrough](screenshots/readme/design-note.png)
