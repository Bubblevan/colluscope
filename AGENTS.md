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
