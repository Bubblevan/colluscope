# Iteration follow-up — M4 B5 repeatability runner

**Date:** 2026-10-21
**Evidence class:** offline engineering preflight
**Model/API attempts:** 0
**Decision:** offline canary pass; live dispatch no-go pending registration and a new approval.

## INSPECT

The highest remaining operational threat was that the new repeated-view schedule could duplicate an uncertain attempt, silently accept malformed output, save credentials, or send to a non-approved endpoint. The completed context-sensitivity approval is consumed and does not cover this candidate.

## SPECIFY

The counterexamples were: same context/view repetitions compile to different bytes; an HTTP 400 is hidden behind missing usage; a malformed 200 is retried or treated as valid; a process interruption causes a started request to be resubmitted; an endpoint redirects or leaves loopback in offline tests; or production dispatch reads credentials/sends without a new registration and authorization.

## IMPLEMENT

Added a versioned runner that uses the existing M4 request compiler, freezes all 144 body hashes in a Git-ignored ACL-restricted directory, enforces the per-run attempt and cost ceilings, writes an append-only start row before each transport call, records raw response bytes locally, performs strict parsing without repair, and never retries. A started slot with unknown outcome is terminalized and skipped on resume. Production dispatch validates registration, the immutable approval batch, budget snapshot, expiry, off-peak time, endpoint, manifest, and frozen source hashes before loading the API key.

## RUN

- Offline preparation: 144 slots, 48 context/view profiles, all triples byte-identical, 12,104 maximum input-token upper bound, USD 0.26585640 off-peak reserve, 0 model calls.
- Fake-server canary: 431 localhost response files, zero external requests and zero model/API calls. The final targeted test suite passed 6/6.
- Initial test failures were retained. The first identified HTTP error misclassification; later failures were caused by a missing zero-valued summary field and a stale fixture with a duplicated start entry. The runner rejected the duplicate entry before further network activity; the corrected fresh interruption fixture completed with 143 new local requests and one already-started slot recorded as unknown, without resending it.
- `python scripts/researchctl.py audit`: `integrity_check=PASS`, four historical registered cycles, zero open experiments, and unchanged usage of 352 requests / USD 0.039167058.

## ADVERSARIAL REVIEW

The fake outputs are canned parser fixtures and provide no monitor-accuracy evidence. The view contrast still bundles permission, event packaging, message text, and token length. The DeepSeek alias is mutable. The 144 privileged message-event appearances would leave the local machine if approved and dispatched. Matching fingerprints would not prove identical hidden serving state. The runner's production path remains unexercised against the provider and is deliberately unreachable without a registered, exact-scope approval.

## DECIDE

Operational status is `OFFLINE_CANARY_PASS / LIVE_DISPATCH_NO_GO`. The 232-call approval is not reused. The M4 scientific result remains `INCONCLUSIVE`; this runner adds no behavior or monitor evidence.

## REPORT

The next single action is to obtain a new exact-scope approval for the 144-request candidate, including the private-message transfer, before registering or dispatching it. If that approval is not granted, continue the program through offline M1 evidence work rather than calling the monitor.
