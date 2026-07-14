"""Agent evaluation harness for SalesTrainer Pro.

Evaluates customer-agent and coach-agent behavior against synthetic scripted
scenarios, with deterministic rule-based checks (hard pass/fail gate) and an
optional LLM-judge rubric layer (soft quality signal). Providers are pluggable
via app.llm_providers.LLMProvider.

Not part of the pytest/coverage suite — run via ``python -m evals.run``.
"""

HARNESS_VERSION = "1.0"
