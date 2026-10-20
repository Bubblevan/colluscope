# ColluScope — Autonomous Scientific Discovery Goal

Paste this as a persistent Codex `/goal`. This file defines research direction;
it does not start a goal, register an experiment, or grant authorization.

---

Continuously advance ColluScope toward a defensible, falsifiable, reproducible
scientific contribution about what evidence can and cannot establish in
multi-agent collusion audits. Follow `RESEARCH_PROGRAM.md`, the repository
research charter, the active phase TRD, `docs/RESEARCH_RISK_REGISTER.md`, and
`docs/ITERATION_LOG.md`.

## Do not stop at an ordinary experiment result

An experiment reaching terminal state, a passing test suite, a protocol gate,
an operational PASS/NO-GO, a refuted hypothesis, or a draft paper does not by
itself complete this Goal. After every cycle, interpret the result, update
claim-level research memory, ask what competing explanation remains, and choose
one useful next action. Continue permitted no-call analysis when a live action
is blocked. Stop the Goal only after the completion criteria below are met, a
real hard boundary prevents all useful work, or the deadline makes further work
counterproductive; explain which condition applies.

Use these scientific outcomes: `SUPPORTED`, `REFUTED`, `INCONCLUSIVE`,
`INVALID_EXPERIMENT`, `EXECUTION_BLOCKED`, and `RESOURCE_BLOCKED`. Keep the
operational review disposition separate. A failed or inconclusive hypothesis
triggers diagnosis, a competing hypothesis, or a pivot. An invalid experiment
triggers root-cause investigation or a redesigned evaluation. A blocked live
action pauses that action only.

## Reconcile actual history first

The terminal, hash-checked closeout for `DEEPSEEK-FIRST-RESEARCH-01` is already
in `research/handoffs/DEEPSEEK-FIRST-RESEARCH-01.json`. It records 628 historical
requests, 24 Agent groups, 376 Monitor rows, independent replay, and a consumed
one-run authorization. Do not wait for this run, reimport it as a new
preregistration, rerun inference, or reuse its approval.

The separate `FULL-RESEARCH-EXECUTION-20261020` result is at
`docs/results/full-research-execution-20261020/full_research_results_summary.json`.
It covers a different 856-row Monitor schedule and a local M4 run. Keep the two
run records, denominators, failures, and claims separate. Do not accept the
attachment's “20/24 prediction changes” example as evidence unless a
hash-pinned local source supports that exact denominator and claim.

Read `research/state.json`, `research/memory.json`, `research/hypotheses.json`,
`research/budget.json`, both evaluator versions, and
`scripts/researchctl.py` before selecting the next cycle.

## Run a real reasoning loop

For each turn:

1. Inspect the relevant frozen protocol, sanitized evidence, adverse results,
   claim memory, risk register, and Git diff.
2. Separate direct observations from interpretation. Generate at least two
   plausible rival mechanisms grounded in the cited evidence.
3. Consult primary literature when novelty or a current citation claim matters.
   Map each novelty claim to its source.
4. Compare no more than three candidate directions by scientific importance,
   identifiability, information gain, cost, failure risk, and deadline. Choose
   one primary question; prefer an existing-data analysis if it can decide it.
5. Preregister the frozen inputs, denominator, primary outcome, rivals,
   controls, analysis, budget, and explicit stop gates before changing a
   scientific protocol or running a new experiment.
6. Use only a permitted existing experiment entry point. Preserve all assigned
   rows and failures. Recompute results independently where possible.
7. Update memory with the previous belief, what changed, what remains
   plausible, and hash-pinned evidence. Do not mark progress from a self-asserted
   boolean. Independent review must have its own sanitized, hash-pinned artifact.
8. Ask the `scientific-critic` skill to challenge novelty, causal attribution,
   label validity, dependence/missingness, baseline fairness, and the remaining
   contribution. If the reviewer cannot be separated from the author, mark it
   as adversarial self-review.
9. Choose exactly one next action: continue the hypothesis, test a rival,
   diagnose an invalid run, pivot, continue offline, await an exact boundary,
   or synthesize the final report.

Use `/goal` as the continuation driver. `python scripts/researchctl.py next`
prints the next registry step. It is guidance only. This harness is a
Goal-driven coordinator, not a background daemon or experiment runner. The
CLI never executes `protocol.reproduction_command`, generated shell, or model
requests. No subagent review is a formal benchmark Monitor result.

## Experiment selection and resources

Prefer one small experiment that separates rival explanations over repeated
larger batches that only add rows. Before spending calls, record which claim
could change, what existing evidence already answers, the minimum calls and
wall time, and the likely confounders.

The current authorization is zero new model/API calls and zero external spend.
No past approval carries forward. A new user approval must name experiment IDs,
scope, total call and cost ceilings, and expiry. Keep one immutable record per
approval ID, separate its cumulative usage from other approvals, and preserve a
separate project-wide limit. The preregistration reserves its full ceiling;
each physical attempt must be accounted in a sanitized request ledger.

The present harness audits those timestamps and totals after a cycle. It cannot
enforce a request before transport because there is no dispatcher. A future
runner must implement an atomic pre-request reservation and repeat authorization,
expiry, identity, and budget checks before it can dispatch. Do not describe
post-run checks as pre-dispatch enforcement.

Offline review, deterministic replay, code inspection, writing, and literature
work may continue when they stay inside the repository rules and do not alter
frozen inputs. Never change frozen data, prompts, labels, or scoring rules;
never delete failures; never infer collusion or intent from treatment, harm,
agreement, or monitor scores alone.

Up to three hypotheses may be compared using read-only analysis. Only one
formal experiment is open at a time. Separate worktree execution, branch-level
ledgers, and shared atomic paid-call scheduling are not implemented.

## Completion criteria

Complete this Goal only when the strongest direction has been selected from
evidence; its central claim or the strongest achievable negative/
identifiability result has been appropriately tested; relevant baselines and
negative controls are assessed; an independent Scientific Critic has reviewed
the central claim; evidence, uncertainty, failures, and limitations reproduce
from available artifacts; and a coherent submission report and reproduction
package are ready. If no positive discovery is supported, report the strongest
honest negative result or boundary. Do not manufacture a breakthrough.

Scientific uncertainty alone is not a reason to stop. A hard authorization,
budget, privacy, data-integrity, security, deadline, or unrecoverable runtime
boundary can stop the affected execution. Continue other permitted work when it
still reduces uncertainty.
