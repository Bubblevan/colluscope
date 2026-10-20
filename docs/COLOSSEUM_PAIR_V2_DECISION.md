# Colosseum pair v2 gate decision

**Decision date:** 2026-10-20 (Asia/Shanghai)

## Offline gate result

**PASS** for the bounded protocol freeze, source-derived compatibility shim, independent outcome replay, and offline mock tests.

### Submission-branch recheck

This decision was rechecked on a clean topic branch based on remote `main` at `598e17bb6e35d95210c02add76ff7e6496c5af10`. The targeted Colosseum suite passed **17 tests and 8 subtests**. A current full-repository rerun did **not** pass: **307 passed, 16 failed, 6 errors, 1 skipped, and 8 subtests passed**. The failures/errors were traced to sandbox-blocked local HTTP tests and missing ignored historical M1 artifacts, not omitted from the report. The earlier recorded “57 passed” result is retained as a historical run result and is not used to describe this recheck. Details and retained failure records are in `COLOSSEUM_FAILURE_AND_REPAIR_HISTORY.md` and `docs/results/colosseum-local-audit-20261020/submission-recheck-failure-history.txt`.

Evidence:

- The final targeted Colosseum recheck passed 12/12 runtime compatibility tests, 3/3 independent audit tests, and 2/2 local-reproduction tests (17 total plus 8 subtests). The full-repository recheck is not green in this sandbox; see the subsection above.
- The original ledger independently matches 128 starts, 127 responses, 106×200, 19×400, 2×500, and one in-flight no-response request.
- All 21 failed responses have a sanitized row-level episode/agent/round mapping. The baseline mapping is cross-checked against prompt timestamps and terminal turn records; the interrupted-arm mapping is timestamp-based only.
- The seed-1 Jira cost reconstruction matches all 48 cost cells explicitly printed in first-round agent prompts; independent realized reward and exact feasible optimum agree with frozen public fields and independently calculated additive rewards.
- Strict tool-argument tests prove malformed arguments and environment rejection cannot invoke a successful callback. Plain assistant/no-tool planning output terminates after one generation; execution without an environment commit fails explicitly.
- Request capture unit tests preserve exact mocked request/response bytes and omit auth headers. No external endpoint or model was contacted by tests.
- The current source version, local model hash, llama.cpp version, two episode IDs, and 180-attempt guard are frozen and independently verified with manifest SHA-256 `CAB6B33C1ADF8403AE4F6DA5CDBF22981A08CDC55A80D208A1913E89EF055ECE`. This is a no-inference freeze; machine-specific model/server paths remain local and are supplied by environment variables.

## Real-pair dispatch

**NO-GO in the present evidence state.** The old failed request and response bodies, generated tool arguments, and `finish_reason` were never persisted. The 500s occur before a completion object returns; offline mocks cannot establish that the adapter handles the actual hidden completion that produced them. The new adapter addresses the source-confirmed 400 continuation defect and the unsafe `{}` fallback, but it cannot prove the server-side 500 is repaired.

No real model calls were made in this task. The next-step command is fully bounded to the two seed-1 arms and a hard cap of 180 attempts; it is provided in `COLOSSEUM_PAIR_V2_PROTOCOL.md` and awaits separate user approval.

## Claim boundary

The one completed historical summary supports exact arithmetic for one outcome, not a general behavior estimate. It includes 16 failed planning continuations even though the upstream runner wrote `status=complete`. Neither that outcome nor a future paired difference should be described as proof of collusion, intent, successful negotiation, or a communication-only causal effect.
