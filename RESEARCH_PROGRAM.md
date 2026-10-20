# ColluScope Autoresearch Program

## Mission and maturity

Produce a compact, falsifiable, independently replayable result about what
authorized evidence can and cannot establish in multi-agent collusion audits.
Optimize credible reduction in scientific uncertainty per engineering hour,
model call, and deadline risk. A negative result or a well-supported abstention
boundary is a valid outcome.

The current harness is a **Goal-driven research coordinator**, with a hash-
checked registry, claim-level memory, candidate hypotheses, and authorization
accounting. Codex `/goal` supplies the reasoning and continuation. The CLI does
not launch experiments, execute registered commands, call models, or run in the
background. Do not call this a self-dispatching runner or a complete AI
Scientist system.

This program does not supersede the repository research charter, phase
protocols, frozen artifacts, or explicit user authorization.

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

The historical 628-request DeepSeek-first run and the separate 856-row Monitor
run are distinct evidence records. The first has 126 assessable matched B4/B5
pairs; the second has no common completed-and-assessable pair. Their rows,
budgets, and conclusions must never be pooled. The hash-checked 628-request
closeout is in `research/handoffs/DEEPSEEK-FIRST-RESEARCH-01.json`; its approval
is consumed and is not reusable.

## Scientific memory and exploration

`research/memory.json` records what current evidence supports, refutes, or
leaves unresolved, why, and the exact artifacts that support that scope.
`research/hypotheses.json` holds at most three competing candidate directions.
Candidates are not registered experiments and do not grant permission.

Up to three directions may be compared through read-only evidence review,
literature work, and deterministic analysis planning. Only one formal experiment
may be open in this checkout. Candidates cannot concurrently edit shared code
or frozen data. Separate worktree execution, a central budget lock, and a
reviewable multi-branch merge process are not implemented; do not imply that
parallel experiment branches exist.

## Outcome model

Each cycle records two separate judgments:

- **Scientific outcome:** `SUPPORTED`, `REFUTED`, `INCONCLUSIVE`,
  `INVALID_EXPERIMENT`, `EXECUTION_BLOCKED`, or `RESOURCE_BLOCKED`.
- **Operational review disposition:** `PASS`, `FAIL`, `AMBIGUOUS`, `BLOCKED`, or
  `PIVOT`.

A phase gate or operational PASS is not a scientific result. `REFUTED` and
`INCONCLUSIVE` trigger diagnosis, competing explanations, and another permitted
cycle; they do not complete the program Goal. `INVALID_EXPERIMENT` triggers
root-cause analysis or a redesigned evaluator. A blocked live action pauses
that action only; the Goal should continue useful offline work if one remains.

Research memory records the old belief, the change, remaining alternatives,
and hash-pinned evidence. A progress counter is credited only when the closure
contains an evidence-backed material update and an independent review artifact.
This is a structured provenance rule, not an automatic scientific truth test.
After three consecutive cycles without such a reviewed update, pivot the
question or state the concrete boundary that prevents further useful work.

## Iteration loop

Codex `/goal` is the continuation driver. At the start of every turn and after
each terminal cycle:

1. **OBSERVE** — read the persistent research goal, active phase protocol,
   risk register, iteration log, state, memory, candidate hypotheses, current
   authorization, relevant evidence, and Git diff.
2. **EXPLAIN** — distinguish observations from interpretations. Identify the
   strongest unexplained result and at least two competing mechanisms.
3. **DISCOVER** — consult relevant primary literature when novelty or a current
   citation claim matters. Record which source supports each novelty claim.
4. **SELECT** — compare at most three candidates by claim importance, novelty,
   identifiability, information value, cost, failure risk, and deadline. Choose
   one primary question; prefer an existing-data analysis if it can decide the
   issue.
5. **PREREGISTER** — use schema version 2 with hash-pinned inputs, sample
   selection, intervention, controls, outcome, denominator, success/failure/
   ambiguous gates, analysis plan, competing explanations, and resources.
   Registration does not authorize execution.
