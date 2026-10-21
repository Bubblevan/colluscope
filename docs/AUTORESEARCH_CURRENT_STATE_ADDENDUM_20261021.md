# Autoresearch Current-State Addendum — 2026-10-21

This addendum records the current authorization and next experiment state without rewriting the historical `CODEX_AUTORESEARCH_GOAL.md`, `RESEARCH_PROGRAM.md`, `COLLUSCOPE_PERSISTENT_RESEARCH_GOAL.md`, or closed campaign records.

## Current authorization facts

The `CODEX_AUTORESEARCH_GOAL.md` and `RESEARCH_PROGRAM.md` paragraphs describing the `DS-FLASH-1200-2P50-20261020` window are stale. Those files are included in the hash-pinned B5 post-close artifact manifest, so this update deliberately leaves them unchanged.

The current registry is authoritative for new-cycle usage:

- `DS-FLASH-1200-2P50-20261020` is scoped to the closed 120-call B5 diagnostic and is fully consumed.
- `DS-FLASH-M4B5-CONTEXT-232-20261021` is scoped to the closed M4-B5 campaign and is fully consumed at 232 calls / USD 0.027381738. Its later expiry date does not make its exhausted budget reusable.
- `python scripts/researchctl.py audit` reports four closed cycles, no open experiment, 352 new-cycle calls, and USD 0.039167058 recorded. The project-level arithmetic balance is 848 calls and USD 2.460832942; that balance is not an experiment authorization.
- No current approval covers the M1 v3 Qwen experiment. A general preference for DeepSeek use during a low-price period does not authorize a different local-model experiment or external transfer of private messages and ballots.

## Selected scientific direction

The selected candidate remains `m1-reward-chat-24group-replication-v1`: a preregistered finite replication of the private-target-reward × chat-stage package over 24 distinct payoff matrices. It assigns 120 episodes and permits at most 456 local Qwen generations / 480 loopback HTTP attempts, zero retries/replacements, zero external requests, and USD 0 external spend. The primary claim is the finite assigned-package interaction only. Shared knowledge of the rewarded target and the additional message stage prevent a message-semantic causal or collusion/intent claim.

The current `--check-only` run passed the schedule, independent six-permutation matrix audit, prompt-profile recomputation, and registry checks. A separate no-call verifier matched all 23 runtime source hashes and 11 supporting review hashes. It did not start a server, verify live listener ownership or tokenizer/template parity, or generate any agent action. The hash-pinned review snapshot is `research/drafts/m1-package-replication-v3-review-manifest-20261021.json`; its status explicitly remains non-preregistered and non-authorizing.

The M1 Monitor task is separate and deferred. Its current candidate passes a structural offline audit but is not dispatch-ready: it lacks a deterministic extraction baseline, primary metrics/comparison rule, named third adjudicator, live dispatcher, and human annotations. Sending delivered private-message text and recipient ballots to DeepSeek would require an explicit approval naming that transfer. These Cycle 2 gaps do not block the M1 Agent behavior experiment.

## One next action

Request exact-scope user authorization for the M1 v3 local Qwen experiment described in `docs/M1_PACKAGE_REPLICATION_AUTHORIZATION_REQUEST_20261021.md`. Only after approval should the project create an immutable authorization batch, complete and register the schema-v2 preregistration, and run the existing gated preflight. No model call is permitted before those steps; do not reuse either consumed DeepSeek approval.
