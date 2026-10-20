# Sprint Execution Readiness Decision

**Decision date:** 2026-10-20
**Branch:** `codex/sprint-execution-readiness-20261020`
**Current scoped decision (2026-10-20): GO for the frozen M4 v2 tokenizer/template parity gate only; NO-GO for M4 behavioral inference or any Monitor inference.**

This update supersedes only the earlier “tokenizer parity unverified” status for the fixed M4 v2 offline-Mock prompts. It does not authorize Agent generations, does not validate natural model-generated proposal lengths, and does not change the frozen v1 results.

## Gate-by-gate decision

The following table is the original readiness snapshot before the v2 server diagnostic; the dated addendum below supersedes only the token-parity and server-verification rows.

| Gate | Decision | Evidence |
|---|---|---|
| B0 reference-label blindness | GO after correction; old outputs retained | Poisoned-reference counterexample passes; two former privileged matches are now errors; B0 14/35 vs old 16/35. |
| Frozen baseline artifact replay | GO for deterministic offline replay | `verify_sprint_baselines.py`: 8 synthetic cases, 280 references and schedule rows, source hashes verified; no model calls. |
| B2–B5 bounded executor integrity | GO for mock only | 280/280 mock rows terminal, 280 request-response links, no retry, no auth persisted, raw ACL verified, reserved cost $0.4086309 below $1.00; zero real calls. |
| M4 runtime/software replay | GO for mock only | 24/24 groups, 264/264 synthetic records and 24/24 independently replayed settlements; zero model/HTTP/network calls. |
| Local model/runtime identity | GO on file hashes only | Model/runtime/tokenizer/template hashes match the frozen identity; server was not launched. |
| M4 positive-control stimulus token equality | **GO for prospective v2 local count only** | v1 failure was reproduced (0/24 exact, 183 vs 184); separate `NONE` candidate v2 matched 24/24 (183 vs 183) under the frozen local GGUF tokenizer/template. v1 remains unchanged. |
| M4 focal Proposal/Neutral stimulus token equality | **NO-GO** | Frozen runtime prompts still differ by one token in 24/24 groups. |
| Live endpoint and tokenizer parity | **NO-GO / unverified** | No llama-server was launched; endpoint and tokenization parity are not established. |
| Monitor live inference | **NO-GO / not authorized** | Current run is mock-only, pricing is an estimate for an alias, and no current provider/model identity was checked. |
| Whole repository test gate | **INCOMPLETE due missing historical evidence** | **377 passed, 13 failed, 6 errors, 1 skipped.** All 19 failures/errors are missing ignored historical inputs: 4 M1-100 raw-run/resume tests, 6 M2-V3 setup errors depending on M1 T, 6 M2-V2 tests depending on M1-P0 T, and 3 M3 tests depending on M1-P0 frozen configs. Exact output: `docs/results/sprint-execution-readiness/pytest-full-suite-final.log`. |

## What is established

The reference-blind B0 is less accurate on the old ambiguous privileged rows; that is the expected cost of removing label leakage. The offline monitor and M4 software can enforce their configured schedules and produce independently replayable mock artifacts. The local Qwen/model/runtime files match the frozen file identities. A separate positive-control v2 candidate now matches exactly under the embedded local tokenizer; frozen v1 remains mismatched, and the focal Proposal/Neutral pair remains mismatched.

The targeted readiness/M3 subset yielded **119 passed, 3 failed**; the three failures have the same M1-P0 missing-config cause documented above. The full suite has 377 passes and a separate opt-in skip, but cannot be called green because the original ignored experimental files are absent. These are retained as blockers in the tests and reports.

## What is not established

There is no real Monitor prediction, real M4 Agent behavior, live server/tokenizer parity, generalization to naturalistic traces, causal communication effect, or evidence of latent collusion in this work. The shared rewarded target remains a confound: A and B receive the same private target and bonus, so matching that target without a communication intervention cannot identify communication-induced coordination.

## Required before another execution request

