# Backend: Luxe Sales Coach v2

FastAPI backend for real-time voice roleplay training using Gemini Live API.

## Getting Started

### Prerequisites
- Python 3.11+
- uv package manager
- Google Cloud Project with Gemini API key

### Setup

```bash
cd backend
uv sync
cp .env.example .env
# Edit .env with your credentials
uv run uvicorn app.main:app --reload --port 8000
```

Backend runs on `http://localhost:8000`. Swagger docs available at `/docs`.

## Architecture

```
Backend (FastAPI + Python 3.11)
|
├── API Routes
|   ├── /auth/* - Google OAuth and session management
|   ├── /api/v1/* - Core application endpoints
|   ├── /ws/gemini/live - WebSocket for real-time voice
|   └── /health - Health check
|
├── Core Components
|   ├── Authentication
|   |   ├── authService - OAuth flow, token management
|   |   ├── tokenRepository - JWT token storage
|   |   └── userRepository - User data persistence
|   |
|   ├── Voice Sessions
|   |   ├── geminiService - Gemini Live API client
|   |   ├── sessionService - Session lifecycle management
|   |   ├── geminiRelay - WebSocket relay (audio streaming)
|   |   └── sessionRepository - Session persistence
|   |
|   ├── Conversation Tracking
|   |   ├── transcriptRepository - Transcript storage
|   |   ├── customerAgentService - Customer persona simulation
|   |   └── transcript models - Conversation data
|   |
|   └── Coaching & Evaluation
|       ├── coachAgentService - Real-time hint generation
|       ├── coachService (scorer, analyzer, hints)
|       ├── evaluationService - Post-session scoring
|       ├── evaluationRepository - Evaluation storage
|       └── coach models - Evaluation data structures
|
├── Data & Configuration
|   ├── /data/
|   |   ├── easy_system.py - E.A.S.Y. selling methodology
|   |   └── objections.py - Common sales objections
|   ├── /agents/
|   |   ├── coach/ - Coach agent (scorer, hints, prompts)
|   |   └── customer/ - Customer agent (personas, behavior)
|   └── models/ - Pydantic schemas for all domains
|
└── Infrastructure
    ├── logging - Structured JSON logging
    ├── exceptions - Custom error handling
    ├── middleware - Request/response processing
    ├── dependencies - FastAPI dependency injection
    └── session - CSRF and session state management

Data Flow:
  Client WebSocket -> Relay -> Gemini Live API -> Relay -> Client
    ^                                                        |
    |________ Real-time Coach Hints (via Coach Service) ___|
```

## Key Features

- **Google OAuth 2.0**: Secure authentication with JWT tokens
- **Gemini Live API**: Real-time bidirectional audio streaming
- **WebSocket Relay**: 30-minute session timeout, reconnection support
- **Customer Personas**: 3 personas (Assistant, Executive, Skeptic) with difficulty levels
- **Coach Agent**: Real-time hint generation and turn-by-turn analysis
- **Session Evaluation**: Post-session scoring and E.A.S.Y. checklist verification
- **Transcript Storage**: Full session transcripts via Firestore
- **Error Handling**: Custom WebSocket close codes (4001-4005) for client handling

## Development

### Commands

```bash
uv sync                          # Install dependencies
uv run uvicorn app.main:app --reload --port 8000  # Start dev server
uv run pytest                    # Run all tests
uv run pytest tests/unit/        # Unit tests only
uv run pytest --cov=app          # With coverage
uv run ruff check .              # Lint
uv run ruff format .             # Format
uv run mypy app/                 # Type check
```

### Project Structure

```
backend/
├── app/
|   ├── api/                  # FastAPI routes
|   |   ├── auth.py          # Authentication endpoints
|   |   ├── gemini.py        # Gemini API proxy
|   |   ├── health.py        # Health check
|   |   ├── personas.py      # Persona data
|   |   ├── websocket.py     # WebSocket router
|   |   └── ws/
|   |       └── gemini_relay.py   # Audio relay logic
|   |
|   ├── services/            # Business logic
|   |   ├── auth_service.py
|   |   ├── gemini_service.py
|   |   ├── session_service.py
|   |   ├── customer_agent_service.py
|   |   └── coach_agent_service.py
|   |
|   ├── repositories/        # Database access
|   |   ├── user_repository.py
|   |   ├── token_repository.py
|   |   ├── session_repository.py
|   |   ├── transcript_repository.py
|   |   └── evaluation_repository.py
|   |
|   ├── models/              # Pydantic schemas
|   |   ├── user.py
|   |   ├── auth.py
|   |   ├── session.py
|   |   ├── transcript.py
|   |   ├── coach.py
|   |   ├── evaluation.py
|   |   └── gemini.py
|   |
|   ├── agents/              # Agent logic
|   |   ├── coach/          # Coach agent (scorer, hints)
|   |   ├── customer/       # Customer agent (personas)
|   |   ├── prompts.py      # LLM prompts
|   |   ├── state.py        # Conversation state
|   |   └── personas.py     # Persona definitions
|   |
|   ├── data/               # Static data
|   |   ├── easy_system.py  # E.A.S.Y. methodology
|   |   └── objections.py   # Sales objections
|   |
|   ├── core/               # Infrastructure
|   |   ├── logging.py      # Structured logging
|   |   ├── exceptions.py   # Error definitions
|   |   ├── middleware.py   # Request middleware
|   |   ├── dependencies.py # FastAPI DI
|   |   └── session.py      # Session management
|   |
|   ├── config.py           # Settings (pydantic-settings)
|   └── main.py             # FastAPI app entry
|
├── tests/
|   ├── unit/               # Unit tests
|   ├── integration/        # Integration tests
|   └── conftest.py        # Test fixtures
|
├── scripts/
|   ├── verify_firestore.py # Firestore connectivity check
|   └── test_gemini_idle_timeout.py # Performance testing
|
├── pyproject.toml         # Dependencies and tool config
├── .env.example           # Environment variables template
└── README.md              # This file
```

