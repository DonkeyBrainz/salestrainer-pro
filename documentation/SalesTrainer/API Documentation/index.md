# API Documentation

Complete REST and WebSocket API reference for SalesTrainer Pro.

**Tags:** #api #endpoints #reference

## Main Reference

- **[[API_SPECIFICATION]]** - Full endpoint documentation, request/response examples, authentication

## Quick Access by Category

### Authentication
- `POST /auth/login` - Google OAuth login (SPA)
- `GET /auth/callback` - OAuth callback handler
- `POST /auth/refresh` - Refresh JWT token
- `GET /auth/me` - Get current user
- `POST /auth/logout` - Logout

See [[API_SPECIFICATION]] for details.

### Sessions & Conversations
- `GET /api/v1/sessions` - List current user's session history
- `GET /api/v1/sessions/:id` - Retrieve session detail (transcript + evaluation)
- `WebSocket /ws/gemini/live` - Real-time voice conversation with provider support
  - Query params: `token`, `mode` (training/evaluation), `voice_provider` (gemini/vertex)
  - Sessions are created implicitly here, not via REST

### Data & Evaluation
- `GET /personas` - List available customer personas
- `GET /personas/evaluation` - List evaluation-mode personas
- `GET /api/v1/products` - Product catalog for RAG context
- `GET /health` - Health check endpoint

### Admin (requires admin email allowlist)
- `GET /api/v1/admin/personas/metrics` - Persona performance metrics
- `GET /api/v1/admin/users/metrics` - User analytics
- `GET /api/v1/admin/sessions/:id` - Any session's detail (admin view)

## Integration Guide

### For Frontend Developers
1. Review [[API_SPECIFICATION#Authentication|API_SPECIFICATION.md]] for login flow
2. WebSocket connection: `ws://localhost:8000/ws/gemini/live?token=<jwt>&mode=training`
3. See [[AGENT_FLOW|../Architecture%20&%20Design/AGENT_FLOW.md]] for conversation patterns

### For Backend Developers
1. Endpoints defined in `backend/app/api/`
2. Data models in `backend/app/models/`
3. Business logic in `backend/app/services/`

See [[DATABASE_SCHEMA|../Architecture%20&%20Design/DATABASE_SCHEMA.md]] for data contracts.

## Error Handling

API returns standard HTTP status codes:
- `200` - Success
- `400` - Bad request
- `401` - Unauthorized (missing/invalid token)
- `404` - Not found
- `500` - Server error

WebSocket close codes:
- `1000` - Normal closure
- `4001` - Invalid/expired token
- `4003` - Rate limit exceeded
- `4004` - Invalid request
- `4005` - Service unavailable

See [[API_SPECIFICATION]] for full error details.

## Rate Limiting & Quotas

Check [[ADMIN_TROUBLESHOOTING|../Features/ADMIN_TROUBLESHOOTING.md]] for quota information and limits.

## Environment Variables

Required for API:
```
GEMINI_API_KEY             # Google AI API key
GOOGLE_CLIENT_ID           # OAuth client ID
GOOGLE_CLIENT_SECRET       # OAuth client secret
FIREBASE_PROJECT_ID        # Firestore project ID
```

See [[BACKEND_SETUP|../Getting%20Started/BACKEND_SETUP.md]] for full list.

---

**Need help?** Check [[ADMIN_TROUBLESHOOTING|../Features/ADMIN_TROUBLESHOOTING.md]] for common issues.

---

**Last updated:** 2026-07-13
