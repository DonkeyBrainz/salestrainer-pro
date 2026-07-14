"""Runner that drives CustomerAgentGraph through a scripted scenario.

Mirrors production usage (CustomerAgentService): the graph is compiled with a
MemorySaver checkpointer, and every ``invoke`` passes the same per-scenario
thread_id so turn N+1 resumes turn N's checkpointed state.

``random.seed(scenario.seed)`` is set before each scenario so the graph's
probabilistic mood/objection behavior is reproducible across runs.
"""

import random
import time
import uuid
from typing import cast

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.customer_agent import CustomerAgentGraph
from app.agents.personas import get_persona
from app.agents.state import CoreStageProgress, CustomerAgentState, SalesStage
from app.config import Settings, get_settings
from app.llm_providers import LLMProvider
from evals.report.models import ScenarioResult, TurnRecord
from evals.scenarios.types import CustomerScenario


def _initial_state(scenario: CustomerScenario, session_id: str) -> CustomerAgentState:
    """Build the initial agent state from the scenario's persona."""
    persona = get_persona(scenario.persona_id)
    if persona is None:
        raise ValueError(f"Unknown persona_id: {scenario.persona_id!r}")

    from app.agents.state import Mood

    return {
        "messages": [],
        "turn_count": 0,
        "persona": persona,
        "mood": scenario.initial_mood or Mood.NEUTRAL,
        "regard_level": persona.initial_regard,
        "objections_available": list(persona.objections),
        "objections_raised": [],
        "objections_resolved": [],
        "stage_progress": CoreStageProgress(current_stage=SalesStage.CONNECT),
        "session_id": session_id,
        "user_id": "eval-harness",
    }


async def run_customer_scenario(
    scenario: CustomerScenario,
    provider: LLMProvider,
    settings: Settings | None = None,
) -> ScenarioResult:
    """Run a scripted customer scenario and capture the per-turn transcript.

    Deterministic checks are applied separately (evals.checks.customer_checks);
    this function only executes and records.
    """
    settings = settings or get_settings()
    session_id = f"eval-{scenario.id}-{uuid.uuid4().hex[:8]}"

    random.seed(scenario.seed)
    agent = CustomerAgentGraph(settings, provider=provider)

    state = _initial_state(scenario, session_id)
    turns: list[TurnRecord] = []
    total_latency = 0.0
    usage_totals: dict[str, int] = {}

    try:
        for i, turn in enumerate(scenario.turns):
            mood_before = state["mood"].value
            regard_before = state["regard_level"].value
            raised_before = list(state["objections_raised"])

            # Mirror CustomerAgentService: full state with the new message appended.
            updated: CustomerAgentState = {
                **state,
                "messages": list(state["messages"])
                + [HumanMessage(content=turn.salesperson_message)],
            }

            started = time.monotonic()
            state = await agent.invoke(updated, thread_id=session_id)
            latency_ms = (time.monotonic() - started) * 1000
            total_latency += latency_ms

            response_text = ""
            if state["messages"] and isinstance(state["messages"][-1], AIMessage):
                response_text = str(state["messages"][-1].content)

            turn_usage = cast(dict[str, int] | None, state.get("_last_usage"))
            if turn_usage:
                for key, value in turn_usage.items():
                    usage_totals[key] = usage_totals.get(key, 0) + value

            turns.append(
                TurnRecord(
                    turn_index=i,
                    salesperson_message=turn.salesperson_message,
                    response_text=response_text,
                    mood_before=mood_before,
                    mood_after=state["mood"].value,
                    regard_before=regard_before,
                    regard_after=state["regard_level"].value,
                    objections_raised_before=raised_before,
                    objections_raised_after=list(state["objections_raised"]),
                    latency_ms=latency_ms,
                    usage=turn_usage,
                )
            )
    except Exception as e:  # noqa: BLE001 - a failing scenario must not kill the run
        return ScenarioResult(
            scenario_id=scenario.id,
            tags=scenario.tags,
            passed=False,
            turns=turns,
            total_latency_ms=total_latency,
            usage=usage_totals,
            error=f"{type(e).__name__}: {e}",
        )

    return ScenarioResult(
        scenario_id=scenario.id,
        tags=scenario.tags,
        passed=True,  # provisional; checks decide the final value
        turns=turns,
        total_latency_ms=total_latency,
        usage=usage_totals,
    )
