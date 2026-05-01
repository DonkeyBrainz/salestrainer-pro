# Core Module

This module contains core infrastructure components used throughout the application.

## Components

### `exceptions.py`

Custom exception classes that map to the error codes defined in the API specification.

**Exception Hierarchy:**
```
AppException (base)
├── ValidationError (400)
├── InvalidRequestError (400)
├── UnauthorizedError (401)
├── TokenExpiredError (401)
├── ForbiddenError (403)
├── NotFoundError (404)
├── ConflictError (409)
├── RateLimitError (429)
├── InternalError (500)
└── ServiceUnavailableError (503)
```

**Usage:**
```python
from app.core.exceptions import NotFoundError, ValidationError

# Simple usage
raise NotFoundError("User not found")

# With validation details
raise ValidationError(
    "Invalid input",
    details=[
        {"field": "email", "message": "Invalid email format"},
        {"field": "age", "message": "Must be >= 18"}
    ]
)
```

### `logging.py`

Structured JSON logging compatible with Google Cloud Logging.

**Features:**
- JSON-formatted logs in production
- Human-readable logs in development
- Automatic service context (name, version, environment)
- Source location tracking (file, line, function)
- GCP-compatible severity levels

**Usage:**
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

logger.info("User logged in", extra={"userId": user_id})
logger.warning("Rate limit approaching", extra={"remaining": 10})
logger.error("Database connection failed", exc_info=True)
```

**Log Format (Production):**
```json
{
  "timestamp": "2026-01-27T12:00:00Z",
  "severity": "INFO",
  "message": "User logged in",
  "service": {
    "name": "Luxe Sales Coach API",
    "version": "0.1.0",
    "environment": "production"
  },
  "sourceLocation": {
    "file": "/app/services/auth.py",
    "line": 42,
    "function": "login"
  },
  "userId": "550e8400-e29b-41d4-a716-446655440000"
}
```

### `middleware.py`

Custom middleware for request processing.

**Middleware Stack:**
1. `RequestIDMiddleware` - Adds unique ID to each request
2. `TimingMiddleware` - Measures request processing time
3. `ErrorLoggingMiddleware` - Logs unhandled exceptions

**Request ID:**
- Generated for each request (UUID v4)
- Can be provided by client via `X-Request-ID` header
- Added to response headers for tracing
- Available in request state: `request.state.request_id`

**Timing:**
- Adds `X-Process-Time` header to responses (e.g., "42.50ms")
- Logs request duration with method, path, and status code

**Error Logging:**
- Catches and logs unhandled exceptions with full context
- Re-raises exception for exception handlers to process

### `dependencies.py`

Shared FastAPI dependencies for dependency injection.

**Available Dependencies:**

**`get_settings() -> Settings`**
```python
from app.core.dependencies import SettingsDep

@router.get("/config")
async def get_config(settings: SettingsDep):
    return {"environment": settings.environment}
```

**`get_request_id(request: Request) -> str`**
```python
from app.core.dependencies import RequestIDDep

@router.post("/items")
async def create_item(item: Item, request_id: RequestIDDep):
    logger.info("Creating item", extra={"requestId": request_id})
    ...
```

**`get_auth_token(authorization: str | None) -> str`**
```python
from app.core.dependencies import AuthTokenDep

@router.get("/protected")
async def protected_endpoint(token: AuthTokenDep):
    # Token is extracted from "Bearer <token>" header
    user = decode_jwt(token)
    ...
```

## Exception Handling

All exceptions are handled by global exception handlers in `app/main.py`:

1. **AppException Handler** - Converts custom exceptions to standard error format
2. **ValidationError Handler** - Converts FastAPI/Pydantic validation errors
3. **Generic Handler** - Catches all unhandled exceptions

**Standard Error Response:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "details": [],
    "requestId": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## Adding New Exceptions

To add a new exception type:

1. Create a new class in `exceptions.py` that inherits from `AppException`
2. Set the appropriate error code and HTTP status
3. Document it in the API specification

```python
class CustomError(AppException):
    """Description of when this error occurs."""

    def __init__(self, message: str = "Default message") -> None:
        super().__init__(
            message=message,
            code="CUSTOM_ERROR",
            status_code=400,
        )
```

## Testing

All core components have comprehensive unit tests in `tests/unit/`:

- `test_exceptions.py` - Exception class tests
- `test_middleware.py` - Middleware behavior tests
- `test_exception_handlers.py` - Exception handler integration tests
- `test_dependencies.py` - Dependency injection tests

Run tests with:
```bash
pytest tests/unit/test_*.py
```