## API Overview

### Authentication

```
GET  /auth/login           # Redirect to Google OAuth
POST /auth/login           # Get OAuth URL (SPA)
GET  /auth/callback        # OAuth callback (browser)
POST /auth/callback        # OAuth callback (SPA)
POST /auth/refresh         # Refresh token
GET  /auth/me              # Get current user
POST /auth/logout          # Logout
```

### Voice Sessions

```
WebSocket /ws/gemini/live  # Real-time audio streaming
  ?token=<jwt>             # Authentication via query param
  &mode=training|evaluation # Session mode
```

### Data & Evaluation

```
GET  /api/v1/personas       # List available personas
POST /api/v1/sessions       # Create session
GET  /api/v1/sessions/:id   # Get session details
POST /api/v1/evaluate       # Generate evaluation
```

## Testing

434 tests with 90%+ coverage:
- Auth: 100% coverage
- Gemini API: 100% coverage
- WebSocket relay: 16 unit + 9 integration tests
- Session management: 29 tests
- Coach agent: 60+ tests (scorer, hints, evaluation)
- Customer agent: 40+ tests (personas, behavior)

Run tests:

```bash
uv run pytest                  # All tests
uv run pytest -k coach         # Coach agent tests only
uv run pytest --cov=app        # With coverage report
```

## Environment Variables

See `.env.example` for full list. Required:

### Core Configuration
```
GEMINI_API_KEY             # Google AI API key
GOOGLE_CLIENT_ID           # OAuth client ID
GOOGLE_CLIENT_SECRET       # OAuth client secret
FIREBASE_PROJECT_ID        # Firestore project
FIREBASE_PRIVATE_KEY       # Service account key
FIREBASE_CLIENT_EMAIL      # Service account email
```

### Microsoft Azure/Entra ID (Optional)
Enable alternative OAuth provider for enterprise deployments:

```
AZURE_OAUTH_CLIENT_ID      # Azure Entra ID application ID
AZURE_OAUTH_CLIENT_SECRET  # Azure Entra ID client secret
AZURE_OAUTH_TENANT_ID      # Azure Entra ID tenant ID
```

### Email Domain Allowlist (Optional)
Restrict OAuth login to specific email domains:

```
EMAIL_DOMAIN_ALLOWLIST     # Comma-separated list of allowed domains (e.g., "example.com,company.com")
```

### RAG Configuration (Optional)
Enable product knowledge retrieval for enhanced coach hints:

```
RAG_ENABLED                # Set to "true" to enable RAG pipeline
RAG_COLLECTION_NAME        # Firestore collection for vectors (default: "knowledge_chunks")
RAG_EMBEDDING_MODEL        # Model for embeddings (default: "gemini-embedding-001")
RAG_TOP_K                  # Number of results to return (default: 3)
RAG_USE_HYBRID_SEARCH      # Enable hybrid semantic + keyword search (default: false)
RAG_USE_RERANKING          # Enable LLM re-ranking of results (default: false)
RAG_USE_CONVERSATION_CONTEXT  # Include full conversation in retrieval (default: false)
RAG_USE_OBJECTION_LOOKUP   # Enable objection database lookup (default: true)
```

```

## Deployment

Build Docker image:

```bash
docker build -t luxe-sales-coach-backend .
docker run -p 8000:8000 --env-file .env luxe-sales-coach-backend
```

Or use docker-compose:

```bash
docker-compose up
```

## Code Style

- **Linting**: ruff (line-length: 100)
- **Formatting**: ruff format
- **Type Checking**: mypy (strict mode)
- **Testing**: pytest with 80%+ coverage requirement

Run all checks:

```bash
uv run ruff check . && uv run ruff format . && uv run mypy app/ && uv run pytest
```
