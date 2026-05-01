"""Health check endpoints."""

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status

from app.config import get_settings
from app.core.logging import get_logger
from app.repositories.base import get_firestore_client

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint.

    Returns service status without checking dependencies.
    Used for Kubernetes/Cloud Run liveness probes.

    Returns:
        Dictionary with health status
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready")
async def readiness_check(response: Response) -> dict[str, Any]:
    """Readiness check with dependency status.

    Checks all critical dependencies and returns detailed status.
    Used for Kubernetes/Cloud Run readiness probes before accepting traffic.

    Returns:
        Dictionary with readiness status and dependency checks

    Response Codes:
        200: All dependencies healthy (ready)
        503: One or more dependencies unhealthy (degraded)
    """
    # Run all health checks concurrently for faster response
    check_results = await asyncio.gather(
        _check_database(),
        _check_gemini_api(),
        _check_secret_manager(),
        return_exceptions=True,
    )

    checks = {
        "database": _process_check_result(check_results[0]),
        "geminiApi": _process_check_result(check_results[1]),
        "secretManager": _process_check_result(check_results[2]),
    }

    all_healthy = all(checks.values())

    # Set appropriate status code
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning("Readiness check failed", extra={"checks": checks})

    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _process_check_result(result: bool | BaseException) -> bool:
    """Process health check result, handling exceptions.

    Args:
        result: Check result or exception

    Returns:
        Boolean health status
    """
    if isinstance(result, BaseException):
        logger.error("Health check failed", exc_info=result)
        return False
    return result


async def _check_database() -> bool:
    """Check Firestore connectivity.

    Attempts to read from Firestore to verify connectivity.
    Uses a timeout to prevent hanging.

    Returns:
        True if database is accessible, False otherwise
    """
    try:
        if not settings.gcp_project_id:
            logger.warning("GCP project ID not configured")
            return False

        async with asyncio.timeout(2.0):
            db = get_firestore_client()
            # Lightweight read to verify connectivity (document doesn't need to exist)
            await db.collection("_health").document("ping").get()
            return True
    except TimeoutError:
        logger.error("Database health check timed out")
        return False
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def _check_gemini_api() -> bool:
    """Check Gemini API availability.

    Verifies that Gemini API credentials are configured.
    In production, could make a lightweight API call.

    Returns:
        True if API is available, False otherwise
    """
    try:
        # TODO: Implement actual Gemini API health check when integration is complete
        # Example:
        # async with asyncio.timeout(2.0):
        #     # Make lightweight API call (e.g., list models)
        #     client = get_gemini_client()
        #     await client.list_models()
        #     return True

        # For now, check if API key is configured
        if not settings.gemini_api_key:
            logger.warning("Gemini API key not configured")
            return False

        return True
    except TimeoutError:
        logger.error("Gemini API health check timed out")
        return False
    except Exception as e:
        logger.error(f"Gemini API health check failed: {e}")
        return False


async def _check_secret_manager() -> bool:
    """Check GCP Secret Manager availability.

    Verifies Secret Manager access for production deployments.

    Returns:
        True if accessible, False otherwise
    """
    try:
        # In development, Secret Manager is not required
        if settings.is_development:
            return True

        # TODO: Implement actual Secret Manager health check when needed
        # Example:
        # async with asyncio.timeout(2.0):
        #     client = get_secret_manager_client()
        #     await client.access_secret_version(...)
        #     return True

        # For now, assume it's available in production if GCP project is set
        return bool(settings.gcp_project_id)
    except TimeoutError:
        logger.error("Secret Manager health check timed out")
        return False
    except Exception as e:
        logger.error(f"Secret Manager health check failed: {e}")
        return False
