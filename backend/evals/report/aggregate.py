"""Aggregation and comparison of eval-harness run reports."""

from collections import defaultdict

from evals.report.models import (
    ComparisonReport,
    RunReport,
    RunSummary,
    ScenarioDiff,
    ScenarioResult,
)


def summarize(results: list[ScenarioResult]) -> RunSummary:
    """Compute aggregate stats for a set of scenario results."""
    if not results:
        return RunSummary()

    passed = [r for r in results if r.passed]
    latencies = [r.total_latency_ms for r in results if r.total_latency_ms > 0]

    total_usage: dict[str, int] = defaultdict(int)
    for r in results:
        for key, value in r.usage.items():
            total_usage[key] += value

    # Pass rate sliced by tag
    by_tag: dict[str, list[bool]] = defaultdict(list)
    for r in results:
        for tag in r.tags:
            by_tag[tag].append(r.passed)
    pass_rate_by_tag = {
        tag: round(sum(vals) / len(vals), 3) for tag, vals in sorted(by_tag.items())
    }

    # Judge averages across scenarios that have judge scores
    dim_scores: dict[str, list[int]] = defaultdict(list)
    for r in results:
        for score in r.judge or []:
            dim_scores[score.dimension].append(score.score)
    judge_avg = {
        dim: round(sum(scores) / len(scores), 2) for dim, scores in sorted(dim_scores.items())
    }

    return RunSummary(
        scenario_count=len(results),
        passed_count=len(passed),
        pass_rate=round(len(passed) / len(results), 3),
        avg_latency_ms=round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
        total_usage=dict(total_usage),
        pass_rate_by_tag=pass_rate_by_tag,
        judge_avg_by_dimension=judge_avg,
    )


def compare(baseline: RunReport, current: RunReport) -> ComparisonReport:
    """Diff two runs scenario-by-scenario, flagging regressions."""
    base_by_id = {r.scenario_id: r for r in baseline.scenario_results}
    curr_by_id = {r.scenario_id: r for r in current.scenario_results}

    diffs: list[ScenarioDiff] = []
    regressions: list[str] = []
    improvements: list[str] = []

    for scenario_id in sorted(set(base_by_id) | set(curr_by_id)):
        base = base_by_id.get(scenario_id)
        curr = curr_by_id.get(scenario_id)

        base_checks = {c.name: c.passed for c in base.checks} if base else {}
        curr_checks = {c.name: c.passed for c in curr.checks} if curr else {}
        regressed = [n for n, p in base_checks.items() if p and curr_checks.get(n) is False]
        fixed = [n for n, p in base_checks.items() if not p and curr_checks.get(n) is True]

        diffs.append(
            ScenarioDiff(
                scenario_id=scenario_id,
                baseline_passed=base.passed if base else None,
                current_passed=curr.passed if curr else None,
                regressed_checks=regressed,
                fixed_checks=fixed,
            )
        )
        if base and curr:
            if base.passed and not curr.passed:
                regressions.append(scenario_id)
            elif not base.passed and curr.passed:
                improvements.append(scenario_id)

    return ComparisonReport(
        baseline_run_id=baseline.run_id,
        current_run_id=current.run_id,
        baseline_model=baseline.model,
        current_model=current.model,
        baseline_pass_rate=baseline.summary.pass_rate,
        current_pass_rate=current.summary.pass_rate,
        regressions=regressions,
        improvements=improvements,
        diffs=diffs,
    )
