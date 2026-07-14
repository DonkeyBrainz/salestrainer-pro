"""Coach agent models for real-time analysis and intervention.

This module defines the data structures used by the coach agent to analyze
salesperson messages, detect C.O.R.E. technique usage, and determine
appropriate interventions during training sessions.
"""

from enum import Enum

from pydantic import BaseModel, Field


class SessionMode(str, Enum):
    """Mode determining coach behavior during session.

    - TRAINING: Active coaching with real-time hints and audio interventions
    - EVALUATION: Silent observation with report only at session end
    """

    TRAINING = "training"
    EVALUATION = "evaluation"


class InterventionLevel(str, Enum):
    """Severity level of coach intervention.

    Determines how the intervention is delivered to the salesperson:
    - NONE: No intervention needed
    - INFO: Positive feedback (text toast)
    - SUGGESTION: Missed opportunity (text banner)
    - WARNING: Deviation from C.O.R.E. (text + visual highlight)
    - CRITICAL: Major deviation requiring pause (audio interruption)
    """

    NONE = "none"
    INFO = "info"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    CRITICAL = "critical"


class StageItemUpdate(BaseModel):
    """Update to a specific stage checklist item."""

    stage: str = Field(..., description="Stage name (CONNECT, OBSERVE, RECOMMEND, EXECUTE)")
    item: str = Field(..., description="Checklist item ID")
    completed: bool = Field(..., description="Whether item was completed")


class CoachAnalysisResponse(BaseModel):
    """Wire schema for the coach LLM's structured output.

    Passed to Gemini as ``response_schema`` so the SDK guarantees shape and
    enum validity. Mirrors CoachAnalysis minus code-owned fields
    (``confidence`` is set by the analyzer, never by the model); the analyzer
    finalizes this into a CoachAnalysis (template hint fallback, confidence).
    """

    techniques_detected: list[str] = Field(
        default_factory=list,
        description="C.O.R.E. technique IDs observed in the salesperson message",
    )
    stage_items_completed: list[StageItemUpdate] = Field(
        default_factory=list,
        description="Checklist items completed by this message (completed=true)",
    )
    pbms_acknowledged: list[str] = Field(
        default_factory=list,
        description="Customer motivators the salesperson acknowledged in this turn",
    )
    deviations: list[str] = Field(
        default_factory=list,
        description="C.O.R.E. deviation IDs detected",
    )
    intervention_level: InterventionLevel = Field(
        InterventionLevel.NONE,
        description="Severity of intervention needed",
    )
    hint: str | None = Field(
        None,
        description="Coaching hint text if intervention needed, else null",
    )
    example_phrase: str | None = Field(
        None,
        description="Word-for-word example phrase the salesperson could say next, or null",
    )
    ready_for_next_stage: bool = Field(
        False,
        description="True when all current-stage checklist items are complete",
    )
    suggested_stage: str | None = Field(
        None,
        description="Stage to transition to (CONNECT/OBSERVE/RECOMMEND/EXECUTE), or null",
    )


class CoachAnalysis(BaseModel):
    """Result of coach agent analyzing a salesperson message.

    The coach analyzes each salesperson turn to:
    1. Detect C.O.R.E. techniques being used
    2. Track stage progress (checklist items completed)
    3. Identify PBM acknowledgments
    4. Detect deviations from the selling system
    5. Determine if intervention is needed
    """

    # Technique detection
    techniques_detected: list[str] = Field(
        default_factory=list,
        description="C.O.R.E. techniques observed (e.g., 'non_business_greet', 'layer2_discovery')",
    )

    # Stage progress updates
    stage_items_completed: list[StageItemUpdate] = Field(
        default_factory=list,
        description="Checklist items completed by this message",
    )

    # PBM tracking
    pbms_acknowledged: list[str] = Field(
        default_factory=list,
        description="PBMs the salesperson acknowledged in this turn",
    )

    # Deviation detection
    deviations: list[str] = Field(
        default_factory=list,
        description="C.O.R.E. deviations (e.g., 'skipped_critical_questions', 'pushed_product_too_early')",
    )

    # Intervention decision
    intervention_level: InterventionLevel = Field(
        InterventionLevel.NONE,
        description="Severity of intervention needed",
    )
    hint: str | None = Field(
        None,
        description="Coaching hint text (for SUGGESTION/WARNING/CRITICAL)",
    )

    # Example phrase for the salesperson
    example_phrase: str | None = Field(
        default=None,
        description="Word-for-word example phrase the salesperson could say next",
    )

    # Ready for next stage indicator
    ready_for_next_stage: bool = Field(
        default=False,
        description="Whether all current stage items are complete and salesperson should transition",
    )

    # Suggested stage transition
    suggested_stage: str | None = Field(
        None,
        description="Stage the coach suggests transitioning to (if applicable)",
    )

    # Confidence score (for logging/debugging)
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this analysis (0-1)",
    )


class CoachHint(BaseModel):
    """Coaching hint sent to the frontend.

    Used for text-based interventions (INFO, SUGGESTION, WARNING).
    Delivered via WebSocket as a JSON message.
    """

    level: InterventionLevel = Field(..., description="Intervention severity")
    hint: str = Field(..., description="Coaching message text")
    stage: str = Field(..., description="Current C.O.R.E. stage")
    example_phrase: str | None = Field(
        None, description="Word-for-word example phrase the salesperson could say next"
    )
    ready_for_next_stage: bool = Field(
        False, description="Whether salesperson should transition to the next stage"
    )


class FeedbackResponse(BaseModel):
    """Structured output schema for post-session narrative feedback.

    Used as the response_schema for the evaluation feedback LLM call.
    """

    strengths: list[str] = Field(
        default_factory=list, description="Specific strengths observed in the session"
    )
    improvements: list[str] = Field(
        default_factory=list, description="Specific improvement areas for the trainee"
    )


class CoachAudioIntervention(BaseModel):
    """Audio intervention for critical deviations (Training mode only).

    The coach speaks directly to interrupt the session and redirect
    the salesperson back to proper C.O.R.E. technique.
    """

    transcript: str = Field(..., description="What the coach will say")
    audio_base64: str | None = Field(None, description="Base64-encoded PCM audio bytes")
