"""Custom middleware for request processing."""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID to each request.

    The request ID is:
    - Generated for each request (UUID v4)
    - Added to request state for use in handlers
    - Included in response headers for client-side tracing
    - Added to all log messages via contextvars
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and add request ID."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Add to request state for access in route handlers
        request.state.request_id = request_id

        # Process request
        response: Response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to measure and log request processing time.

    Logs request duration and adds timing information to response headers
    for performance monitoring.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and measure timing."""
        start_time = time.time()

        # Process request
        response: Response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add timing header
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        # Log request details
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "Request completed",
            extra={
                "requestId": request_id,
                "method": request.method,
                "path": request.url.path,
                "statusCode": response.status_code,
                "durationMs": round(duration_ms, 2),
                "userAgent": request.headers.get("user-agent", ""),
            },
        )

        return response


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log unhandled exceptions.

    Catches exceptions that escape route handlers and logs them
    with full context before re-raising.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and log any errors."""
        try:
            response: Response = await call_next(request)
            return response
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")

            logger.error(
                "Unhandled exception in request",
                extra={
                    "requestId": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(exc),
                    "errorType": type(exc).__name__,
                },
                exc_info=True,
            )

            # Re-raise to be handled by exception handlers
            raise
