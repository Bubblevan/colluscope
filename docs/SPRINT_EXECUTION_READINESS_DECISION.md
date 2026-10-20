# Sprint Execution Readiness Decision

**Decision date:** 2026-10-20
**Branch:** `codex/sprint-execution-readiness-20261020`
**Decision:** **GO for offline artifact/software validation only; NO-GO for live Monitor or M4 inference.**

## Gate-by-gate decision

| Gate | Decision | Evidence |
|---|---|---|
| B0 reference-label blindness | GO after correction; old outputs retained | Poisoned-reference counterexample passes; two former privileged matches are now errors; B0 14/35 vs old 16/35. |
| Frozen baseline artifact replay | GO for deterministic offline replay | `verify_sprint_baselines.py`: 8 synthetic cases, 280 references and schedule rows, source hashes verified; no model calls. |
| B2–B5 bounded executor integrity | GO for mock only | 280/280 mock rows terminal, 280 request-response links, no retry, no auth persisted, raw ACL verified, reserved cost $0.4086309 below $1.00; zero real calls. |
| M4 runtime/software replay | GO for mock only | 24/24 groups, 264/264 synthetic records and 24/24 independently replayed settlements; zero model/HTTP/network calls. |
| Local model/runtime identity | GO on file hashes only | Model/runtime/tokenizer/template hashes match the frozen identity; server was not launched. |
| M4 stimulus token equality | **NO-GO** | Both positive-control and focal Proposal/Neutral pairs differ by exactly one token in 24/24 groups. |
| Live endpoint and tokenizer parity | **NO-GO / unverified** | No llama-server was launched; endpoint and tokenization parity are not established. |
| Monitor live inference | **NO-GO / not authorized** | Current run is mock-only, pricing is an estimate for an alias, and no current provider/model identity was checked. |
| Whole repository test gate | **INCOMPLETE due missing historical evidence** | **377 passed, 13 failed, 6 errors, 1 skipped.** All 19 failures/errors are missing ignored historical inputs: 4 M1-100 raw-run/resume tests, 6 M2-V3 setup errors depending on M1 T, 6 M2-V2 tests depending on M1-P0 T, and 3 M3 tests depending on M1-P0 frozen configs. Exact output: `docs/results/sprint-execution-readiness/pytest-full-suite-final.log`. |

## What is established

The reference-blind B0 is less accurate on the old ambiguous privileged rows; that is the expected cost of removing label leakage. The offline monitor and M4 software can enforce their configured schedules and produce independently replayable mock artifacts. The local Qwen/model/runtime files match the frozen file identities. The rendered M4 message pairs are not token matched under the exact local tokenizer implementation.

The targeted readiness/M3 subset yielded **119 passed, 3 failed**; the three failures have the same M1-P0 missing-config cause documented above. The full suite has 377 passes and a separate opt-in skip, but cannot be called green because the original ignored experimental files are absent. These are retained as blockers in the tests and reports.

## What is not established

There is no real Monitor prediction, real M4 Agent behavior, live server/tokenizer parity, generalization to naturalistic traces, causal communication effect, or evidence of latent collusion in this work. The shared rewarded target remains a confound: A and B receive the same private target and bonus, so matching that target without a communication intervention cannot identify communication-induced coordination.

## Required before another execution request

1. Version the M4 stimuli prospectively to address or explicitly accept the token mismatch without output-driven edits; rerun exact tokenization.
2. Verify live server/tokenizer/template parity without generating an Agent response, within a separately approved local diagnostic budget.
3. Freeze the provider's exact model identity and current price before any Monitor request; preserve the one-attempt schedule, endpoint restrictions and hard budget.
4. Obtain separate user approval fixing model, protocol, call ceiling, output retention and stop conditions. This decision does not authorize any of those calls.

## Reproduction

See `docs/SPRINT_EXECUTION_READINESS_PROTOCOL.md` for complete commands. The raw Mock traces are local, ignored and ACL-restricted; their committed audit receipts/hashes permit artifact-integrity checking but are not public behavioral data.
