"""Scoring functions for coach agent evaluation.

This module implements the scoring algorithm for C.O.R.E. selling system
evaluations. Scores are calculated based on:
- Weighted stage completion (CONNECT 15%, OBSERVE 30%, RECOMMEND 30%, EXECUTE 25%)
- Customer Motivator bonus (up to +10 for high match rate)
- Objection penalty (up to -10 for poor handling)
- Deviation penalty (up to -15 for skipping stages)
"""

from app.agents.state import CoreStageProgress
from app.models.evaluation import Grade

# Stage weights for overall score calculation
STAGE_WEIGHTS: dict[str, float] = {
    "connect": 0.15,
    "observe": 0.30,
    "recommend": 0.30,
    "execute": 0.25,
}

# Grade thresholds
GRADE_THRESHOLDS: dict[Grade, int] = {
    Grade.A: 90,
    Grade.B: 80,
    Grade.C: 70,
    Grade.D: 60,
    Grade.F: 0,
}

# Customer Motivator bonus configuration
PBM_BONUS_MAX = 10.0
PBM_MATCH_THRESHOLD_FULL = 1.0  # 100% match = full bonus
PBM_MATCH_THRESHOLD_HALF = 0.5  # 50% match = half bonus

# Objection penalty configuration
OBJECTION_PENALTY_MAX = -10.0
OBJECTION_RESOLUTION_THRESHOLD = 0.5  # Below 50% resolution = penalty

# Deviation penalty configuration (Evaluation mode only)
DEVIATION_PENALTY_PER_SKIP = -5.0
DEVIATION_PENALTY_MAX = -15.0


def calculate_stage_score(
    items_completed: list[str],
    items_total: list[str],
) -> float:
    """Calculate score for a single stage.

    Args:
        items_completed: List of completed checklist item IDs
        items_total: List of all checklist item IDs for the stage

    Returns:
        Score from 0.0 to 100.0
    """
    if not items_total:
        return 0.0

    completed_count = len([item for item in items_completed if item in items_total])
    return (completed_count / len(items_total)) * 100.0


def calculate_pbm_bonus(
    pbms_expressed: list[str],
    pbms_acknowledged: list[str],
) -> float:
    """Calculate bonus points for Customer Motivator handling.

    Args:
        pbms_expressed: Motivators the customer mentioned
        pbms_acknowledged: Motivators the salesperson acknowledged

    Returns:
        Bonus from 0.0 to PBM_BONUS_MAX (10.0)
    """
    if not pbms_expressed:
        return 0.0

    # Calculate match rate (how many expressed motivators were acknowledged)
    acknowledged_count = len([pbm for pbm in pbms_acknowledged if pbm in pbms_expressed])
    match_rate = acknowledged_count / len(pbms_expressed)

    if match_rate >= PBM_MATCH_THRESHOLD_FULL:
        return PBM_BONUS_MAX
    elif match_rate >= PBM_MATCH_THRESHOLD_HALF:
        return PBM_BONUS_MAX * match_rate
    else:
        return PBM_BONUS_MAX * match_rate * 0.5  # Reduced bonus for low match


def calculate_objection_penalty(
    objections_raised: list[str],
    objections_resolved: list[str],
) -> float:
    """Calculate penalty for poor objection handling.

    Args:
        objections_raised: Objections raised by customer
        objections_resolved: Objections successfully handled

    Returns:
        Penalty from OBJECTION_PENALTY_MAX (-10.0) to 0.0
    """
    if not objections_raised:
        return 0.0

    resolution_rate = len(objections_resolved) / len(objections_raised)

    if resolution_rate >= OBJECTION_RESOLUTION_THRESHOLD:
        return 0.0
    else:
        # Penalty scales with how poorly objections were handled
        penalty_factor = 1.0 - (resolution_rate / OBJECTION_RESOLUTION_THRESHOLD)
        return OBJECTION_PENALTY_MAX * penalty_factor


def calculate_deviation_penalty(deviations: list[str]) -> float:
    """Calculate penalty for C.O.R.E. stage deviations.

    Args:
        deviations: List of deviation descriptions

    Returns:
        Penalty from DEVIATION_PENALTY_MAX (-15.0) to 0.0
    """
    if not deviations:
        return 0.0

    penalty = len(deviations) * DEVIATION_PENALTY_PER_SKIP
    return max(penalty, DEVIATION_PENALTY_MAX)


def calculate_grade(score: float) -> Grade:
    """Convert numeric score to letter grade.

    Args:
        score: Final score (0-100)

    Returns:
        Letter grade (A, B, C, D, or F)
    """
    if score >= GRADE_THRESHOLDS[Grade.A]:
        return Grade.A
    elif score >= GRADE_THRESHOLDS[Grade.B]:
        return Grade.B
    elif score >= GRADE_THRESHOLDS[Grade.C]:
        return Grade.C
    elif score >= GRADE_THRESHOLDS[Grade.D]:
        return Grade.D
    else:
        return Grade.F


def calculate_score(
    stage_progress: CoreStageProgress,
    objections_raised: list[str] | None = None,
    objections_resolved: list[str] | None = None,
    deviations: list[str] | None = None,
) -> tuple[float, float, Grade]:
    """Calculate complete evaluation score.

    Args:
        stage_progress: Progress through C.O.R.E. stages
        objections_raised: Customer objections raised
        objections_resolved: Objections successfully handled
        deviations: C.O.R.E. deviations detected

    Returns:
        Tuple of (raw_score, final_score, grade)
    """
    objections_raised = objections_raised or []
    objections_resolved = objections_resolved or []
    deviations = deviations or []

    # Calculate stage scores
    stage_scores: dict[str, float] = {}

    # CONNECT stage
    connect_items_total = list(stage_progress.connect.keys())
    connect_items_completed = [k for k, v in stage_progress.connect.items() if v]
    stage_scores["connect"] = calculate_stage_score(connect_items_completed, connect_items_total)

    # OBSERVE stage
    observe_items_total = list(stage_progress.observe.keys())
    observe_items_completed = [k for k, v in stage_progress.observe.items() if v]
    stage_scores["observe"] = calculate_stage_score(observe_items_completed, observe_items_total)

    # RECOMMEND stage
    recommend_items_total = list(stage_progress.recommend.keys())
    recommend_items_completed = [k for k, v in stage_progress.recommend.items() if v]
    stage_scores["recommend"] = calculate_stage_score(
        recommend_items_completed, recommend_items_total
    )

    # EXECUTE stage
    execute_items_total = list(stage_progress.execute.keys())
    execute_items_completed = [k for k, v in stage_progress.execute.items() if v]
    stage_scores["execute"] = calculate_stage_score(execute_items_completed, execute_items_total)

    # Calculate weighted raw score
    raw_score = sum(stage_scores[stage] * weight for stage, weight in STAGE_WEIGHTS.items())

    # Calculate bonuses and penalties
    pbm_bonus = calculate_pbm_bonus(
        stage_progress.pbms_expressed,
        stage_progress.pbms_acknowledged,
    )
    objection_penalty = calculate_objection_penalty(objections_raised, objections_resolved)
    deviation_penalty = calculate_deviation_penalty(deviations)

    # Calculate final score (clamped to 0-100)
    final_score = raw_score + pbm_bonus + objection_penalty + deviation_penalty
    final_score = max(0.0, min(100.0, final_score))

    grade = calculate_grade(final_score)

    return raw_score, final_score, grade