1. If using the v2 positive-control candidate, explicitly freeze it in a new M4 protocol/runtime version; retain v1 unchanged. Address or explicitly model the remaining focal token mismatch without output-driven edits, then rerun exact tokenization.
2. Verify live server/tokenizer/template parity without generating an Agent response, within a separately approved local diagnostic budget.
3. Freeze the provider's exact model identity and current price before any Monitor request; preserve the one-attempt schedule, endpoint restrictions and hard budget.
4. Obtain separate user approval fixing model, protocol, call ceiling, output retention and stop conditions. This decision does not authorize any of those calls.

## Reproduction

See `docs/SPRINT_EXECUTION_READINESS_PROTOCOL.md` for complete commands. The raw Mock traces are local, ignored and ACL-restricted; their committed audit receipts/hashes permit artifact-integrity checking but are not public behavioral data.

## Decision update — M4 v2 fixed-stimulus tokenizer parity (2026-10-20)

| Gate | Updated decision | Independently replayed evidence |
|---|---|---|
| Positive-control v2 information vs `NONE` prompt length | **GO, fixed prompts only** | 24/24 equal under local GGUF tokenizer; llama.cpp returned exact per-prompt token IDs for both arms (48/48 prompts). The v1 `XXXX` mismatch remains reproduced at 0/24. |
| Focal Proposal vs retained-history Neutral candidate | **GO, deterministic Mock stimuli only** | 24/24 equal token counts under local GGUF tokenizer; the server rendered and tokenized all 48 focal prompts exactly against frozen local prompt strings and GGUF token IDs. |
| Server/template/tokenizer parity | **GO, bounded diagnostic only** | 96/96 rendered prompts exact and 96/96 token-ID arrays exact; 192/192 local HTTP attempts returned 200; routes were only `/apply-template` and `/tokenize`; 194 exact-owner checks; no generation route. |
| Runtime's final receipt writer | **Initial run failed; corrected and smoke-tested** | Raw finalization error is retained. An independent auditor replayed every raw request/response and verified the stopped process, absent listener and removed temporary key. Corrected report construction passed a PowerShell shape smoke test and parser check; the 192-request run was not repeated. |
| Real M4 Agent behavior / 264-call run | **NO-GO / no authorization** | No completion endpoint was called. The focal prompts were generated from deterministic Mock message actions; natural model-generated messages may change prompt token lengths. A separate execution approval remains required. |

The independent receipt is `docs/results/sprint-execution-readiness/m4-v2-server-tokenizer-parity-audit.json`. Raw request and response bodies, including private Mock observation text, remain local under the Git-ignored ACL-restricted path `runs/m4/tokenizer-parity-v2-attempt07-20261020/`.

## Reproduction commands

Run from the repository root:

```powershell
python -m pytest -q tests/test_m4_runtime.py tests/test_m4_token_matching.py
python scripts/audit_m4_v2_token_matching.py --v1-mock-run runs/m4/offline-mock-v2 --v2-mock-run runs/m4/offline-mock-v3-candidate --out docs/results/sprint-execution-readiness/m4-v2-token-match-audit.json
python scripts/audit_m4_mock.py --run runs/m4/offline-mock-v3-candidate --out docs/results/sprint-execution-readiness/m4-v2-mock-audit.json
python scripts/audit_m4_llama_token_parity.py --run runs/m4/tokenizer-parity-v2-attempt07-20261020 --out docs/results/sprint-execution-readiness/m4-v2-server-tokenizer-parity-audit.json
```

The last command is an offline raw-trace replay and does not start a server. The live token-only reproduction command is `& .\scripts\verify_m4_llama_token_parity.ps1 -MockRun runs/m4/offline-mock-v3-candidate -Out runs/m4/tokenizer-parity-v2-new-run`; it issues up to 192 loopback `/apply-template`/`/tokenize` HTTP requests, never generations. Do not rerun it as part of reviewing this completed evidence package; it would create a second diagnostic run. It must be launched directly in the active PowerShell host because nested PowerShell processes on this host lacked CIM/TCP-table access.
