# M4 DeepSeek Agent V1 — Decision

**Decision state:** `PRE_INFERENCE_NO_GO_PENDING_FREEZE_REVIEW`  
**No real requests authorized by this document alone.** The user separately authorized the bounded DeepSeek-first run through the attached task; this file records implementation status and does not expand that scope.

## Gate status

| Gate | Pre-inference status | Evidence needed to change status |
|---|---|---|
| Model/API identity and credential | Offline preflight passed; credential value was not displayed or written | Pilot HTTP response must return an allowlisted model alias and nonempty stable fingerprint |
| Strict/fallback interface | Not run | Pilot must validate all required Agent action types and Monitor threshold; fallback only after explicit capability rejection |
| Raw evidence persistence and privacy ACL | Temporary current-user ACL preflight passed | Actual run directory ACL and every request/response/ledger entry must verify; auth headers must remain absent |
| Per-request and aggregate budget | Implemented and unit-tested | Attempt ledger must remain ≤264 Agent, ≤376 Monitor, ≤900 global, reserved cost ≤USD 5 |
| First two Agent gate groups | Not run | Both assigned groups must complete and independently replay from raw requests/responses |
| Full 24-group Agent corpus | Not run | Only gate PASS unlocks bulk; any failed group stops remaining Agent calls and remains in denominator |
| Scientific inference | Not available | Even a complete run supports only this alias/interface and observable behavior; no latent collusion label |

## Decision rule

No Agent bulk inference until the compatibility pilot passes and both gate groups independently replay. No Monitor schedule until all 24 assigned Agent groups are present, independently audited, and the Monitor plan freeze reproduces byte-for-byte. Any fatal identity, privacy, cap, or source-integrity mismatch is an immediate stop. Invalid model actions are retained as failures; `no_message`, target disagreement, or no welfare loss are ordinary behavioral outcomes, not interface failures.

## Current call count

Real model/API calls in this task as of the frozen candidate: **0**. Offline tests and injected fake HTTP responses are not model behavior evidence.
