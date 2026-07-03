"""Shared FastAPI dependencies for dependency injection.

These dependencies can be used across route handlers for common functionality
like authentication, database access, and request validation.
"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.core.session import StateManager, get_state_manager
from app.models.user import User
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.store_repository import StoreRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.coach_agent_service import CoachAgentService
from app.services.customer_agent_service import CustomerAgentService
from app.services.gemini_service import GeminiService
from app.services.objection_service import ObjectionLookupService
from app.services.objection_service import get_objection_service as _get_objection_service
from app.services.rag_service import FirestoreRAGService
from app.services.rag_service import get_rag_service as _get_rag_service
from app.services.session_service import SessionService


async def get_request_id(request: Request) -> str:
    """Get the request ID from request state.

    The request ID is added by RequestIDMiddleware.

    Args:
        request: FastAPI request object

    Returns:
        Request ID string
    """
    return getattr(request.state, "request_id", "unknown")


# Security scheme for OpenAPI docs
security = HTTPBearer()


async def get_auth_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """Extract and validate Bearer token from Authorization header.

    Args:
        credentials: HTTP Bearer credentials from Authorization header

    Returns:
        JWT token string

    Raises:
        UnauthorizedError: If token is missing or malformed
    """
    return credentials.credentials


# State management dependency
def get_state_manager_dep(
    settings: Annotated[Settings, Depends(get_settings)],
) -> StateManager:
    """Get state manager instance for OAuth CSRF protection."""
    return get_state_manager(settings)


# Repository dependencies
def get_user_repository() -> UserRepository:
    """Get user repository instance."""
    return UserRepository()


def get_token_repository() -> TokenRepository:
    """Get token repository instance."""
    return TokenRepository()


def get_session_repository() -> SessionRepository:
    """Get session repository instance."""
    return SessionRepository()


def get_transcript_repository() -> TranscriptRepository:
    """Get transcript repository instance."""
    return TranscriptRepository()


def get_evaluation_repository() -> EvaluationRepository:
    """Get evaluation repository instance."""
    return EvaluationRepository()


def get_store_repository() -> StoreRepository:
    """Get store repository instance."""
    return StoreRepository()


# Service dependencies
def get_auth_service(
    settings: Annotated[Settings, Depends(get_settings)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    token_repo: Annotated[TokenRepository, Depends(get_token_repository)],
) -> AuthService:
    """Get auth service instance with injected dependencies."""
    return AuthService(
        settings=settings,
        user_repository=user_repo,
        token_repository=token_repo,
    )


def get_gemini_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GeminiService:
    """Get Gemini service instance with injected dependencies."""
    return GeminiService(settings=settings)


def get_session_service(
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    transcript_repository: Annotated[TranscriptRepository, Depends(get_transcript_repository)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> SessionService:
    """Get session service instance with injected dependencies."""
    return SessionService(
        session_repository=session_repository,
        transcript_repository=transcript_repository,
        user_repository=user_repository,
    )


def get_customer_agent_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CustomerAgentService:
    """Get customer agent service instance with injected dependencies."""
    return CustomerAgentService(settings=settings)


def get_coach_agent_service(
    settings: Annotated[Settings, Depends(get_settings)],
    evaluation_repo: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
) -> CoachAgentService:
    """Get coach agent service instance with injected dependencies."""
    return CoachAgentService(settings=settings, evaluation_repository=evaluation_repo)


def get_rag_service_dep() -> FirestoreRAGService:
    """Get RAG service instance (initialized at startup)."""
    return _get_rag_service()


def get_objection_service_dep() -> ObjectionLookupService:
    """Get objection service instance (initialized at startup)."""
    return _get_objection_service()


# Current user dependency (the key authentication dependency)
async def get_current_user(
    token: Annotated[str, Depends(get_auth_token)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Get current authenticated user from token.

    This dependency:
    1. Extracts Bearer token (via get_auth_token)
    2. Decodes and validates the JWT
    3. Fetches user from database
    4. Raises UnauthorizedError or TokenExpiredError if invalid
    """
    return await auth_service.get_current_user(token)


# Type aliases for common dependencies
SettingsDep = Annotated[Settings, Depends(get_settings)]
RequestIDDep = Annotated[str, Depends(get_request_id)]
AuthTokenDep = Annotated[str, Depends(get_auth_token)]
StateManagerDep = Annotated[StateManager, Depends(get_state_manager_dep)]
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
TokenRepositoryDep = Annotated[TokenRepository, Depends(get_token_repository)]
SessionRepositoryDep = Annotated[SessionRepository, Depends(get_session_repository)]
TranscriptRepositoryDep = Annotated[TranscriptRepository, Depends(get_transcript_repository)]
EvaluationRepositoryDep = Annotated[EvaluationRepository, Depends(get_evaluation_repository)]
StoreRepositoryDep = Annotated[StoreRepository, Depends(get_store_repository)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
GeminiServiceDep = Annotated[GeminiService, Depends(get_gemini_service)]
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
CustomerAgentServiceDep = Annotated[CustomerAgentService, Depends(get_customer_agent_service)]
CoachAgentServiceDep = Annotated[CoachAgentService, Depends(get_coach_agent_service)]
RAGServiceDep = Annotated[FirestoreRAGService, Depends(get_rag_service_dep)]
ObjectionServiceDep = Annotated[ObjectionLookupService, Depends(get_objection_service_dep)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
