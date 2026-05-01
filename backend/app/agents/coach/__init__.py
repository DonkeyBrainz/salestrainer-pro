"""Coach agent package for real-time sales coaching and evaluation.

The coach agent observes sales training sessions and provides:
- Real-time technique detection (E.A.S.Y. method analysis)
- Stage progression tracking
- Intervention hints (Training mode) or silent observation (Evaluation mode)
- Post-session scoring and feedback
"""

from app.agents.coach.analyzer import CoachAnalyzer
from app.agents.coach.hints import (
    HINT_TEMPLATES,
    get_hint_for_stage,
    get_intervention_message,
)
from app.agents.coach.prompts import (
    COACH_ANALYSIS_PROMPT,
    build_coach_prompt,
)
from app.agents.coach.scorer import (
    GRADE_THRESHOLDS,
    STAGE_WEIGHTS,
    calculate_grade,
    calculate_pbm_bonus,
    calculate_score,
    calculate_stage_score,
)

__all__ = [
    # Analyzer
    "CoachAnalyzer",
    # Prompts
    "COACH_ANALYSIS_PROMPT",
    "build_coach_prompt",
    # Scorer
    "GRADE_THRESHOLDS",
    "STAGE_WEIGHTS",
    "calculate_grade",
    "calculate_pbm_bonus",
    "calculate_score",
    "calculate_stage_score",
    # Hints
    "HINT_TEMPLATES",
    "get_hint_for_stage",
    "get_intervention_message",
]