6. **IMPLEMENT** — make the smallest reversible change. Separate protocol,
   infrastructure, and analysis provenance. Never modify frozen inputs to
   improve a result.
7. **RUN** — use only a permitted existing entry point, within a currently
   valid approval batch when required. Preserve all attempts, failures, and
   assigned denominators. The CLI has no dispatch command.
8. **INTERPRET** — assign the typed scientific outcome. Recompute from original
   bytes or deterministic data where possible; update memory from actual
   observations, not a desired score.
9. **CRITIQUE** — ask the `scientific-critic` skill for a separate review before
   claiming material uncertainty reduction or finalizing a central claim. If
   reviewer access/context is not independent, record adversarial self-review.
10. **DECIDE / REPORT** — continue, diagnose, test a rival, pivot, or synthesize.
    Update the closure, claim memory, state, risk register, and iteration log.
    End each turn with exactly one next action.

Call `python scripts/researchctl.py next` to see the registry's continuation
step. It prints guidance only; it does not execute that step. The copy-ready
Goal instructions are in `CODEX_AUTORESEARCH_GOAL.md`.

## Authorization and resource accounting

- The latest approval `DS-FLASH-1200-2P50-20261020` is time-valid through
  `2026-10-21T01:00:00Z` but names only the now-closed
  `b5-evidence-view-stability-120` diagnostic. That registered cycle's cap was
  120 calls / $0.25, and all 120 call slots were consumed. Its unused
  project-wide balance does not authorize a different experiment. There is no
  callable scope for another cycle; historical approvals are never reused.
- A future explicit approval must name the scope, experiment IDs, total calls,
  total cost, and expiry. Preserve one immutable record per approval ID under
  `research/authorizations/`; a preregistration pins its SHA-256.
- Keep per-approval cumulative limits separate from project-wide lifetime
  limits. A new approval batch does not inherit usage from an earlier batch,
  while all new batches still count against the project limit.
- Registration reserves the full cycle ceiling against both limits. Every
  physical attempt, including a failed attempt or retry allowed by protocol,
  must appear in the sanitized request ledger. The evaluator checks each
  attempt timestamp against approval expiry and sums the costs.
- The current harness has no request dispatcher. The request-ledger check is a
  post-run audit; it cannot enforce an API call before transport. A future
  runner must repeat approval, expiry, budget-reservation, and identity checks
  immediately before each request, with a shared atomic ledger, before it can
  claim pre-dispatch enforcement.
- No file, CLI flag, registered protocol, prior approval, or successful
  preflight creates permission. A new user approval must name the exact scope
  and ceiling before a live model/API run or new expensive phase.
- `protocol.reproduction_command` is inert record text. Never pass it to a
  shell from this harness. Arbitrary generated shell is not an approved runner.
- If authorization, budget, privacy, security, data integrity, or deadline
  blocks a live action, pause only that action and continue independent
  no-call work when it can reduce uncertainty.

## Claim and completion rules

Prioritize work that can change a defensible research claim at low cost. Before
any cycle, answer: Which claim could change? What is the strongest alternative?
What observation falsifies the hypothesis? What is the smallest decisive
offline or authorized test? How are failures and denominators retained?

Do not finish the Goal only because an experiment ran, an evaluator passed, a
TRD reached GO/NO-GO, a hypothesis failed, or a paper draft exists. The Goal is
complete only when the strongest direction has been selected from evidence;
the main claim or strongest achievable negative/identifiability result is
appropriately tested; meaningful baselines and controls are assessed; a
separate critic has reviewed the central claim; results and limits reproduce
from the available artifacts; and the submission report and reproduction
package are ready. Never manufacture a positive result to meet that criterion.

Pause only for an actual hard boundary or when no useful permitted action
remains. Do not issue meaningless tool calls to keep the Goal alive.
