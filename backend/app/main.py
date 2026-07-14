"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.gemini import router as gemini_router
from app.api.health import router as health_router
from app.api.organizations import router as organizations_router
from app.api.personas import router as personas_router
from app.api.products import router as products_router
from app.api.sessions import router as sessions_router
from app.api.users import router as users_router
from app.api.websocket import router as websocket_router
from app.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    ErrorLoggingMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)
from app.repositories.base import get_firestore_client
from app.services.objection_service import init_objection_service
from app.services.rag_service import init_rag_service

# Initialize logging
setup_logging()
logger = get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info(
        "Application starting",
        extra={
            "appName": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
    )

    # Initialize objection service (always, no external deps)
    init_objection_service()
    logger.info("Objection service initialized")

    # Initialize RAG service if enabled (skipped when GCP credentials are unavailable)
    if settings.rag_enabled:
        try:
            db = get_firestore_client()
            init_rag_service(db, settings)
            logger.info("RAG service initialized")
        except Exception as e:
            logger.warning(
                "RAG service initialization failed — running without RAG",
                extra={"error": str(e)},
            )

    yield
    # Shutdown
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for Luxe Sales Coach v2 - Voice-enabled AI sales training",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    swagger_ui_parameters={
        "persistAuthorization": True,  # Remember auth token in browser
    },
)


# Exception Handlers
@app.exception_handler(AppError)
async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle custom application exceptions.

    Returns standardized error response matching API specification.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        "Application exception",
        extra={
            "requestId": request_id,
            "errorCode": exc.code,
            "errorMessage": exc.message,
            "statusCode": exc.status_code,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "requestId": request_id,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI request validation errors.

    Converts Pydantic validation errors to our standard error format.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Convert Pydantic errors to our format
    details = [
        {
            "field": ".".join(str(loc) for loc in error["loc"][1:]),  # Skip 'body'
            "message": error["msg"],
        }
        for error in exc.errors()
    ]

    logger.warning(
        "Request validation failed",
        extra={
            "requestId": request_id,
            "errors": details,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": details,
                "requestId": request_id,
            }
        },
    )


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors from response models."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "Response validation failed",
        extra={
            "requestId": request_id,
            "error": str(exc),
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": [],
                "requestId": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions.

    Logs the full exception and returns a generic error response.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "Unhandled exception",
        extra={
            "requestId": request_id,
            "error": str(exc),
            "errorType": type(exc).__name__,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": [],
                "requestId": request_id,
            }
        },
    )


# Middleware (order matters - applied in reverse order)
# 1. CORS (applied first, so it runs last)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Error logging
app.add_middleware(ErrorLoggingMiddleware)

# 3. Timing
app.add_middleware(TimingMiddleware)

# 4. Request ID (applied last, so it runs first)
app.add_middleware(RequestIDMiddleware)


# Routers
app.include_router(health_router, tags=["Health"])
app.include_router(auth_router, tags=["Authentication"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(gemini_router, prefix="/api/v1", tags=["Gemini"])
app.include_router(personas_router, tags=["Personas"])
app.include_router(products_router, tags=["Products"])
app.include_router(sessions_router, tags=["Sessions"])
app.include_router(users_router, tags=["Users"])
app.include_router(organizations_router, tags=["Organizations"])
app.include_router(websocket_router, tags=["WebSocket"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
