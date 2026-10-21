# Autoresearch continuation — selected M1 v3 package review (2026-10-21)

## INSPECT

Read `AGENTS.md`, `COLLUSCOPE_PERSISTENT_RESEARCH_GOAL.md`, `CODEX_AUTORESEARCH_GOAL.md`, `RESEARCH_PROGRAM.md`, the M1 v3 protocol/runtime TRD/evidence/decision, the root risk register and iteration log, `research/state.json`, `research/memory.json`, `research/hypotheses.json`, `research/budget.json`, and both frozen evaluator versions. No separate research-charter file exists; the charter is in `AGENTS.md` and the persistent research goal.

The root autoresearch Goal and Program contain an old authorization snapshot. They are hash-pinned by the closed B5 manifest and were not edited. Their current authorization status is corrected in `docs/AUTORESEARCH_CURRENT_STATE_ADDENDUM_20261021.md`.

## EXPLAIN / COMPETING MECHANISMS

The post-hoc M1-100 analysis reports a target-execution difference-in-differences of +1 in 9/15 matched groups, zero in 6/15 and no negative groups; the private-reward-plus-chat cell executed the target in 9/15 groups and each other cell in 0/15. Regret interaction averaged +9. This is exploratory, based on 15 groups and three earlier payoff families. It does not establish a population effect, semantic-message effect, collusion or intent.

Two strong alternatives remain: (1) agents independently select a commonly known, privately rewarded target; and (2) the extra chat-stage prompt or target salience, rather than message meaning, shifts behavior. Payoff-family dependence and checkpoint-specific behavior are further alternatives. The three earlier family rates for the combined cell were 1/5, 5/5 and 3/5, motivating the output-independent 24-matrix extension and its 6/12/18 target-regret strata.

The chosen test is the already frozen M1 v3 finite-package contrast, not a new B5 synthetic-format sweep or an immediate Monitor campaign. Its four-cell target-execution interaction and common-incentive control test the assigned package; they do not separate message semantics from stage and shared-target effects. Monitor Cycle 2 remains a separate future question and its deficiencies do not block Cycle 1.

## PREREGISTER / IMPLEMENT / RUN

- The candidate remains `m1-reward-chat-24group-replication-v1`, schema-v2 registration pending. No registration was created because the validator requires an exact approval ID and no M1-specific approval exists.
- The review snapshot manifest enumerates the runtime's exact 23 frozen input paths and supporting protocol/runtime evidence. It is explicitly marked as a review snapshot, not a preregistration or authorization.
- A separate no-call verification matched all 23 runtime input hashes and 11 supporting review-artifact hashes; receipt: `docs/results/research-sprint-20261021/m1-package-replication-offline-refresh/m1v3-review-manifest-verification-20261021.json`.
- Re-ran `python scripts/run_m1_package_replication_v3.py --check-only`; result `PASS_OFFLINE_CANDIDATE`: 120 assigned episodes, 360 ballots, 96 message decisions, 456 maximum generations, 24 identity checks, 480 physical HTTP attempts, external calls/cost zero, and all four offline source gates passed. Saved output at `docs/results/research-sprint-20261021/m1-package-replication-offline-refresh/m1v3-check-only-current-20261021.json`.
- The no-call checks do not verify the live port owner, llama.cpp `/props`, tokenizer/template parity, or any behavior. No Agent or Monitor call occurred.
- `researchctl audit` still passes registry integrity with four closed cycles, no open experiment, 352 calls / USD 0.039167058 recorded in new-cycle accounting, and no errors. Both prior DeepSeek grants are consumed; project budget remaining is not a grant.

## ADVERSARIAL REVIEW

The design retains the common-incentive and no-chat cells and all five conditions in each matched matrix group. A positive result would support only this finite assigned package under the tested Qwen checkpoint and schedule. Shared target information, added chat stage, deterministic decoding, and the constructed matrix set remain interpretive limits. A non-positive or family-specific outcome is a valid falsification; invalid/missing outcomes stay in the denominator and make the primary result inconclusive.

The separate-context critic ranked this package above additional B5 inference but only reviewed sanitized artifacts, not raw M1-100 T/B/E. The current M1 Monitor candidate is separately NO-GO for its own dispatch because its metric, rule-baseline, adjudication, and live-runner gates are incomplete. Its 672-generation/696-HTTP combined candidate budget is not a reason to add it to Cycle 1.

## DECIDE / REPORT

**Scientific outcome:** `INCONCLUSIVE` for the prospective M1 v3 hypothesis because it has not been run. The post-hoc pattern is motivating evidence, not confirmation.

**Operational disposition:** offline candidate passes; not registered, no live identity check, no M1 approval, no inference. The exact authorization request and hash snapshot are now reviewable. The next action is one exact user approval for the local M1 v3 scope; after it, create the immutable approval batch, register the schema-v2 preregistration, and run only the gated live command. This Goal remains active after that gate.
