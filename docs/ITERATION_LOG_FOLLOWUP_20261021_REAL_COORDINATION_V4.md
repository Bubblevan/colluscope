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
