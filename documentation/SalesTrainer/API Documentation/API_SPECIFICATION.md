---
tags: [#api, #endpoints, #reference]
---

# API Specification: Luxe Sales Coach v2 Backend

> **Version:** 2.0.0
> **Last Updated: 2026-04-30
> **Status:** Current
> **Base URL:** `https://api.luxe-sales-coach.run.app` (production) / `http://localhost:8000` (development)

---

## Overview

This document defines the REST and WebSocket API for the Luxe Sales Coach v2 backend. All endpoints follow REST conventions and return JSON responses.

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
6. [Error Handling](#6-error-handling)
7. [WebSocket Protocol](#7-websocket-protocol)

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

Establish real-time voice session with Gemini Live API.

**Connection Query Parameters:**
- `token` (required) - JWT authentication token
- `mode` (required) - `training` or `evaluation`
- `persona` (optional) - Customer persona ID (Assistant, Executive, Skeptic)
- `difficulty` (optional) - Difficulty level (Basic, Intermediate, Advanced)

**Example URL:**
```
ws://localhost:8000/ws/gemini/live?token={accessToken}&mode=training&persona=executive&difficulty=intermediate
```

**Features:**
- JWT authentication via query parameter
- Bidirectional audio streaming (PCM 16kHz input, 24kHz output)
- Text message support for control commands
- Real-time coaching hints (coach mode)
- 30-minute idle timeout
- Automatic reconnection support
- Full conversation transcription

See [WebSocket Protocol](#7-websocket-protocol) for message formats and error handling.

---

## 5. Personas

### GET /personas

List available customer personas for roleplay. No authentication required.

**Response:** `200 OK`
```json
{
  "personas": [
    {
      "id": "assistant",
      "name": "Assistant",
      "description": "Cooperative and helpful customer",
      "traits": ["eager to buy", "asks clarifying questions"],
      "difficultyLevels": ["Basic", "Intermediate", "Advanced"]
    },
    {
      "id": "executive",
      "name": "Executive",
      "description": "Time-conscious decision maker",
      "traits": ["results-focused", "demands ROI proof"],
      "difficultyLevels": ["Basic", "Intermediate", "Advanced"]
    },
    {
      "id": "skeptic",
      "name": "Skeptic",
      "description": "Skeptical and objection-prone customer",
      "traits": ["raises objections", "questions value"],
      "difficultyLevels": ["Basic", "Intermediate", "Advanced"]
    }
  ]
}
```

---

### GET /personas/evaluation

List personas available for evaluation mode. No authentication required.

**Response:** `200 OK` (same format as `/personas`)

---

## 6. Error Handling

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

## 7. WebSocket Protocol

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
```json
{
  "type": "hint",
  "hint": "Try asking about their budget to move the conversation forward",
  "context": "Customer is still in exploration phase"
}
```

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


---

## 6. Admin Endpoints

Admin-only endpoints for metrics, analytics, and session management. Requires admin user role.

### GET /admin/personas/metrics

Retrieve performance metrics for all customer personas.

**Authentication:** Required (admin role)

**Response:** `200 OK`
```json
{
  "personas": [
    {
      "persona_id": "eager_newlywed",
      "name": "Eager Newlywed",
      "total_sessions": 156,
      "avg_user_score": 78.5,
      "avg_coach_rating": 4.2,
      "difficulty_level": "easy",
      "abandonment_rate": 0.05
    }
  ],
  "generated_at": "2026-02-19T14:30:00Z"
}
```

---

### GET /admin/users/metrics

Retrieve aggregated user-level metrics and analytics.

**Authentication:** Required (admin role)

**Response:** `200 OK`
```json
{
  "total_users": 245,
  "active_users_7d": 87,
  "total_sessions": 3421,
  "avg_sessions_per_user": 14.0,
  "avg_user_score": 76.3,
  "avg_session_duration_seconds": 420,
  "completion_rate": 0.92,
  "most_used_personas": [
    "eager_newlywed",
    "luxury_renovator",
    "budget_conscious"
  ],
  "generated_at": "2026-02-19T14:30:00Z"
}
```

---

### GET /admin/users/{user_id}/sessions

Retrieve session history for a specific user. Admin view with full details.

**Authentication:** Required (admin role)

**Path Parameters:**
- user_id (string, UUID): Target user ID

**Response:** `200 OK`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_email": "rep@example.com",
  "sessions": [
    {
      "session_id": "sess-123",
      "mode": "training",
      "persona": "eager_newlywed",
      "difficulty": "easy",
      "started_at": "2026-02-19T13:00:00Z",
      "ended_at": "2026-02-19T13:07:30Z",
      "duration_seconds": 450,
      "grade": "A-",
      "score": 87,
      "status": "completed",
      "message_count": 12,
      "has_evaluation": true,
      "has_transcript": true
    }
  ]
}
```

---

### GET /admin/sessions/{session_id}

Retrieve detailed information about a specific session with full context.

**Authentication:** Required (admin role)

**Path Parameters:**
- session_id (string): Session identifier

**Response:** `200 OK`
```json
{
  "session": {
    "session_id": "sess-123",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_email": "rep@example.com",
    "mode": "training",
    "persona": "eager_newlywed",
    "difficulty": "easy",
    "started_at": "2026-02-19T13:00:00Z",
    "ended_at": "2026-02-19T13:07:30Z",
    "duration_seconds": 450,
    "status": "completed",
    "grade": "A-",
    "score": 87,
    "message_count": 12
  }
}
```

---

## 7. Products Endpoint

Product catalog and filtering for RAG-based coaching context.

### GET /products

Retrieve the complete product catalog.

**Authentication:** Not required

**Query Parameters:**
- category (string, optional): Filter by product category

**Response:** `200 OK`
```json
{
  "products": [
    {
      "id": "prod-bedroom-001",
      "name": "Bedroom Set - Cherry",
      "category": "furniture",
      "product_type": "bedroom_set",
      "features": ["Solid wood", "Queen size", "5-piece set"],
      "price_range": "$1,200-1,800"
    }
  ],
  "total_count": 247
}
```

---

### GET /products/categories

List all product categories.

**Authentication:** Not required

**Response:** `200 OK`
```json
{
  "categories": [
    "furniture",
    "mattresses",
    "financing",
    "protection_plans"
  ]
}
```

---

## 8. Sessions Endpoint

Session management and evaluation retrieval.

### GET /api/v1/sessions

Retrieve current user's session history.

**Authentication:** Required

**Query Parameters:**
- limit (integer, optional): Results per page (default: 20)
- offset (integer, optional): Pagination offset (default: 0)

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "session_id": "sess-456",
      "mode": "training",
      "persona": "luxury_renovator",
      "difficulty": "medium",
      "started_at": "2026-02-19T12:00:00Z",
      "grade": "B+",
      "score": 82
    }
  ],
  "pagination": {"total": 42, "limit": 20, "offset": 0}
}
```

---

### GET /api/v1/sessions/{session_id}

Retrieve a specific session's details.

**Authentication:** Required

**Path Parameters:**
- session_id (string): Session identifier

**Response:** `200 OK`
```json
{
  "session_id": "sess-456",
  "mode": "training",
  "persona": "luxury_renovator",
  "difficulty": "medium",
  "duration_seconds": 495,
  "status": "completed",
  "evaluation": {
    "score": 82,
    "grade": "B+",
    "strengths": ["Good listen skills"],
    "improvements": ["Strengthen closing technique"]
  }
}
```

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
| GET | `/admin/personas/metrics` | Yes (admin) | Persona performance metrics |
| GET | `/admin/users/metrics` | Yes (admin) | User analytics |
| GET | `/admin/users/{user_id}/sessions` | Yes (admin) | User session history |
| GET | `/admin/sessions/{session_id}` | Yes (admin) | Session details |
| GET | `/products` | No | Product catalog |
| GET | `/products/categories` | No | Product categories |
| GET | `/api/v1/sessions` | Yes | User session list |
| GET | `/api/v1/sessions/{session_id}` | Yes | Session details with evaluation |

---

**Last Updated:** 2026-04-30
**Maintainer:** Development Team
