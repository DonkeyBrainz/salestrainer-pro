"""Deterministic rule-based checks for coach-agent scenario results.

Scorer arithmetic (app/agents/coach/scorer.py) is deliberately NOT re-checked
here — it is pure code with no model involved and is covered by the existing
pytest suite (backend/tests/unit/test_coach_scorer.py).
"""

from app.models.coach import InterventionLevel
from evals.report.models import CheckResult, CoachCaseRecord, ScenarioResult
from evals.scenarios.types import CoachScenario, CoachTurnCase

_INTERVENTION_ORDER = [
    InterventionLevel.NONE.value,
    InterventionLevel.INFO.value,
    InterventionLevel.SUGGESTION.value,
    InterventionLevel.WARNING.value,
    InterventionLevel.CRITICAL.value,
]


def check_analysis_produced(case: CoachCaseRecord) -> CheckResult:
    """Verify the analyzer produced a real analysis, not its error fallback.

    CoachAnalyzer returns a safe default with confidence=0.0 when the LLM call
    fails or yields no structured output.
    """
    name = f"case{case.case_index}.analysis_produced"
    confidence = case.analysis.get("confidence", 0.0)
    return CheckResult(
        name=name,
        passed=confidence > 0.0,
        reason="" if confidence > 0.0 else "analyzer returned its error/empty fallback",
    )


def check_hint_populated(case: CoachCaseRecord) -> CheckResult | None:
    """Verify hint text exists whenever an intervention is flagged."""
    level = case.analysis.get("intervention_level", InterventionLevel.NONE.value)
    if level == InterventionLevel.NONE.value:
        return None
    name = f"case{case.case_index}.hint_populated"
    hint = case.analysis.get("hint")
    return CheckResult(
        name=name,
        passed=bool(hint),
        reason="" if hint else f"intervention_level={level} but hint is empty",
    )


def check_technique_recall(case: CoachCaseRecord, expected: CoachTurnCase) -> CheckResult | None:
    """Verify at least one expected technique was detected."""
    if not expected.expect_techniques_any_of:
        return None
    name = f"case{case.case_index}.technique_recall"
    detected = set(case.analysis.get("techniques_detected", []))
    wanted = set(expected.expect_techniques_any_of)
    hit = detected & wanted
    return CheckResult(
        name=name,
        passed=bool(hit),
        reason="" if hit else f"expected any of {sorted(wanted)}, detected {sorted(detected)}",
    )


def check_deviation_flagging(case: CoachCaseRecord, expected: CoachTurnCase) -> CheckResult | None:
    """Verify deviations are flagged iff the scenario expects them."""
    if expected.expect_deviation_flagged is None:
        return None
    name = f"case{case.case_index}.deviation_flagging"
    deviations = case.analysis.get("deviations", [])
    ok = bool(deviations) == expected.expect_deviation_flagged
    return CheckResult(
        name=name,
        passed=ok,
        reason=""
        if ok
        else f"expected deviation_flagged={expected.expect_deviation_flagged}, got {deviations}",
    )


def check_intervention_level(case: CoachCaseRecord, expected: CoachTurnCase) -> CheckResult | None:
    """Verify the intervention level meets the scenario's minimum severity."""
    if expected.expect_intervention_at_least is None:
        return None
    name = f"case{case.case_index}.intervention_level"
    actual = case.analysis.get("intervention_level", InterventionLevel.NONE.value)
    want = expected.expect_intervention_at_least.value
    ok = _INTERVENTION_ORDER.index(actual) >= _INTERVENTION_ORDER.index(want)
    return CheckResult(
        name=name,
        passed=ok,
        reason="" if ok else f"expected intervention >= {want}, got {actual}",
    )


def check_stage_readiness(case: CoachCaseRecord, expected: CoachTurnCase) -> CheckResult | None:
    """Verify ready_for_next_stage matches the scenario expectation."""
    if expected.expect_ready_for_next_stage is None:
        return None
    name = f"case{case.case_index}.stage_readiness"
    actual = bool(case.analysis.get("ready_for_next_stage", False))
    ok = actual == expected.expect_ready_for_next_stage
    return CheckResult(
        name=name,
        passed=ok,
        reason=""
        if ok
        else f"expected ready_for_next_stage={expected.expect_ready_for_next_stage}, got {actual}",
    )


def run_coach_checks(scenario: CoachScenario, result: ScenarioResult) -> list[CheckResult]:
    """Run all deterministic checks for a coach scenario result."""
    checks: list[CheckResult] = []
    if result.error:
        checks.append(CheckResult(name="scenario_completed", passed=False, reason=result.error))
        return checks

    for case, expected in zip(result.cases, scenario.cases, strict=False):
        checks.append(check_analysis_produced(case))
        for check in (
            check_hint_populated(case),
            check_technique_recall(case, expected),
            check_deviation_flagging(case, expected),
            check_intervention_level(case, expected),
            check_stage_readiness(case, expected),
        ):
            if check is not None:
                checks.append(check)
    return checks
