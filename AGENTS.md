# Repository instructions

## ColluScope research charter (persistent)

Before changing research code or running any experiment, read
`COLLUSCOPE_PERSISTENT_RESEARCH_GOAL.md`, the active phase TRD,
`docs/RESEARCH_RISK_REGISTER.md`, and `docs/ITERATION_LOG.md`.

North Star: credible, falsifiable multi-agent collusion-audit evidence per
engineering hour and model call; prioritize an independently reproducible
research result and the Apart sprint submission over platform features.

Treat scripted/Mock, live engineering preflight, real LLM behavior, and
monitor evaluation as distinct evidence levels. Never promote one to another.

Do not change frozen datasets/prompts, infer collusion from treatment/harm,
remove failures, or call live models/start new expensive phases without
separate explicit user approval. Keep exact hashes and adverse evidence.

Iterate: INSPECT → HYPOTHESIZE → PREREGISTER → IMPLEMENT → RUN →
ADVERSARIAL REVIEW → DECIDE → REPORT. Log results and propose exactly the
single highest-value next uncertainty-reducing experiment.

## Autoresearch harness

For ongoing research iterations, read `RESEARCH_PROGRAM.md` and the relevant
skills under `.agents/skills/` before acting. Start from `research/state.json`,
`research/memory.json`, `research/hypotheses.json`, and `research/budget.json`.
Use `python scripts/researchctl.py next` for the next lifecycle step and
`register`, `close`, `audit`, and `sync-memory` for the corresponding record
operations.

Treat scientific outcomes (`SUPPORTED`, `REFUTED`, `INCONCLUSIVE`,
`INVALID_EXPERIMENT`, `EXECUTION_BLOCKED`, `RESOURCE_BLOCKED`) separately from
operational gate decisions. An ordinary `GO/NO-GO` or a failed hypothesis does
not by itself complete the research Goal. After each cycle, interpret the
result, update evidence-backed memory, and continue with one next action if
permitted work remains.

The harness is a Goal-driven coordinator and record gate; it does not authorize
or dispatch experiments. The `reproduction_command` field is inert text. Keep
per-approval budgets separate from the project-wide limit, and never reuse a
historical approval. Up to three hypotheses may be compared through read-only
work; keep only one formal experiment open in the shared checkout.

`research/frozen_eval/` is versioned evaluation policy. Version 1 stays
unchanged; changes use a new evaluator version, a hash pin, and an explicit
audit trail. Never edit an evaluator to make a result pass.
