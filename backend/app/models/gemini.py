"""Gemini API models for text generation requests and responses."""

from pydantic import BaseModel, Field


class GeminiRequest(BaseModel):
    """Request for text generation using Gemini."""

    prompt: str = Field(..., min_length=1, description="The text prompt for generation")
    temperature: float | None = Field(
        None, ge=0.0, le=2.0, description="Override default temperature"
    )
    max_tokens: int | None = Field(
        None, gt=0, le=8192, alias="maxTokens", description="Override default max output tokens"
    )

    model_config = {"populate_by_name": True}


class UsageMetadata(BaseModel):
    """Token usage statistics from Gemini response."""

    prompt_token_count: int = Field(
        serialization_alias="promptTokenCount", description="Tokens in prompt"
    )
    candidates_token_count: int = Field(
        serialization_alias="candidatesTokenCount", description="Tokens in response"
    )
    total_token_count: int = Field(
        serialization_alias="totalTokenCount", description="Total tokens used"
    )


class ModelInfo(BaseModel):
    """Information about the model used for generation."""

    model: str = Field(description="Model identifier")
    temperature: float = Field(description="Temperature used")
    max_tokens: int = Field(serialization_alias="maxTokens", description="Max tokens configured")


class GeminiResponse(BaseModel):
    """Response from Gemini text generation."""

    text: str = Field(description="Generated text content")
    usage: UsageMetadata = Field(description="Token usage statistics")
    model_info: ModelInfo = Field(
        serialization_alias="modelInfo", description="Model configuration used"
    )


class GeminiStreamChunk(BaseModel):
    """Streaming chunk from Gemini generation."""

    text: str = Field(description="Incremental text content")
    is_final: bool = Field(
        default=False,
        serialization_alias="isFinal",
        description="Whether this is the final chunk",
    )
