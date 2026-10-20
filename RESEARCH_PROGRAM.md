# ColluScope Autoresearch Program

## Mission

Produce a compact, falsifiable, independently replayable result about what
authorized evidence can and cannot establish in multi-agent collusion audits.
Optimize credible reduction in scientific uncertainty per engineering hour,
model call, and deadline risk. A negative result or a well-supported abstention
boundary is a valid outcome.

This program guides Codex's research decisions. It does not supersede the
repository research charter, phase protocols, frozen artifacts, or explicit
user authorization. The local harness records and audits work; it never runs
an experiment or creates an authorization.

## Evidence ladder

Keep these evidence classes separate in every registry entry and report:

1. `scripted_mock`: scripted mechanisms and deterministic fixtures.
2. `live_engineering_preflight`: runtime, transport, parser, or identity
   compatibility; not agent behavior.
3. `real_llm_behavior`: actions/messages from authorized real-agent episodes.
4. `monitor_evaluation`: authorized monitor outputs against defensible
   observable references.
5. `offline_reanalysis`: deterministic replay or synthesis of existing data.

Do not promote a result between classes. Treatment, shared incentives, harm,
agreement, channel availability, monitor scores, or citation membership do not
identify latent collusion or intent.

## Iteration loop

Every cycle follows:

1. **INSPECT** — read the persistent goal, active phase protocol, risk register,
   iteration log, current state, relevant raw/sanitized evidence, and Git diff.
2. **HYPOTHESIZE** — state one primary claim and at least one competing
   explanation. Identify what evidence would change the direction of the work.
3. **PREREGISTER** — create an immutable record with frozen input hashes,
   sample selection, intervention, controls, primary outcome, denominator,
   success/failure/ambiguous gates, analysis, and resource budget.
4. **IMPLEMENT** — make the smallest reversible change. Separate protocol,
   infrastructure, and analysis provenance.
5. **RUN** — use only a permitted existing entry point and only within a
   separate, current user authorization. Retain all assigned rows, failures,
   attempts, and adverse outcomes. No harness command launches a run.
6. **ADVERSARIAL REVIEW** — independently replay where possible; attack labels,
   leakage, confounding, missingness, sample dependence, and claim scope.
7. **DECIDE** — record `PASS`, `FAIL`, `AMBIGUOUS`, `BLOCKED`, or `PIVOT` with
   a reason. A software gate is not a scientific pass.
8. **REPORT** — append the evidence and exactly one highest-value next action
   to the research log and state projection.

Use one primary experiment per cycle. Harness v1 allows only one open
preregistration; encode competing mechanisms as arms of one discriminating
protocol where possible. Do not run parallel live branches by default. After three consecutive
cycles without reducing a new scientific uncertainty, stop micro-tuning and
reconsider the question against failures and prior work; preserve that pivot
in the log.

## Authorization and stop rules

- The current harness budget is zero new model/API calls and zero external
  spend. Historical approvals are consumed and are not reusable.
- No file, CLI flag, registered protocol, previous approval, or successful
  preflight is authorization. A new user approval must name the scope and
  ceiling before any live model/API run.
- Registration is not dispatch. The CLI has no `run` or arbitrary shell
  execution command.
- If a phase protocol is complete, stop at its gate. Select the next question
  from the actual evidence; do not automatically start the next phase.
- Preserve frozen datasets, prompts, labels, failures, raw traces, and exact
  hashes. Keep private run material under existing ignored and ACL-restricted
  paths; publish only reviewed sanitized outputs.
- Stop on identity, privacy, source-hash, budget, transport-integrity, or
  authorization failure. Do not retry or replace rows unless the approved
  protocol explicitly permits it.

## Claim and resource scorecard

Prioritize work that can change a defensible paper claim at low cost. Before a
cycle, answer: Which claim could change? What is the strongest alternative?
What observation falsifies the hypothesis? What is the smallest decisive
offline or authorized test? How are failures and denominators retained?
If no answer is concrete, do literature/evidence synthesis or stop; do not
invent an experiment to keep the loop busy.

The registry's outcome fields are not a universal scientific metric. Report
raw denominators, uncertainty, population and evidence class. Do not optimize a
single development score or infer a population effect from a small fixed sample.

## Handoff

At the start of a resumed Codex goal, check whether another task owns an
unfinished experiment. Do not interrupt it or import provisional outputs.
After its terminal decision, import only its sanitized closure packet and
independent audit references with `python scripts/researchctl.py
import-closeout <packet.json>`, verify the hashes, then select the next cycle.
This is a historical handoff import, not a retroactive preregistration or
authorization.
If the experiment owner is not visible in this checkout, record that fact and
wait for its final artifact rather than guessing its result.

The copy-ready `/goal` prompt is in `CODEX_AUTORESEARCH_GOAL.md`. Use the
`scientific-discovery` skill for question selection and the `experiment-audit`
skill for registration, replay, and claim review.
