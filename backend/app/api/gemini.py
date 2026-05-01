"""Gemini API endpoints for text generation."""

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUserDep, GeminiServiceDep
from app.models.gemini import GeminiRequest, GeminiResponse

router = APIRouter(prefix="/gemini", tags=["Gemini"])


@router.post("/generate", response_model=GeminiResponse, status_code=status.HTTP_200_OK)
async def generate_text(
    request: GeminiRequest,
    gemini_service: GeminiServiceDep,
    current_user: CurrentUserDep,
) -> GeminiResponse:
    """Generate text using Gemini model.

    Requires authentication. Uses the configured Gemini model to generate
    text based on the provided prompt.

    Args:
        request: Generation request with prompt and optional parameters
        gemini_service: Gemini service instance (injected)
        current_user: Authenticated user (injected, ensures auth)

    Returns:
        GeminiResponse with generated text and metadata
    """
    return await gemini_service.generate(request)
