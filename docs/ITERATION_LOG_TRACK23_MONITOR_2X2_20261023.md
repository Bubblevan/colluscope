# Iteration addendum — Track 2.3 Monitor 2x2 (2026-10-23)

## INSPECT / RUN

The registered development set (pairs 31, 20, 32; C0/C1/D0/D1) used 12 DeepSeek calls, one attempt each. Eleven outputs were valid after the documented exact-claim-echo compatibility review; `pilot-32-D1` returned mutually conflicting q7 status/reason/note and failed the 12/12 expansion gate. All 12 responses were HTTP 200 with usage; returned alias/fingerprint were stable. Reconciled peak-rate cost is USD 0.054851448. The original summary undercounted by USD 0.001508352 because the invalid response failed before a cost accumulator update. All 24 held-out calls remain unstarted.

## Adversarial interpretation

This is not a C-vs-D result. A zero-call review found an implicit q7 rounding convention and an explicit q9 causal cue. Pair 31 is a development example, not an efficacy estimate. The invalid response and initial C1 parser rejection are preserved.

## Decision

Operational `BLOCKED`; scientific outcome `EXECUTION_BLOCKED`. Do not use remaining authorization to bypass the frozen expansion gate.

## One next action

Perform a zero-call, versioned audit of numeric tolerance, q9's role, contradictory-output handling, and cost aggregation before considering any new preregistration.
