# Architecture & Design

System design, data models, and architectural decisions.

**Tags:** #architecture #design #system

## Core Architecture

### Data Model
- **[[DATABASE_SCHEMA]]** - Complete Firestore schema, collections, and relationships

### Conversation Architecture
- **[[AGENT_FLOW]]** - Conversation flow, customer personas, and coach hint system
- **[[SESSION_STATE_RESUMPTION]]** - Session persistence and recovery patterns

### Product & Strategy
- **[[PRODUCT_REQUIREMENTS]]** - Vision, goals, target markets, and non-goals
- **[[FUTURE_API_ENDPOINTS]]** - Planned endpoints and feature expansions

## Key Concepts

### Sessions
A **Session** represents one training conversation between a user and an AI customer persona.

- Created before a voice WebSocket connection
- Tracks mode (training vs evaluation)
- Persists to Firestore for analytics and history
- See: [[DATABASE_SCHEMA#Sessions Collection|DATABASE_SCHEMA.md]]

### Agent Flow
Two main agents interact during conversations:

1. **Customer Agent** - Simulates customer personas (Assistant, Executive, Skeptic)
2. **Coach Agent** - Generates real-time hints and post-session evaluations

See: **[[AGENT_FLOW]]** for detailed flow

### E.A.S.Y. Selling System
The coaching framework underlying all evaluations.

- **E** - Establish rapport
- **A** - Ask qualifying questions
- **S** - Share solutions
- **Y** - Yield agreement

Tracked in evaluations and hint generation.

## API Contracts

See **[[API_SPECIFICATION|../API%20Documentation/API_SPECIFICATION.md]]** for REST and WebSocket endpoints.

## Design Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Gemini Live API | Real-time voice, low-latency | WebSocket relay needed, 30min timeout handling |
| Firestore | Serverless, vector search | Document-based schema, no migrations |
| OAuth 2.0 | Secure, federated identity | JWT tokens, refresh flow |
| E.A.S.Y. Framework | Sales methodology | Evaluation criteria, hint generation |

## Related Sections

- **[[Getting Started|../Getting%20Started/index.md]]** - Setup before development
- **[[API Documentation|../API%20Documentation/index.md]]** - Endpoint details
- **[[Infrastructure|../Infrastructure/index.md]]** - Deployment implications

---

**Architecture questions?** Check [[ADMIN_TROUBLESHOOTING|../Features/ADMIN_TROUBLESHOOTING.md]] or [[AGENT_FLOW]] for details.
