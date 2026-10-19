# Codex persistent setup — use alongside the TRD

Do **not** blindly replace an existing root `AGENTS.md`; first read and merge any local obligations. Put `COLLUSCOPE_PERSISTENT_RESEARCH_GOAL.md` at repository root and the phase TRD at `docs/M1_P0_INTERFACE_TRD.md`. Add the following small clause to `AGENTS.md` so later Codex sessions find the long-lived goal:

```markdown
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
```

## One-time Codex kickoff message

> Read the persistent research charter and the new M1-P0 Next Gate TRD. Audit the current remote HEAD `657eab90356ce9137c2988aacb4b5b10d0402c28` first. The model emitted a protocol-valid `no_message` on a compatibility probe explicitly asking for `send_message`; separate schema validity from instruction compliance while retaining that adverse result. Produce a versioned new protocol, tight offline counterexample tests, and a decision memo. Do not make live calls or use old consumed approvals. Your objective is to advance a scientifically credible Track 2.2/2.3 result within the sprint deadline, not to make every gate green. Stop for approval before any new real-model preflight or 25-episode run.

## Milestone handoff contract

Each Codex iteration report should end with:

- `STATE`: branch, commit, clean/dirty, protocol ID, what was *actually* run.
- `EVIDENCE`: raw logs, hashes, new/old failed cases, scope and caveats.
- `RESEARCH_IMPLICATION`: what hypothesis becomes more/less plausible.
- `DECISION`: GO / NO-GO / AMBIGUOUS / BLOCKED / PIVOT, with a measurable gate.
- `NEXT ACTION`: one highest-value step, exact budget, and whether user approval is needed.

No progress claim should depend on a file link that has not actually been generated and verified in that checkout.
