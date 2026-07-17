# `app/core` — infrastructure

Cross-cutting components: exceptions, logging, middleware, DI, RBAC, session state.

## `exceptions.py`

`AppError` base (message, `code`, `status_code`, `details: list[dict]`) with subclasses mapped to HTTP status:

```
AppError (500 default)
├── ValidationError / InvalidRequestError  400
├── UnauthorizedError / TokenExpiredError  401
├── ForbiddenError                         403
├── NotFoundError                          404
├── ConflictError                          409
├── RateLimitError                         429
├── InternalError                          500
└── ServiceUnavailableError                503
```

```python
raise NotFoundError("User not found")
raise ValidationError("Invalid input", details=[{"field": "email", "message": "..."}])
```

New type: subclass `AppError`, set `code`/`status_code`, document in the API spec.

Handlers live in `app/main.py` (AppError, RequestValidationError, generic). Response shape:

```json
{ "error": { "code": "NOT_FOUND", "message": "...", "details": [], "requestId": "..." } }
```

## `logging.py`

`get_logger(__name__)` → structured JSON in prod (GCP Cloud Logging severities, service context, source location), human-readable in dev. Pass structured fields via `extra=`.

## `middleware.py`

Stack: `RequestIDMiddleware` (UUID v4, honors inbound `X-Request-ID`, exposes `request.state.request_id`) → `TimingMiddleware` (`X-Process-Time` header) → `ErrorLoggingMiddleware` (logs unhandled exceptions with context, re-raises for handlers).

## `dependencies.py`

DI providers and `Annotated` aliases. Auth/context: `get_settings` (`SettingsDep`), `get_request_id` (`RequestIDDep`), `get_auth_token` (`AuthTokenDep`, extracts Bearer). Wiring: repository getters (user/token/session/transcript/evaluation/store), service getters (auth/gemini/session/customer-agent/coach-agent/rag/objection), `get_live_provider` (resolves the live speech-to-speech provider via the registry), `get_state_manager_dep`.

## `rbac.py`

Role gates. `require_manager_or_above` (`CurrentUserDep` → `User`, raises `ForbiddenError`) and `get_visible_store_ids` / `VisibleStoreIdsDep` for store-scoped visibility. Used by `/organizations` and `/admin`.

## `session.py`

Server-side session/CSRF state used in the OAuth flow.

## Tests

`tests/unit/test_exceptions.py`, `test_middleware.py`, `test_exception_handlers.py`, `test_dependencies.py`.
