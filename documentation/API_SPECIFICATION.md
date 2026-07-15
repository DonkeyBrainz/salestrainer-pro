# API Specification: SalesTrainer Pro Backend

> **Version:** 2.1.0
> **Last Updated:** 2026-07-02
> **Status:** Current
> **Base URL:** Cloud Run service URL (production) / `http://localhost:8000` (development)

---

## Overview

This document defines the REST and WebSocket API for the SalesTrainer Pro backend. All endpoints follow REST conventions and return JSON responses.

### API Conventions

- **Authentication:** Bearer token in `Authorization` header (unless noted)
- **Content-Type:** `application/json` for all requests/responses
- **Timestamps:** ISO 8601 format
- **IDs:** UUID v4 format
- **Errors:** Standard error response format (see Error Handling section)

---

## Table of Contents

1. [Health & Monitoring](#1-health--monitoring)
2. [Authentication](#2-authentication)
3. [Gemini API Proxy](#3-gemini-api-proxy)
4. [Voice Sessions (WebSocket)](#4-voice-sessions-websocket)
5. [Personas](#5-personas)
6. [Admin Endpoints](#6-admin-endpoints)
7. [Products Endpoint](#7-products-endpoint)
8. [Sessions Endpoint](#8-sessions-endpoint)
9. [Error Handling](#9-error-handling)
10. [WebSocket Protocol](#10-websocket-protocol)

---

## 1. Health & Monitoring

### GET /health

Basic health check. No authentication required.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2026-02-05T12:00:00Z"
}
```

---

### GET /ready

Readiness check with dependency status. No authentication required.

**Response:** `200 OK`
```json
{
  "status": "ready",
  "checks": {
    "database": true,
    "geminiApi": true,
    "secretManager": true
  },
  "timestamp": "2026-02-05T12:00:00Z"
}
```

**Response (Degraded):** `503 Service Unavailable`
```json
{
  "status": "degraded",
  "checks": {
    "database": true,
    "geminiApi": false,
    "secretManager": true
  },
  "timestamp": "2026-02-05T12:00:00Z"
}
```

---

## 2. Authentication

All voice sessions require JWT authentication. OAuth provides both access and refresh tokens.

### POST /auth/login

Initiate Google OAuth flow. Returns authentication URL.

**Request (SPA flow):**
```json
{
  "redirectUri": "http://localhost:3000/auth/callback"
}
```

**Response:** `200 OK`
```json
{
  "authUrl": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random-csrf-state"
}
```

**Errors:**
- `400` - Invalid redirect URI

---

### GET /auth/login

Browser-based OAuth flow redirect. Returns HTTP 307 redirect to Google OAuth.

**Response:** `307 Temporary Redirect`
```
Location: https://accounts.google.com/o/oauth2/v2/auth?...
```

---

### POST /auth/callback

Handle OAuth callback from Google. Exchange authorization code for JWT tokens (SPA flow).

**Request:**
```json
{
  "code": "authorization-code-from-google",
  "state": "random-csrf-state"
}
```

**Response:** `200 OK`
```json
{
  "accessToken": "eyJhbGciOiJSUzI1NiIs...",
  "refreshToken": "refresh-token-string",
  "expiresIn": 3600,
  "tokenType": "Bearer",
  "user": {
    "userId": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

**Errors:**
- `400` - Invalid state parameter (CSRF attack prevention)
- `401` - Authorization code expired or invalid
- `500` - Token exchange failed

---

### GET /auth/callback

Browser-based OAuth callback handler. Exchanges code and redirects to frontend (browser flow).

**Query Parameters:**
- `code` (required) - Authorization code from Google
- `state` (required) - CSRF state token

**Response:** `302 Found` or `400 Bad Request`
```
Location: http://localhost:3000/?token=<accessToken>&user=<userId>
```

---

### POST /auth/refresh

Refresh an expired access token using a valid refresh token.

**Request:**
```json
{
  "refreshToken": "refresh-token-string"
}
```

**Response:** `200 OK`
```json
{
  "accessToken": "eyJhbGciOiJSUzI1NiIs...",
  "expiresIn": 3600,
  "tokenType": "Bearer"
}
```

**Errors:**
- `401` - Invalid or expired refresh token

---

### GET /auth/me

Get current authenticated user profile. **Requires authentication.**

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response:** `200 OK`
```json
{
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "name": "John Doe",
  "createdAt": "2026-01-15T10:00:00Z"
}
```

**Errors:**
- `401` - Invalid or missing token

---

### POST /auth/logout

Invalidate current session and revoke refresh token. **Requires authentication.**

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response:** `200 OK`
```json
{
  "success": true
}
```

---

## 3. Gemini API Proxy

### POST /api/v1/gemini/generate

Non-streaming text generation via Gemini. **Requires authentication.**

**Request:**
```json
{
  "prompt": "Explain the C.O.R.E. selling system",
  "model": "gemini-2.5-flash",
  "temperature": 0.7,
  "maxTokens": 1024,
  "systemInstruction": "You are a sales training expert."
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| prompt | string | Yes | - | User prompt text |
| model | string | No | gemini-2.5-flash | Gemini model ID |
| temperature | number | No | 0.7 | Creativity (0.0-1.0) |
| maxTokens | number | No | 1024 | Max output tokens |
| systemInstruction | string | No | - | System context |

**Response:** `200 OK`
```json
{
  "text": "The C.O.R.E. selling system consists of four stages: Connect, Observe, Recommend, Execute...",
  "finishReason": "STOP",
  "inputTokens": 42,
  "outputTokens": 128
}
```

**Errors:**
- `400` - Invalid parameters
- `401` - Invalid or missing token
- `429` - Rate limit exceeded
- `500` - Gemini API error

---

## 4. Voice Sessions (WebSocket)

Real-time bidirectional audio streaming for voice roleplay training. Managed entirely via WebSocket connection (no HTTP endpoints for CRUD).

### WebSocket /ws/gemini/live

Establish real-time voice session with Gemini Live API. Supports multi-provider voice output (Gemini, OpenAI, Google Nova) negotiated at connection time.

**Connection Query Parameters:**
- `token` (required) - JWT authentication token
- `mode` (required) - `training` or `evaluation`
- `persona` (optional) - Customer persona ID (e.g., `anxious_first_timer`, `wealthy_skeptic`)
- `voice_provider` (optional) - Voice provider preference (`gemini`, `openai`, `nova`). Defaults to `gemini`.

**Example URL:**
```
ws://localhost:8000/ws/gemini/live?token={accessToken}&mode=training&persona=anxious_first_timer&voice_provider=gemini
```

**Voice Provider Mapping:**
Each persona supports multiple voice providers. The connection parameter selects which provider's voice will be used:

| Provider | Audio Quality | Latency | Use Case |
|----------|---------------|---------|----------|
| `gemini` | High | Low | Real-time roleplay, default |
| `openai` | Very High | Medium | Premium audio quality |
| `nova` | High | Low | Cost-optimized alternative |

**Features:**
- JWT authentication via query parameter
- Multi-provider voice support (negotiated at connection)
- Bidirectional audio streaming (PCM 16kHz input, 24kHz output)
- Text message support for control commands
- Real-time coaching hints (training mode only)
- 30-minute idle timeout
- Automatic reconnection support
- Full conversation transcription

See [WebSocket Protocol](#10-websocket-protocol) for message formats and error handling.

---

## 5. Personas

### GET /personas

List available customer personas for roleplay. No authentication required.

**Response:** `200 OK`
```json
{
  "personas": [
    {
      "id": "anxious_first_timer",
      "name": "Jennifer",
      "backstory": "28-year-old teacher, engaged, saving for first home. Never owned property before.",
      "looking_for": "First home, 3-bedroom, move-in ready, under $300K",
      "difficulty": "medium_regard",
      "initial_regard": "low",
      "timeline": "urgent",
      "primary_pbm": "confidence",
      "secondary_pbm": "value",
      "objections": [
        "What if the roof breaks after I buy it?",
        "How do I know this is a good deal?",
        "I need to have my parents look at it first",
        "The inspector said the foundation is 'old' — is that a problem?"
      ],
      "voices": {
        "gemini": "aoede",
        "openai": "coral",
        "nova": "tiffany"
      },
      "product_category": "primary_residence",
      "product_type": "starter_home",
      "product_keywords": ["first-time buyer", "confidence", "inspection", "parents", "wedding"]
    },
    {
      "id": "wealthy_skeptic",
      "name": "David",
      "backstory": "58-year-old tech executive, made his money in startups. Distrusts salespeople.",
      "looking_for": "Luxury home, 5+ bedrooms, golf course area, under $700K",
      "difficulty": "low_regard",
      "initial_regard": "low",
      "timeline": "flexible",
      "primary_pbm": "authenticity",
      "secondary_pbm": "investment value",
      "objections": [
        "Why is this worth $685K when the house two streets over is $620K?",
        "I'm not paying a premium just for the neighborhood name",
        "That HOA fee is ridiculous"
      ],
      "voices": {
        "gemini": "charon",
        "openai": "ash",
        "nova": "matthew"
      },
      "product_category": "luxury_estate",
      "product_type": "large_single_family"
    }
  ]
}
```

**Persona Fields:**

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique persona identifier |
| name | string | Customer's first name |
| backstory | string | Brief background context |
| looking_for | string | What they're searching for |
| difficulty | enum | `high_regard`, `medium_regard`, `low_regard`, `no_regard` |
| initial_regard | enum | Starting engagement level (`high`, `medium`, `low`, `no`) |
| timeline | enum | Purchase urgency (`urgent`, `medium`, `flexible`, `browsing`) |
| primary_pbm | string | Primary buying motivation |
| secondary_pbm | string | Secondary motivation (optional) |
| objections | array | Curated list of objections this persona may raise |
| voices | object | Provider-keyed voice IDs: `{"gemini": "...", "openai": "...", "nova": "..."}` |
| product_category | string | Category for RAG filtering (e.g., `primary_residence`, `luxury_estate`) |
| product_type | string | Specific type within category (e.g., `starter_home`, `duplex`) |
| product_keywords | array | Keywords for content retrieval |

---

### GET /personas/evaluation

List personas available for evaluation mode. No authentication required.

**Response:** `200 OK` (same format as `/personas`)

---

## 6. Admin Endpoints

Admin-only endpoints for metrics, analytics, and session management, under `backend/app/api/admin.py`. Restricted via an `ADMIN_EMAILS` allowlist (`require_admin` dependency) — not a role field on the user record.

### GET /api/v1/admin/personas/metrics

Aggregate persona performance metrics across all sessions and transcripts.

**Authentication:** Required (admin email allowlist)

**Response:** `200 OK`
```json
{
  "totalSessions": 156,
  "totalTranscripts": 148,
  "byPersona": [
    {
      "personaId": "executive",
      "sessions": 42,
      "messageCount": 310,
      "volunteerScore": 0.62,
      "firstMessageVolunteerRate": 0.35,
      "salesModeViolations": 2,
      "volunteerCategories": {"needs": 18, "budget": 7}
    }
  ],
  "byDifficulty": [
    {
      "difficulty": "intermediate",
      "sessions": 58,
      "messageCount": 402,
      "volunteerScore": 0.58,
      "firstMessageVolunteerRate": 0.30
    }
  ]
}
```

---

### GET /api/v1/admin/users/metrics

Aggregate user-level activity metrics.

**Authentication:** Required (admin email allowlist)

**Response:** `200 OK`
```json
{
  "totalUsers": 245,
  "activeUsers7d": 87,
  "activeUsers30d": 156,
  "users": [
    {
      "userId": "550e8400-e29b-41d4-a716-446655440000",
      "userName": "Jane Rep",
      "userEmail": "rep@example.com",
      "totalSessions": 14,
      "totalTranscripts": 13,
      "totalMessages": 210,
      "avgMessagesPerSession": 15.0,
      "avgSessionDurationMinutes": 7.5,
      "sessionBreakdown": {"training": 10, "evaluation": 4},
      "personaUsage": {"executive": 6, "skeptic": 8},
      "lastActive": "2026-06-30T18:12:00Z"
    }
  ]
}
```

---

### GET /api/v1/admin/users/{user_id}/sessions

Paginated session history for a specific user (admin view, no ownership check).

**Authentication:** Required (admin email allowlist)

**Path Parameters:**
- `user_id` (string, UUID): Target user ID

**Query Parameters:**
- `limit` (integer, optional, default 20)
- `offset` (integer, optional, default 0)
- `session_type` (string, optional): `training` or `evaluation`

**Response:** `200 OK` — same `SessionListResponse` shape as [Sessions Endpoint](#8-sessions-endpoint)

---

### GET /api/v1/admin/sessions/{session_id}

Full detail for any session, regardless of owner.

**Authentication:** Required (admin email allowlist)

**Path Parameters:**
- `session_id` (string): Session identifier

**Response:** `200 OK` — same `SessionDetailResponse` shape as [Sessions Endpoint](#8-sessions-endpoint)

---

## 7. Products Endpoint

Product catalog used to drive RAG filtering context during a session. **Note:** the catalog (`backend/app/api/products.py`) is currently hardcoded to a furniture-collection taxonomy (Bracken, Calden, Modero, Neo, Whitehaven) and has not yet been generalized to the platform's other industries — update this section when the catalog is made industry-configurable.

### GET /api/v1/products

Retrieve the complete product catalog (categories and their types).

**Authentication:** Not required

**Response:** `200 OK`
```json
{
  "categories": [
    {
      "id": "bracken",
      "name": "Bracken",
      "description": "Bracken furniture collection",
      "types": []
    }
  ]
}
```

---

### GET /api/v1/products/categories

List all product category IDs.

**Authentication:** Not required

**Response:** `200 OK`
```json
["bracken", "calden", "modero", "neo", "whitehaven"]
```

---

## 8. Sessions Endpoint

Authenticated user's own session history and detail (`backend/app/api/sessions.py`).

### GET /api/v1/sessions

Paginated list of the current user's sessions, with grade/score backfilled from the evaluation when one exists.

**Authentication:** Required

**Query Parameters:**
- `limit` (integer, optional, default 20)
- `offset` (integer, optional, default 0)
- `session_type` (string, optional): `training` or `evaluation`

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "session_id": "sess-456",
      "session_type": "training",
      "status": "completed",
      "started_at": "2026-06-19T12:00:00Z",
      "ended_at": "2026-06-19T12:08:15Z",
      "duration": 495,
      "selected_persona": "executive",
      "difficulty": "intermediate",
      "product_category": "bracken",
      "product_type": null,
      "message_count": 18,
      "grade": "B+",
      "score": 82,
      "has_evaluation": true
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

---

### GET /api/v1/sessions/{session_id}

Full session detail: session summary, transcript, and evaluation (if present). Returns `403` if the session belongs to another user, `404` if it doesn't exist.

**Authentication:** Required

**Path Parameters:**
- `session_id` (string): Session identifier

**Response:** `200 OK`
```json
{
  "session": {
    "session_id": "sess-456",
    "session_type": "training",
    "status": "completed",
    "started_at": "2026-06-19T12:00:00Z",
    "ended_at": "2026-06-19T12:08:15Z",
    "duration": 495,
    "selected_persona": "executive",
    "difficulty": "intermediate",
    "message_count": 18,
    "grade": "B+",
    "score": 82,
    "has_evaluation": true
  },
  "transcript": {},
  "evaluation": {}
}
```

**Errors:**
- `403` - Session belongs to another user
- `404` - Session not found

---

## 9. Error Handling

All errors return a standardized error response format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": [],
    "requestId": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | OAuth callback, API response |
| 307 | Temporary Redirect | Browser OAuth flow |
| 400 | Bad Request | Invalid parameters, validation error |
| 401 | Unauthorized | Missing/invalid token |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Gemini API failure |
| 503 | Service Unavailable | Dependency down |

### Common Error Codes

- `VALIDATION_ERROR` - Request validation failed
- `AUTH_ERROR` - Authentication failed
- `TOKEN_EXPIRED` - JWT token expired
- `INVALID_PARAMETERS` - Invalid request parameters
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `GEMINI_API_ERROR` - Gemini API error
- `INTERNAL_ERROR` - Unexpected server error

---

## 10. WebSocket Protocol

### Message Types

The WebSocket endpoint `/ws/gemini/live` handles bidirectional streaming of audio and control messages.

#### Audio Messages (Binary)

PCM audio data in binary format.

**Input:** Client → Server
- Format: PCM 16-bit, 16kHz sample rate
- Frame size: variable (typically 320-640 bytes)
- Encoding: Raw bytes

**Output:** Server → Client
- Format: PCM 16-bit, 24kHz sample rate
- Frame size: variable
- Encoding: Raw bytes

#### Control Messages (JSON Text)

Text messages for session control and metadata.

**Client → Server Example:**
```json
{
  "type": "control",
  "action": "end_session"
}
```

**Server → Client Example:**

A coaching hint (Training mode only; throttled to one per 10s, and only when
the coach's intervention level is non-`none`):
```json
{
  "type": "coach_hint",
  "level": "warning",
  "hint": "The customer just raised a price concern — acknowledge it before moving on.",
  "stage": "CONNECT",
  "example_phrase": "That's a common concern. What's driving it for you?",
  "ready_for_next_stage": false
}
```

The customer's current mood, emitted after every analyzed turn (both modes,
unthrottled) so the mood HUD tracks the same state the persona prompt is
rebuilt from:
```json
{
  "type": "mood_update",
  "mood": "skeptical",
  "regard_level": "low"
}
```

`mood` is one of `frustrated`, `skeptical`, `neutral`, `interested`,
`ready_to_buy`; `regard_level` is one of `high`, `medium`, `low`, `no`.

### Connection Lifecycle

1. **Client initiates WebSocket connection** with JWT token and session parameters
2. **Server validates token and establishes session**
3. **Bidirectional streaming begins:**
   - Client sends audio (16kHz PCM)
   - Server relays to Gemini Live API
   - Gemini responds with audio (24kHz PCM)
   - Server sends back to client
   - Coach agent generates real-time hints (if enabled)
4. **Client receives coaching hints** (async, non-blocking)
5. **Connection closes** when client disconnects or 30-minute timeout occurs

### Error Handling

WebSocket errors are sent as JSON text messages:

```json
{
  "type": "error",
  "code": 4001,
  "message": "Invalid or expired token"
}
```

#### WebSocket Close Codes

| Code | Meaning | Recovery |
|------|---------|----------|
| 1000 | Normal closure | Reconnect if needed |
| 4001 | Invalid/expired token | Re-authenticate and reconnect |
| 4003 | Rate limit exceeded | Wait before reconnecting |
| 4004 | Invalid request | Check connection parameters |
| 4005 | Service unavailable | Retry after delay |

### Reconnection

Clients should implement exponential backoff for reconnection:

1. Detect disconnect (WebSocket onclose event)
2. Wait 1s, then attempt reconnect
3. On failure, wait 2s, then reconnect
4. On failure, wait 4s, then reconnect
5. Max wait: 30s

The backend maintains session state for 5 minutes after disconnect, allowing seamless reconnection.

---

## Rate Limiting

- **Gemini API calls:** 100 req/min per user
- **WebSocket connections:** 5 concurrent per user
- **Auth endpoints:** 10 req/min per IP

Rate limit headers returned on each response:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1707144000
```

---

## Summary of Implemented Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check |
| GET | `/ready` | No | Readiness check |
| GET | `/auth/login` | No | Browser OAuth redirect |
| POST | `/auth/login` | No | SPA OAuth URL |
| GET | `/auth/callback` | No | Browser OAuth callback |
| POST | `/auth/callback` | No | SPA OAuth callback |
| POST | `/auth/refresh` | No | Token refresh |
| GET | `/auth/me` | Yes | Current user profile |
| POST | `/auth/logout` | Yes | Logout |
| POST | `/api/v1/gemini/generate` | Yes | Text generation |
| WebSocket | `/ws/gemini/live` | Yes | Voice session |
| GET | `/personas` | No | List personas |
| GET | `/personas/evaluation` | No | List evaluation personas |
| GET | `/api/v1/admin/personas/metrics` | Yes (admin) | Persona performance metrics |
| GET | `/api/v1/admin/users/metrics` | Yes (admin) | User analytics |
| GET | `/api/v1/admin/users/{user_id}/sessions` | Yes (admin) | User session history |
| GET | `/api/v1/admin/sessions/{session_id}` | Yes (admin) | Session details |
| GET | `/api/v1/products` | No | Product catalog |
| GET | `/api/v1/products/categories` | No | Product category IDs |
| GET | `/api/v1/sessions` | Yes | Current user's session list |
| GET | `/api/v1/sessions/{session_id}` | Yes | Session details with transcript + evaluation |

---

**Last Updated:** July 2, 2026
**Maintainer:** Development Team
