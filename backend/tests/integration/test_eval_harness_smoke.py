"""Smoke tests for the eval harness wiring.

These do NOT judge agent quality — they run one scenario per suite with a
mocked provider to assert the harness's own code (scenario loading, runners,
checks, aggregation, report serialization) doesn't break.
"""

import json
from unittest.mock import AsyncMock

import pytest

from app.llm_providers import CompletionResult
from app.models.coach import CoachAnalysisResponse, InterventionLevel
from evals import HARNESS_VERSION
from evals.checks.coach_checks import run_coach_checks
from evals.checks.customer_checks import run_customer_checks
from evals.report.aggregate import compare, summarize
from evals.report.models import RunReport
from evals.report.render import render_comparison_console, render_run_console
from evals.runners.coach_runner import run_coach_scenario
from evals.runners.customer_runner import run_customer_scenario
from evals.scenarios.types import load_coach_scenarios, load_customer_scenarios


@pytest.fixture
def mock_provider() -> AsyncMock:
    """Provider whose completions are canned and cost nothing."""
    provider = AsyncMock()
    provider.name = "mock"
    provider.complete.return_value = CompletionResult(
        text="Well, I'd have to think about that.",
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )
    provider.complete_structured.return_value = CompletionResult(
        text="{}",
        parsed=CoachAnalysisResponse(
            techniques_detected=["warm_greeting"],
            intervention_level=InterventionLevel.NONE,
        ),
    )
    return provider


class TestScenarioLoading:
    def test_customer_scenarios_load_and_validate(self) -> None:
        scenarios = load_customer_scenarios()
        assert len(scenarios) >= 8
        assert all(s.turns for s in scenarios)

    def test_coach_scenarios_load_and_validate(self) -> None:
        scenarios = load_coach_scenarios()
        assert len(scenarios) >= 8
        assert all(s.cases for s in scenarios)

    def test_tag_filtering(self) -> None:
        all_scenarios = load_customer_scenarios()
        filtered = load_customer_scenarios(tags=["behavior:insult"])
        assert 0 < len(filtered) < len(all_scenarios)
        assert all("behavior:insult" in s.tags for s in filtered)


class TestCustomerRunner:
    async def test_runs_scenario_and_checks(self, mock_provider: AsyncMock) -> None:
        from app.config import get_settings

        scenario = next(
            s for s in load_customer_scenarios() if s.id == "renovator_insult_then_recovery"
        )
        result = await run_customer_scenario(scenario, mock_provider, get_settings())

        assert result.error is None
        assert len(result.turns) == len(scenario.turns)
        assert result.turns[0].response_text == "Well, I'd have to think about that."

        checks = run_customer_checks(scenario, result)
        # Insult worsens and high-regard acknowledgment improves — both
        # deterministic, so the mood checks pass even with a mocked LLM.
        mood_checks = [c for c in checks if "mood_transition" in c.name]
        assert mood_checks and all(c.passed for c in mood_checks)


class TestCoachRunner:
    async def test_runs_scenario_and_checks(self, mock_provider: AsyncMock) -> None:
        scenario = next(s for s in load_coach_scenarios() if s.id == "connect_greeting_detected")
        result = await run_coach_scenario(scenario, mock_provider)

        assert result.error is None
        assert len(result.cases) == 1
        checks = run_coach_checks(scenario, result)
        by_name = {c.name: c for c in checks}
        assert by_name["case0.analysis_produced"].passed
        assert by_name["case0.technique_recall"].passed
        assert by_name["case0.deviation_flagging"].passed


class TestReporting:
    async def test_report_roundtrip_and_compare(self, mock_provider: AsyncMock) -> None:
        scenario = next(s for s in load_coach_scenarios() if s.id == "connect_greeting_detected")
        result = await run_coach_scenario(scenario, mock_provider)
        result.checks = run_coach_checks(scenario, result)
        result.passed = all(c.passed for c in result.checks)

        report = RunReport(
            harness_version=HARNESS_VERSION,
            run_id="test-run",
            provider_name="mock",
            model="mock-model",
            suite="coach",
            scenario_results=[result],
            summary=summarize([result]),
        )

        # JSON round-trip must be lossless (this is the --compare contract).
        restored = RunReport.model_validate(json.loads(report.model_dump_json()))
        assert restored.summary.pass_rate == report.summary.pass_rate

        comparison = compare(report, restored)
        assert comparison.regressions == []
        assert render_run_console(report)
        assert render_comparison_console(comparison)

    def test_summary_slices_by_tag(self, mock_provider: AsyncMock) -> None:
        from evals.report.models import ScenarioResult

        results = [
            ScenarioResult(scenario_id="a", tags=["stage:connect"], passed=True),
            ScenarioResult(scenario_id="b", tags=["stage:connect"], passed=False),
        ]
        summary = summarize(results)
        assert summary.pass_rate == 0.5
        assert summary.pass_rate_by_tag["stage:connect"] == 0.5
