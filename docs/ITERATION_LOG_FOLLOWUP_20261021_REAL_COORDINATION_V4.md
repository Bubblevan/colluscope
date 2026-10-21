# Iteration Log — DeepSeek Real Coordination V4

## INSPECT

V3 was not started. Official DeepSeek strict-mode documentation excludes the `null` union and `maxLength` constraints in its game-stage schemas, and the fact-control schemas were too simple to test those constraints. The configured ordinary completion URL also differed from the shared client's strict Beta endpoint. The highest risk was therefore a predictable HTTP 400 after spending the four controls, followed by an invalid endpoint record.

## SPECIFY

Counterexamples: reject `type: ["string", "null"]`; reject `maxLength`; fail if the frozen endpoint differs from the actual strict client route; preserve `no_message` without translating or repairing model output; reject over-240-character text after storing the raw response; never execute game requests after a failed capability control.

## IMPLEMENT

Closed V3 as `BLOCKED / INVALID_EXPERIMENT` before dispatch with zero calls, and preserved the frozen V3 files. Created V4 with `UNDECIDED` string sentinel, local 240-character validation, an offline strict-schema validator, exact `/beta/chat/completions` endpoint, fresh request IDs, and the same task, rewards, arm schedule and 40/$0.50 cap. Checked the official pricing page; the runtime uses the current peak cache-miss/output rates as conservative reservations.

## RUN

- Python compilation: exit 0.
- Targeted V4 runner/schema tests plus frozen V2 behavior/analysis regressions: **31 passed**.
- Freezer: `PASS_FREEZE_CHECK`; schedule SHA `6117b17982aafbb711a2ceeeb35de54a4fbadb1f3a26b31c530160539cff4b96`; config SHA `a26c3becb6ff43ce5fa8d05b74f6deb02b8ab989f60896313c44f56df8542211`.
- Runner `--check-only`: `PASS_OFFLINE_PREFLIGHT`, 0 calls, exact Beta endpoint.
- Registry audit: `PASS`, no errors; V4 is the only open cycle.
- V4 model requests before push: **0**.

## ADVERSARIAL REVIEW

The V4 schemas now fall within the published strict subset, but only the first four actual requests can test live provider behavior. The provider alias remains mutable; the first valid response pins returned model/fingerprint. The shared +20 target remains a parallel-behavior confound. Three fixed matrices and a single temperature-zero run cannot identify population or latent-intent effects. The official API may still reject an unexpected schema detail; the first such failure must remain terminal, with no retry.

## DECIDE

GO for one V4 batch only after commit/push: at most 40 physical attempts, $0.50 peak-rate reservation, zero retries/replacements, 90-minute cap. Four capability controls precede all 36 game requests. A failed control stops the entire game schedule; an invalid game action blocks its dependencies. V3 remains closed and is never dispatched.

## REPORT

The branch is ready for the user-authorized live run after it is pushed. If controls pass, continue through the frozen schedule within the hard cap. Analyze all assigned rows, including invalid and unattempted rows. Report observable messages, delivery, ballots, welfare, failures, and costs separately; do not label any row as latent collusion.


## Execution update — 2026-10-21 05:23 UTC

V4 was pushed before dispatch at `7a314a8`. The first assigned fact-delivery control (`v4-C1-delivered`) failed before any HTTP response: Windows `getaddrinfo` returned `Errno 11001`. The frozen runner stopped immediately. Final counts for this execution are 1 physical transport attempt, 0 HTTP responses, 0 valid model completions, 39 assigned requests unattempted, 0 retries, and 0 replacements. No behavior, fact-use, communication, or payoff outcome is observable.

The raw request remains in the Git-ignored local run directory. Its SHA-256 (`e80ed1e34d72e8056fc1a572af2f29778b9ce2aa2a8bc0ad94409c523744bd9f`) matches both the `attempt_started` ledger and request metadata; no response file or provider identity file exists, and no authorization header was stored. A later DNS-only check resolved the official host, after an earlier DNS/TLS-only check had also passed. This is consistent with a transient local resolver failure; it does not show that DeepSeek was down. No model retry was made.

The frozen post-run analyzer emits `request_hash_mismatch` because the shared client intentionally omits `request_sha256` from transport terminal rows. Independent byte-level replay confirms the start and metadata hashes match the raw request, so this specific analyzer finding is a false positive. The frozen analyzer was not edited after registration. Full sanitized audit: `docs/results/deepseek-real-coordination-v4/transport_failure_audit.json`; cost/request ledger: `docs/results/deepseek-real-coordination-v4/attempt_ledger.json`.

Decision: **BLOCKED / EXECUTION_BLOCKED**. The V4 behavior hypothesis is unchanged and untested. The first control did not fail behaviorally; it produced no response. The one attempt is counted against the project cap; no replacement or continuation is permitted under this batch.
