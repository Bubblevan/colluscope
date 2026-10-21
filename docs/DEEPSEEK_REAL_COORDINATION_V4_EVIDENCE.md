# DeepSeek Real Coordination Pilot V4 — Evidence

**Pre-dispatch state:** registered and frozen; offline gates pass; **0 V4 HTTP attempts, 0 model responses, 0 V4 cost**. The first V4 model request is intentionally held until this branch is pushed and reported.

## Why V4 replaced V3

V3 closed `INVALID_EXPERIMENT` before dispatch. The official strict-mode subset does not support JSON Schema `null` unions or `maxLength`, both present in V3 proposal/reply schemas. The four simple fact controls would not have caught those defects. V3 also recorded the ordinary completion path while the frozen strict-function client routes to the official `/beta/chat/completions` endpoint. V3 remains at 0 calls and all 40 rows are unattempted. See [V3 schema audit](DEEPSEEK_REAL_COORDINATION_V3_SCHEMA_AUDIT.md) and [V3 closure](results/deepseek-real-coordination-v3/pre_dispatch_schema_failure.json).

V4 preserves the three payoff matrices, +20 shared incentive, three routing arms, call order, 40-request graph, temperature, and hard budget. It encodes a missing choice as `UNDECIDED` and applies the original 240-character limit in local validation after raw response capture. A distinct experiment ID, request namespace, schedule, and preregistration preserve this prospective interface change.

## Frozen V4 identities

- Experiment: `deepseek-real-coordination-40-v4`.
- Requested alias: `deepseek-flash`; the official pricing page currently maps this alias to DeepSeek-V4.1-Flash-1017. The provider alias is mutable; the first valid response must return an allowlisted model and a non-empty fingerprint, which are pinned for this run. No weight hash is available.
- Exact strict endpoint: `https://api.deepseek.com/beta/chat/completions`.
- Schedule SHA-256: `6117b17982aafbb711a2ceeeb35de54a4fbadb1f3a26b31c530160539cff4b96`.
- Configuration SHA-256: `a26c3becb6ff43ce5fa8d05b74f6deb02b8ab989f60896313c44f56df8542211`.
- Tokenizer SHA-256: `81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99`.
- Request graph: 4 delivery/absence controls first; then 3 matrices × 3 arms × 4 stage calls = 36 game requests. Total 40 assigned requests.
- Hard ceilings: 40 physical attempts, zero retries/replacements, USD 0.50 peak-rate cost reservation, 90 minutes. Project total at freeze is 1,157/1,200 attempts and USD 0.133568658/USD 2.50; V4 leaves three attempt slots unused.
- Official pricing checked at 2026-10-21T05:11:33Z: peak cache-miss input USD 0.30/M tokens, peak output USD 1.20/M. The runtime reserves at these peak rates, even when calling off-peak. Snapshot: `docs/results/deepseek-real-coordination-v4/official_api_preflight.json`.

## Offline evidence

| Check | Result | Record |
|---|---|---|
| Python compilation | Exit 0 | `docs/results/deepseek-real-coordination-v4/py_compile.log` |
| V4 schema, endpoint, sentinel, analysis, transport recovery and frozen V2 regression tests | **31 passed** | `docs/results/deepseek-real-coordination-v4/targeted_pytest.log` |
| Freezer reconstruction | `PASS_FREEZE_CHECK` | `docs/results/deepseek-real-coordination-v4/freeze_check.log` |
| Runner check-only | `PASS_OFFLINE_PREFLIGHT`, 0 calls, exit 0 | `docs/results/deepseek-real-coordination-v4/runner_check_only.log` |
| Research registry audit | `PASS`, no errors; V4 sole open cycle | `docs/results/deepseek-real-coordination-v4/registry_audit_final.log` |
| Official endpoint DNS/TLS-only check | TLS 1.3 succeeded; no HTTP, key, prompt, or inference | `docs/results/deepseek-real-coordination-v3/endpoint_tls_preflight.json` |

The V4 freezer and runner both reject schemas outside the documented strict subset before dispatch. Offline tests verify the correct Beta endpoint, reject null-union/maxLength schemas, preserve the 240-character local failure boundary, and reconstruct V4-prefixed outcomes independently. They do not prove the live provider will accept every schema; the runner stops on the first HTTP/schema failure and never retries it.

## Execution boundary

The user directed continuation of the previously approved 40-request batch after fixing pre-dispatch defects. V3's batch was closed unused; V4 is a new exact registration under the same 40-call / USD 0.50 ceiling, not an added second batch. No Qwen, third-party endpoint, monitor, or training call is included. Raw requests/responses and private message text are written only under Git-ignored, ACL-restricted `logs/deepseek-real-coordination-v4/`; authorization headers are never recorded.

## Interpretation boundary

Both agents know the same rewarded target, so no-delivery agreement may be independent parallel response to shared incentives. This one model alias in stateless role contexts, three fixed matrices, and one temperature-zero schedule can only support finite-run behavioral observations. It cannot prove latent collusion intent, an internal agreement, or population-level causal effects. V4 reports proposals, delivery acknowledgments, replies, ballots, concordance, and deterministic outcomes separately; it creates no latent-collusion label.


## Execution update — 2026-10-21 05:23 UTC

V4 was pushed before dispatch at `7a314a8`. The first assigned fact-delivery control (`v4-C1-delivered`) failed before any HTTP response: Windows `getaddrinfo` returned `Errno 11001`. The frozen runner stopped immediately. Final counts for this execution are 1 physical transport attempt, 0 HTTP responses, 0 valid model completions, 39 assigned requests unattempted, 0 retries, and 0 replacements. No behavior, fact-use, communication, or payoff outcome is observable.

The raw request remains in the Git-ignored local run directory. Its SHA-256 (`e80ed1e34d72e8056fc1a572af2f29778b9ce2aa2a8bc0ad94409c523744bd9f`) matches both the `attempt_started` ledger and request metadata; no response file or provider identity file exists, and no authorization header was stored. A later DNS-only check resolved the official host, after an earlier DNS/TLS-only check had also passed. This is consistent with a transient local resolver failure; it does not show that DeepSeek was down. No model retry was made.

The frozen post-run analyzer emits `request_hash_mismatch` because the shared client intentionally omits `request_sha256` from transport terminal rows. Independent byte-level replay confirms the start and metadata hashes match the raw request, so this specific analyzer finding is a false positive. The frozen analyzer was not edited after registration. Full sanitized audit: `docs/results/deepseek-real-coordination-v4/transport_failure_audit.json`; cost/request ledger: `docs/results/deepseek-real-coordination-v4/attempt_ledger.json`.

Decision: **BLOCKED / EXECUTION_BLOCKED**. The V4 behavior hypothesis is unchanged and untested. The first control did not fail behaviorally; it produced no response. The one attempt is counted against the project cap; no replacement or continuation is permitted under this batch.
