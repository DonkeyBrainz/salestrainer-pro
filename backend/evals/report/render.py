"""Console and JSON rendering for eval-harness reports."""

import json
from pathlib import Path

from evals.report.models import ComparisonReport, RunReport


def render_run_console(report: RunReport) -> str:
    """Render a run report as a plain console table."""
    lines: list[str] = []
    lines.append(
        f"Run {report.run_id} | suite={report.suite} | provider={report.provider_name} "
        f"| model={report.model}" + (f" | judge={report.judge_model}" if report.judge_model else "")
    )
    lines.append("-" * 78)

    for result in report.scenario_results:
        status = "PASS" if result.passed else "FAIL"
        judge_note = ""
        if result.judge:
            avg = sum(s.score for s in result.judge) / len(result.judge)
            judge_note = f"  judge={avg:.1f}/5"
        lines.append(
            f"{status:4}  {result.scenario_id:40}  {result.total_latency_ms:7.0f}ms{judge_note}"
        )
        for check in result.checks:
            if not check.passed:
                lines.append(f"      ✗ {check.name}: {check.reason}")
        if result.error:
            lines.append(f"      ! error: {result.error}")

    s = report.summary
    lines.append("-" * 78)
    lines.append(
        f"{s.passed_count}/{s.scenario_count} passed ({s.pass_rate:.0%}) | "
        f"avg latency {s.avg_latency_ms:.0f}ms | tokens {s.total_usage or '{}'}"
    )
    if s.judge_avg_by_dimension:
        dims = ", ".join(f"{d}={v}" for d, v in s.judge_avg_by_dimension.items())
        lines.append(f"judge averages: {dims}")
    if s.pass_rate_by_tag:
        tags = ", ".join(f"{t}={v:.0%}" for t, v in s.pass_rate_by_tag.items())
        lines.append(f"pass rate by tag: {tags}")
    return "\n".join(lines)


def render_comparison_console(comparison: ComparisonReport) -> str:
    """Render a comparison report as a plain console diff."""
    lines: list[str] = []
    lines.append(
        f"Comparing {comparison.baseline_run_id} ({comparison.baseline_model}) -> "
        f"{comparison.current_run_id} ({comparison.current_model})"
    )
    lines.append(
        f"pass rate: {comparison.baseline_pass_rate:.0%} -> {comparison.current_pass_rate:.0%}"
    )
    lines.append("-" * 78)
    if comparison.regressions:
        lines.append(f"REGRESSIONS ({len(comparison.regressions)}):")
        for sid in comparison.regressions:
            lines.append(f"  ✗ {sid}")
    if comparison.improvements:
        lines.append(f"improvements ({len(comparison.improvements)}):")
        for sid in comparison.improvements:
            lines.append(f"  ✓ {sid}")
    for diff in comparison.diffs:
        if diff.regressed_checks:
            lines.append(f"  {diff.scenario_id}: regressed checks: {diff.regressed_checks}")
    if not comparison.regressions and not comparison.improvements:
        lines.append("no pass/fail changes")
    return "\n".join(lines)


def write_json_report(report: RunReport, out_path: Path) -> None:
    """Write the run report as JSON for archiving and later comparison."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.model_dump_json(indent=2))


def load_json_report(path: Path) -> RunReport:
    """Load a previously saved run report."""
    return RunReport.model_validate(json.loads(path.read_text()))
