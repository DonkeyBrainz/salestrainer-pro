"""CLI entrypoint for the agent eval harness.

Usage (from backend/):
    uv run python -m evals.run --suite customer --provider gemini
    uv run python -m evals.run --suite all --provider nova
    uv run python -m evals.run --suite all --judge --judge-model gemini-2.5-pro
    uv run python -m evals.run --suite coach --tags stage:connect
    uv run python -m evals.run --suite customer --compare evals/results/run-<id>.json
    uv run python -m evals.run --suite voice --provider gemini --audio-judge

Text providers (customer/coach suites): gemini (default), nova, voxtral.
Voice providers (--suite voice, drives live speech-to-speech sessions with
real audio): gemini, openai, nova. Voice runs bill audio tokens and save WAV
artifacts under evals/results/audio/; it is never included in --suite all.
"""

import argparse
import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings, get_settings
from app.llm_providers import GeminiProvider, LLMProvider
from app.llm_providers.nova import NovaProvider
from app.llm_providers.voxtral import VoxtralProvider
from evals import HARNESS_VERSION
from evals.checks.coach_checks import run_coach_checks
from evals.checks.customer_checks import run_customer_checks
from evals.checks.voice_checks import run_voice_checks
from evals.judge.audio_judge import judge_scenario_audio
from evals.judge.judge import (
    COACH_JUDGE_CONTEXT,
    CUSTOMER_JUDGE_CONTEXT,
    VOICE_JUDGE_CONTEXT,
    judge_scenario,
)
from evals.judge.rubric import COACH_DIMENSIONS, CUSTOMER_DIMENSIONS, VOICE_DIMENSIONS
from evals.report.aggregate import compare, summarize
from evals.report.models import RunReport, ScenarioResult
from evals.report.render import (
    load_json_report,
    render_comparison_console,
    render_run_console,
    write_json_report,
)
from evals.runners.coach_runner import run_coach_scenario
from evals.runners.customer_runner import run_customer_scenario
from evals.runners.voice_runner import run_voice_scenario
from evals.scenarios.types import (
    load_coach_scenarios,
    load_customer_scenarios,
    load_voice_scenarios,
)

PROVIDERS: dict[str, type] = {
    "gemini": GeminiProvider,
    "nova": NovaProvider,
    "voxtral": VoxtralProvider,
}

# Report-label default per provider (customer suite has no --model override
# path; the model actually used is resolved internally by each provider).
_DEFAULT_MODEL_LABEL: dict[str, str] = {
    "gemini": "gemini_model",
    "nova": "nova_model",
    "voxtral": "voxtral_model",
}

# Same, for the voice suite's live (speech-to-speech) providers.
_VOICE_MODEL_LABEL: dict[str, str] = {
    "gemini": "gemini_live_model",
    "openai": "openai_realtime_model",
    "nova": "nova_sonic_model",
}


def _default_model_label(provider_name: str, settings: Settings) -> str:
    """Best-effort report label for the model a provider defaults to."""
    attr = _DEFAULT_MODEL_LABEL.get(provider_name)
    return str(getattr(settings, attr)) if attr else "unknown"


RESULTS_DIR = Path(__file__).parent / "results"


def build_provider(name: str) -> LLMProvider:
    """Construct a provider from the registry."""
    if name not in PROVIDERS:
        raise SystemExit(f"Unknown provider {name!r}. Available: {sorted(PROVIDERS)}")
    provider: LLMProvider = PROVIDERS[name](get_settings())
    return provider


async def run_customer_suite(
    provider: LLMProvider,
    tags: list[str] | None,
    judge: bool,
    judge_model: str | None,
) -> list[ScenarioResult]:
    """Run all customer scenarios with checks (and judge if enabled)."""
    settings = get_settings()
    results: list[ScenarioResult] = []
    for scenario in load_customer_scenarios(tags):
        result = await run_customer_scenario(scenario, provider, settings)
        result.checks = run_customer_checks(scenario, result)
        result.passed = all(c.passed for c in result.checks) and result.error is None
        if judge and not result.error:
            result.judge = await judge_scenario(
                result,
                CUSTOMER_DIMENSIONS,
                provider,
                judge_model or settings.coach_model,
                CUSTOMER_JUDGE_CONTEXT,
            )
        results.append(result)
        print(f"  {'PASS' if result.passed else 'FAIL'}  {scenario.id}")
    return results


async def run_coach_suite(
    provider: LLMProvider,
    tags: list[str] | None,
    judge: bool,
    judge_model: str | None,
    model: str | None,
) -> list[ScenarioResult]:
    """Run all coach scenarios with checks (and judge if enabled)."""
    settings = get_settings()
    results: list[ScenarioResult] = []
    for scenario in load_coach_scenarios(tags):
        result = await run_coach_scenario(scenario, provider, model)
        result.checks = run_coach_checks(scenario, result)
        result.passed = all(c.passed for c in result.checks) and result.error is None
        if judge and not result.error:
            result.judge = await judge_scenario(
                result,
                COACH_DIMENSIONS,
                provider,
                judge_model or settings.coach_model,
                COACH_JUDGE_CONTEXT,
            )
        results.append(result)
        print(f"  {'PASS' if result.passed else 'FAIL'}  {scenario.id}")
    return results


