# DeepSeek Real Coordination Pilot V4 — Decision

**Decision: GO for the single frozen V4 batch after this branch is committed and pushed.** Offline evidence is complete. This is not a scientific conclusion or evidence of latent intent. No V4 model requests have yet been sent.

## Why execution is now admissible

- V3 is terminally closed as `INVALID_EXPERIMENT`, with zero requests, after a source-level strict-schema audit found unsupported `null` and `maxLength` constructs and an inaccurate endpoint record. No V3 row is reused.
- V4 uses supported string schemas and `UNDECIDED` for no-choice; a local validator rejects text over 240 characters after preserving raw output. The runner and freezer independently check the strict-schema subset.
- The configured and actual strict function-call endpoint agree: `https://api.deepseek.com/beta/chat/completions`.
- Tests pass (31), V4 freeze check passes, offline-only runner check passes with zero calls, and the research registry audit passes with V4 as the sole open cycle.
- The user directed continuing the previously approved 40-request DeepSeek batch after pre-dispatch repairs. V3 used 0 of 40; V4 retains the same exact maximum and $0.50 hard cost cap. Project allowance is 1,200 calls, so at most 3 calls remain unused after all 40 V4 attempts.

## Bounded execution

After push, execute:

```powershell
python scripts/run_deepseek_real_coordination_v4.py --execute
python scripts/analyze_deepseek_real_coordination_v4.py --write
python scripts/researchctl.py audit
```

The first four requests test explicit fact delivery/absence. Proceed to the 36 game requests only if all four return correct, valid, complete actions with stable model/fingerprint identity. Any incorrect control, invalid or truncated output, HTTP/transport failure, identity drift, hash mismatch, privacy failure, or budget boundary stops the relevant dependent requests; a control failure stops the entire game schedule. No retry, message rewrite, resampling, or replacement is permitted. Preserve all 40 assigned rows and every started attempt.

## Claim boundary

The primary result is a finite descriptive comparison of joint ballots under actual message delivery versus no peer delivery with the same shared +20 incentive and same number of stages. Agreement in no-delivery remains compatible with independent parallel response to a shared target. A positive gate does not prove communication caused coordination in a population and cannot identify hidden intent. No Monitor or M2 inference is authorized by this decision.


## Execution update — 2026-10-21 05:23 UTC

V4 was pushed before dispatch at `7a314a8`. The first assigned fact-delivery control (`v4-C1-delivered`) failed before any HTTP response: Windows `getaddrinfo` returned `Errno 11001`. The frozen runner stopped immediately. Final counts for this execution are 1 physical transport attempt, 0 HTTP responses, 0 valid model completions, 39 assigned requests unattempted, 0 retries, and 0 replacements. No behavior, fact-use, communication, or payoff outcome is observable.

The raw request remains in the Git-ignored local run directory. Its SHA-256 (`e80ed1e34d72e8056fc1a572af2f29778b9ce2aa2a8bc0ad94409c523744bd9f`) matches both the `attempt_started` ledger and request metadata; no response file or provider identity file exists, and no authorization header was stored. A later DNS-only check resolved the official host, after an earlier DNS/TLS-only check had also passed. This is consistent with a transient local resolver failure; it does not show that DeepSeek was down. No model retry was made.

The frozen post-run analyzer emits `request_hash_mismatch` because the shared client intentionally omits `request_sha256` from transport terminal rows. Independent byte-level replay confirms the start and metadata hashes match the raw request, so this specific analyzer finding is a false positive. The frozen analyzer was not edited after registration. Full sanitized audit: `docs/results/deepseek-real-coordination-v4/transport_failure_audit.json`; cost/request ledger: `docs/results/deepseek-real-coordination-v4/attempt_ledger.json`.

Decision: **BLOCKED / EXECUTION_BLOCKED**. The V4 behavior hypothesis is unchanged and untested. The first control did not fail behaviorally; it produced no response. The one attempt is counted against the project cap; no replacement or continuation is permitted under this batch.
