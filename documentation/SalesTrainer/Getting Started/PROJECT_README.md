# Luxe Sales Coach v2

![Backend CI](https://github.com/afi-internal/ai-ml-sales-coach/actions/workflows/backend-ci.yml/badge.svg)
![Frontend CI](https://github.com/afi-internal/ai-ml-sales-coach/actions/workflows/frontend-ci.yml/badge.svg)
![Backend Deploy](https://github.com/afi-internal/ai-ml-sales-coach/actions/workflows/backend-deploy.yml/badge.svg)
![Frontend Deploy](https://github.com/afi-internal/ai-ml-sales-coach/actions/workflows/frontend-deploy.yml/badge.svg)

AI-native sales training platform using Gemini Live API for real-time voice roleplay with customer personas. Built with LangGraph multi-agent architecture for dynamic customer simulation and real-time coaching feedback.

## Overview

This repository contains a complete full-stack application for training sales representatives in the "E.A.S.Y. Selling System" methodology through immersive conversations with AI-powered customer personas. The system uses two LangGraph-based agents:

1. **Customer Agent**: Simulates realistic customer personas (Assistant, Executive, Skeptic) with difficulty-tuned behavior and objection handling
2. **Coach Agent**: Provides real-time coaching hints and post-session performance evaluation based on E.A.S.Y. methodology

## Repository Structure

```
luxe-sales-coach-v2/
├── backend/                    # FastAPI backend (Python 3.11+)
│   ├── app/
│   │   ├── agents/            # LangGraph agents (customer & coach)
│   │   ├── api/               # REST endpoints and WebSocket relay
│   │   ├── services/          # Business logic (auth, Gemini, sessions)
│   │   ├── models/            # Pydantic schemas
│   │   └── core/              # Infrastructure (logging, exceptions)
│   ├── tests/                 # 434 tests with 90%+ coverage
│   ├── pyproject.toml         # Python dependencies
│   └── README.md              # Backend documentation
│
├── frontend/                   # React + TypeScript frontend
│   ├── src/
│   │   ├── components/        # UI components (CoachHUD, EASYChecklist)
│   │   ├── pages/             # Routes (Home, Session, Login)
│   │   ├── hooks/             # WebSocket and audio hooks
│   │   ├── services/          # API clients and auth
│   │   └── types/             # TypeScript definitions
│   ├── package.json           # npm dependencies
│   └── README.md              # Frontend documentation
│
├── documentation/             # API specs and architecture
│   ├── API_SPECIFICATION.md   # REST and WebSocket endpoints
│   ├── DATABASE_SCHEMA.md     # Firestore schema design
│   └── cutfeatures.md         # Historical feature archive
│
└── README.md                  # This file
```

## Getting Started

### Backend Setup

```bash
cd backend
uv sync
cp .env.example .env
# Configure environment variables (GEMINI_API_KEY, OAuth credentials, etc.)
uv run uvicorn app.main:app --reload --port 8000
```

Backend runs on `http://localhost:8000` with Swagger docs at `/docs`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`. Vite proxies API calls to backend.

## Architecture Highlights

### LangGraph Multi-Agent System

The backend uses LangGraph to build two specialized agents:

**Customer Agent** (`backend/app/agents/customer_agent.py`)
- Implements a stateful conversation graph using `StateGraph` and `MemorySaver`
- Three configurable personas with difficulty levels (Basic, Intermediate, Advanced)
- Handles objections dynamically based on conversation context
- Maintains conversation state for multi-turn interactions

**Coach Agent** (`backend/app/agents/coach/`)
- Analyzes each sales turn in real-time
- Generates contextual coaching hints during active sessions
- Provides post-session scoring and E.A.S.Y. checklist verification
- Components: scorer (grading), hints (guidance), analyzer (intent detection)

### Real-Time Voice Pipeline

1. **Client** -> Records audio (16kHz PCM) via browser audio API
2. **Frontend** -> WebSocket connection with JWT auth
3. **Backend Relay** -> Bidirectional streaming to Gemini Live API
4. **Coach Service** -> Real-time hint generation (async, non-blocking)
5. **Backend** -> Streams audio response (24kHz PCM) back to client
6. **Client** -> Plays audio in real-time

### Data Persistence

- **Firestore**: Session data, transcripts, evaluations (development)
- **PostgreSQL**: Production database (configured via environment & pending)
- **JWT**: Token-based authentication with refresh support

## Key Features

- **Google OAuth 2.0**: Secure sign-in for sales representatives
- **Gemini Live API**: Real-time bidirectional audio streaming with 30-minute timeout
- **E.A.S.Y. Framework**: Interactive checklist tracking (Engagement, Ask, Satisfaction, Yes)
- **Customer Personas**: Three AI-powered personas with objection handling
- **CoachHUD**: Live coaching hints displayed during sessions
- **Session Evaluation**: Post-session scoring and performance feedback
- **Transcript Storage**: Full conversation records for review and analysis
- **Type Safety**: Full TypeScript + Python type hints with strict type checking

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19, TypeScript, Vite | UI and user interactions |
| **Backend** | FastAPI, Python 3.11 | REST API and WebSocket relay |
| **Agents** | LangGraph, LangChain, Gemini | Customer simulation and coaching |
| **Voice AI** | Gemini Live API | Real-time voice conversation |
| **Database** | Firestore / PostgreSQL(pending) | Session persistence |
| **Auth** | Google OAuth 2.0, JWT | Secure authentication |
| **Infrastructure** | Docker, Cloud Run | Production deployment |

## Development Workflow

1. **Backend Development** (Python)
   ```bash
   cd backend
   uv run pytest                    # Run tests
   uv run ruff check . --fix        # Lint and format
   uv run mypy app/                 # Type check
   ```

2. **Frontend Development** (TypeScript)
   ```bash
   cd frontend
   npm run test                     # Run tests
   npm run typecheck                # Type check
   npm run build                    # Production build
   ```

3. **Git Workflow**
   - Use worktrees for feature branches: `git worktree add -b feat/x ../wt-x origin/main`
   - Keep commits small and focused
   - Use conventional commit messages: `feat:`, `fix:`, `chore:`

## Testing & Quality

- **Backend**: 434 tests, 90%+ coverage (pytest + unittest)
- **Frontend**: 47+ tests (Vitest + React Testing Library)
- **Linting**: ruff (100 char line length)
- **Type Checking**: mypy (Python strict mode), TypeScript strict mode
- **E2E**: WebSocket integration tests with mock Gemini API

## Deployment

### Docker

```bash
docker-compose up
```

### Cloud Run

```bash
# Backend
gcloud run deploy luxe-sales-coach-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file .env

# Frontend (static hosting via Cloud Storage + Cloud Load Balancer)
npm run build
gsutil -m cp -r frontend/dist/* gs://luxe-sales-coach-frontend/
```

## Documentation

- **Backend**: `backend/README.md` - Architecture, API overview, development setup
- **Frontend**: `frontend/README.md` - Component architecture, hooks, testing
- **API Spec**: `documentation/API_SPECIFICATION.md` - Complete REST and WebSocket endpoints
- **Database**: `documentation/DATABASE_SCHEMA.md` - Firestore collections and schema
- **Features Archive**: `documentation/cutfeatures.md` - Historical feature reference

## Code Standards

- **Language Versions**: Python 3.11+, TypeScript 5.8+
- **Package Managers**: uv (backend), npm (frontend)
- **Formatting**: ruff format (Python), Prettier (TypeScript)
- **Type Safety**: Full type coverage required on all functions
- **Testing**: 80%+ coverage minimum, 100% for critical paths

## Support & Contribution

Michael Puerto, Ritesh Tewary, Colton Nobles
Jason Osajima, Amelia Loving

---

**Status**: In-progress
**Last Updated**: February 5, 2026
**Version**: 2.0.0
