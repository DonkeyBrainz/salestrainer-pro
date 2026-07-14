"""Runner that drives CoachAnalyzer.analyze() through scripted cases.

The coach is turn-based text (no LangGraph): each case supplies the
salesperson message, a scripted conversation history, and the stage progress
going into the turn.
"""

import time

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agents.coach.analyzer import CoachAnalyzer
from app.agents.personas import get_persona
from app.agents.state import CoreStageProgress
from app.llm_providers import LLMProvider
from evals.report.models import CoachCaseRecord, ScenarioResult
from evals.scenarios.types import CoachScenario, CoachTurnCase


def _to_messages(conversation: list[dict[str, str]]) -> list[BaseMessage]:
    """Convert scripted role/content pairs to LangChain messages.

    In this system the salesperson is "user" (HumanMessage) and the customer
    is "assistant" (AIMessage).
    """
    messages: list[BaseMessage] = []
    for entry in conversation:
        role = entry.get("role", "user")
        content = entry.get("content", "")
        if role == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


def _to_stage_progress(case: CoachTurnCase) -> CoreStageProgress:
    """Build CoreStageProgress from the case's partial override dict."""
    return CoreStageProgress.model_validate(case.stage_progress_before)


async def run_coach_scenario(
    scenario: CoachScenario,
    provider: LLMProvider,
    model: str | None = None,
) -> ScenarioResult:
    """Run all cases in a coach scenario and capture the analyses.

    Deterministic checks are applied separately (evals.checks.coach_checks);
    this function only executes and records.
    """
    persona = get_persona(scenario.persona_id)
    if persona is None:
        raise ValueError(f"Unknown persona_id: {scenario.persona_id!r}")

    analyzer = CoachAnalyzer(model=model, provider=provider)
    cases: list[CoachCaseRecord] = []
    total_latency = 0.0

    try:
        for i, case in enumerate(scenario.cases):
            started = time.monotonic()
            analysis = await analyzer.analyze(
                salesperson_message=case.salesperson_message,
                messages=_to_messages(case.conversation_so_far),
                persona=persona,
                stage_progress=_to_stage_progress(case),
            )
            latency_ms = (time.monotonic() - started) * 1000
            total_latency += latency_ms

            cases.append(
                CoachCaseRecord(
                    case_index=i,
                    salesperson_message=case.salesperson_message,
                    analysis=analysis.model_dump(mode="json"),
                    latency_ms=latency_ms,
                )
            )
    except Exception as e:  # noqa: BLE001 - a failing scenario must not kill the run
        return ScenarioResult(
            scenario_id=scenario.id,
            tags=scenario.tags,
            passed=False,
            cases=cases,
            total_latency_ms=total_latency,
            error=f"{type(e).__name__}: {e}",
        )

    return ScenarioResult(
        scenario_id=scenario.id,
        tags=scenario.tags,
        passed=True,  # provisional; checks decide the final value
        cases=cases,
        total_latency_ms=total_latency,
    )