async def run_voice_suite(
    provider_name: str,
    tags: list[str] | None,
    judge: bool,
    judge_model: str | None,
    audio_judge: bool,
    run_id: str,
) -> list[ScenarioResult]:
    """Run all voice scenarios against a live speech-to-speech provider.

    Real audio in, real audio out: each scripted turn is TTS-synthesized and
    streamed to the model; checks score ASR comprehension (WER), reply text,
    latency, and audibility. The transcript judge (and optional audio judge)
    always run on Gemini, independent of the provider under test.
    """
    from app.agents.personas import get_persona
    from app.llm_providers.registry import LIVE_PROVIDERS, build_live_provider

    if provider_name not in LIVE_PROVIDERS:
        raise SystemExit(
            f"Unknown voice provider {provider_name!r}. Available: {sorted(LIVE_PROVIDERS)}"
        )

    settings = get_settings()
    live_provider = build_live_provider(provider_name, settings)
    judge_provider = GeminiProvider(settings)

    results: list[ScenarioResult] = []
    for scenario in load_voice_scenarios(tags):
        result = await run_voice_scenario(scenario, live_provider, settings, run_id=run_id)
        result.checks = run_voice_checks(scenario, result)
        result.passed = all(c.passed for c in result.checks) and result.error is None
        if judge and not result.error:
            result.judge = await judge_scenario(
                result,
                VOICE_DIMENSIONS,
                judge_provider,
                judge_model or settings.coach_model,
                VOICE_JUDGE_CONTEXT,
            )
        if audio_judge and not result.error:
            persona = get_persona(scenario.persona_id)
            if persona is not None:
                audio_scores = await judge_scenario_audio(result, persona, settings)
                if audio_scores:
                    result.judge = (result.judge or []) + audio_scores
        results.append(result)
        print(f"  {'PASS' if result.passed else 'FAIL'}  {scenario.id}")
    return results


async def main_async(args: argparse.Namespace) -> int:
    """Run the requested suites and emit reports."""
    settings = get_settings()
    if not settings.gemini_api_key:
        print("GEMINI_API_KEY is not set (backend/.env). Aborting.", file=sys.stderr)
        return 2

    run_id = f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"

    if args.suite == "voice":
        voice_attr = _VOICE_MODEL_LABEL.get(args.provider)
        model = args.model or (str(getattr(settings, voice_attr)) if voice_attr else "unknown")
    else:
        model = args.model or _default_model_label(args.provider, settings)

    results: list[ScenarioResult] = []
    if args.suite in ("customer", "all"):
        provider = build_provider(args.provider)
        print(f"Running customer suite ({args.provider}/{model})...")
        results += await run_customer_suite(provider, args.tags, args.judge, args.judge_model)
    if args.suite in ("coach", "all"):
        provider = build_provider(args.provider)
        coach_model = args.model or settings.coach_model
        print(f"Running coach suite ({args.provider}/{coach_model})...")
        results += await run_coach_suite(
            provider, args.tags, args.judge, args.judge_model, args.model
        )
    if args.suite == "voice":
        print(f"Running voice suite ({args.provider}/{model}) — live audio sessions...")
        results += await run_voice_suite(
            args.provider, args.tags, args.judge, args.judge_model, args.audio_judge, run_id
        )

    if not results:
        print("No scenarios matched.", file=sys.stderr)
        return 1

    report = RunReport(
        harness_version=HARNESS_VERSION,
        run_id=run_id,
        provider_name=args.provider,
        model=model,
        suite=args.suite,
        judge_model=(args.judge_model or settings.coach_model) if args.judge else None,
        scenario_results=results,
        summary=summarize(results),
    )

    out_path = Path(args.out) if args.out else RESULTS_DIR / f"run-{run_id}.json"
    write_json_report(report, out_path)

    print()
    print(render_run_console(report))
    print(f"\nJSON report: {out_path}")

    if args.compare:
        baseline = load_json_report(Path(args.compare))
        comparison = compare(baseline, report)
        print()
        print(render_comparison_console(comparison))
        if comparison.regressions:
            return 1

    return 0 if report.summary.pass_rate == 1.0 else 1


def main() -> None:
    """Parse CLI args and run the harness."""
    parser = argparse.ArgumentParser(
        prog="evals.run", description="SalesTrainer Pro agent eval harness"
    )
    parser.add_argument(
        "--suite",
        choices=["customer", "coach", "voice", "all"],
        default="all",
        help="Which suite to run ('all' = customer+coach; voice runs only when explicit)",
    )
    parser.add_argument(
        "--provider",
        default="gemini",
        help=f"Model provider (text suites: {sorted(PROVIDERS)}; voice: gemini/openai/nova)",
    )
    parser.add_argument("--model", default=None, help="Override the model under test")
    parser.add_argument(
        "--tags",
        nargs="*",
        default=None,
        help="Only scenarios with ALL of these tags (e.g. stage:observe)",
    )
    parser.add_argument(
        "--judge", action="store_true", help="Also run LLM-judge rubric scoring (costs LLM calls)"
    )
    parser.add_argument(
        "--judge-model", default=None, help="Judge model (default: settings.coach_model)"
    )
    parser.add_argument(
        "--audio-judge",
        action="store_true",
        help="Voice suite only: also score the saved output audio with a "
        "multimodal judge (vocal naturalness, tone, clarity, pacing)",
    )
    parser.add_argument("--out", default=None, help="JSON report output path")
    parser.add_argument(
        "--compare", default=None, help="Path to a prior JSON report to diff against"
    )
    args = parser.parse_args()

    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
