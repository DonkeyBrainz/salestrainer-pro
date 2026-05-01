# Pydantic models

from app.models.auth import (
    CallbackRequest,
    GoogleUserInfo,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
    TokenPayload,
    TokenResponse,
)
from app.models.coach import (
    CoachAnalysis,
    CoachAudioIntervention,
    CoachHint,
    InterventionLevel,
    SessionMode,
    StageItemUpdate,
)
from app.models.evaluation import (
    Evaluation,
    EvaluationCreate,
    EvaluationResponse,
    EvaluationScorecard,
    Grade,
    StageScore,
)
from app.models.gemini import (
    GeminiRequest,
    GeminiResponse,
    GeminiStreamChunk,
    ModelInfo,
    UsageMetadata,
)
from app.models.session import (
    Difficulty,
    Session,
    SessionCreate,
    SessionResponse,
    SessionStatus,
    SessionType,
    SessionUpdate,
)
from app.models.transcript import (
    MessageRole,
    Transcript,
    TranscriptCreate,
    TranscriptMessage,
    TranscriptResponse,
)
from app.models.user import (
    User,
    UserBase,
    UserCreate,
    UserPreferences,
    UserResponse,
)

__all__ = [
    # Auth models
    "CallbackRequest",
    "GoogleUserInfo",
    "LoginRequest",
    "LoginResponse",
    "LogoutRequest",
    "LogoutResponse",
    "RefreshRequest",
    "RefreshResponse",
    "TokenPayload",
    "TokenResponse",
    # Gemini models
    "GeminiRequest",
    "GeminiResponse",
    "GeminiStreamChunk",
    "ModelInfo",
    "UsageMetadata",
    # Session models
    "Difficulty",
    "Session",
    "SessionCreate",
    "SessionResponse",
    "SessionStatus",
    "SessionType",
    "SessionUpdate",
    # Transcript models
    "MessageRole",
    "Transcript",
    "TranscriptCreate",
    "TranscriptMessage",
    "TranscriptResponse",
    # User models
    "User",
    "UserBase",
    "UserCreate",
    "UserPreferences",
    "UserResponse",
    # Coach models
    "CoachAnalysis",
    "CoachAudioIntervention",
    "CoachHint",
    "InterventionLevel",
    "SessionMode",
    "StageItemUpdate",
    # Evaluation models
    "Evaluation",
    "EvaluationCreate",
    "EvaluationResponse",
    "EvaluationScorecard",
    "Grade",
    "StageScore",
]
