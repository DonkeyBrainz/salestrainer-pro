"""Deterministic rule-based checks for customer-agent scenario results.

These operate on the captured transcript/state only — no LLM calls. They form
the hard pass/fail gate for a scenario; judge scores are a separate soft
signal.
"""

from app.agents.personas import get_persona
from app.agents.state import Mood
from evals.report.models import CheckResult, ScenarioResult, TurnRecord
from evals.scenarios.types import CustomerScenario, CustomerTurnTrigger

# Worst -> best, matching the progression ladder in CustomerAgentGraph.
_MOOD_ORDER = [
    Mood.FRUSTRATED.value,
    Mood.SKEPTICAL.value,
    Mood.NEUTRAL.value,
    Mood.INTERESTED.value,
    Mood.READY_TO_BUY.value,
]


def _mood_rank(mood: str | None) -> int:
    return _MOOD_ORDER.index(mood) if mood in _MOOD_ORDER else -1


def check_mood_transition(turn: TurnRecord, expected: CustomerTurnTrigger) -> CheckResult | None:
    """Verify the mood moved as the scenario expects after this turn."""
    name = f"turn{turn.turn_index}.mood_transition"

    if expected.expected_mood_after is not None:
        actual = turn.mood_after
        want = expected.expected_mood_after.value
        return CheckResult(
            name=name,
            passed=actual == want,
            reason="" if actual == want else f"expected mood {want}, got {actual}",
        )

    if expected.expected_mood_direction is not None:
        before, after = _mood_rank(turn.mood_before), _mood_rank(turn.mood_after)
        direction = expected.expected_mood_direction
        ok = {
            "improve": after > before,
            "worsen": after < before,
            "same": after == before,
            "same_or_worse": after <= before,
        }[direction]
        return CheckResult(
            name=name,
            passed=ok,
            reason=""
            if ok
            else f"expected mood to {direction} from {turn.mood_before}, got {turn.mood_after}",
        )

    return None


def check_objection_injection(
    turn: TurnRecord, expected: CustomerTurnTrigger, scenario: CustomerScenario
) -> CheckResult | None:
    """Verify an objection was raised on this turn, drawn from the persona pool."""
    if not expected.inject_objection_expected:
        return None

    name = f"turn{turn.turn_index}.objection_injected"
    new_objections = [
        o for o in turn.objections_raised_after if o not in turn.objections_raised_before
    ]
    if not new_objections:
        return CheckResult(name=name, passed=False, reason="no objection was injected")

    persona = get_persona(scenario.persona_id)
    pool = set(persona.objections) if persona else set()
    stray = [o for o in new_objections if o not in pool]
    if stray:
        return CheckResult(
            name=name, passed=False, reason=f"objection not from persona pool: {stray}"
        )
    return CheckResult(name=name, passed=True)


def check_no_forbidden_phrases(
    turn: TurnRecord, expected: CustomerTurnTrigger
) -> CheckResult | None:
    """Verify the generated response contains none of the forbidden substrings."""
    if not expected.forbid_phrases:
        return None

    name = f"turn{turn.turn_index}.no_forbidden_phrases"
    text = turn.response_text.lower()
    found = [p for p in expected.forbid_phrases if p.lower() in text]
    return CheckResult(
        name=name,
        passed=not found,
        reason="" if not found else f"forbidden phrases in response: {found}",
    )


def run_customer_checks(scenario: CustomerScenario, result: ScenarioResult) -> list[CheckResult]:
    """Run all deterministic checks for a customer scenario result."""
    checks: list[CheckResult] = []
    if result.error:
        checks.append(CheckResult(name="scenario_completed", passed=False, reason=result.error))
        return checks

    for turn, expected in zip(result.turns, scenario.turns, strict=False):
        for check in (
            check_mood_transition(turn, expected),
            check_objection_injection(turn, expected, scenario),
            check_no_forbidden_phrases(turn, expected),
        ):
            if check is not None:
                checks.append(check)
    return checks
