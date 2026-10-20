# M3 Post-run Audit Errata

**Purpose:** record analysis-code corrections discovered while independently auditing the completed M3 run.
**Generation source:** runtime commit `f190c78ae995669be9772d67bf660448af44e452`; no generation source changes were made after the run.
**Model-facing semantics changed:** no.
**Raw T/B/E, prompts, request payloads and historical artifacts changed:** no.

The final independent-auditor source SHA-256 is `671658d146b752e67d3735058ad4930d7d2ba397c3a38e44563b37d0eab6b288`. This is post-run analysis code; the generation runner remains the independently verified frozen runtime at commit `f190c78ae995669be9772d67bf660448af44e452`.

## Corrections

1. **B/E episode association.** Runtime B and Public-E JSONL rows are id-less projections. The first auditor assumed each had an `episode_id` and misreported every B row as a duplicate. The corrected audit binds them to the fixed schedule using terminal progress order and verifies exact canonical equality against each immutable `episodes/<episode_id>.json` envelope. It rejects count mismatch, duplicate terminal IDs, order mismatch, missing envelopes, and altered/swapped rows.
2. **Behavior event aggregation.** The first replay beyond the join used `cf_events` before assignment. A dedicated helper now gathers message, baseline and counterfactual events for request/observation checks.
3. **T delivery semantics.** T confirmation receipts cover the initial message and baseline ballot stages. Counterfactual requests are audited as later behavior/observations but are not retroactively added to the frozen T receipt. The audit now checks these scopes separately.
4. **Unassigned private reward.** C receives the public score rule but no private target bonus. The verifier now expects C's private-bonus status to be `not_applicable` even when C returned a baseline ballot; public-rule delivery is checked independently.
5. **Optional settlement diagnostics.** The runtime stores outcome fields but omits `chair_tiebreak` and `ballot_tally`. The auditor independently recomputes these from raw ballots and compares them if both are present; it rejects a partial pair. Fixed-peer outcomes are compared by the persisted public-result fields rather than whole-object equality.
6. **Output serialization.** The independent audit previously reached export without a JSON writer. A deterministic UTF-8 writer is now defined and tested.

## Preserved failures

Seven failed no-inference replay attempts are preserved in the local append-only `runs/m3/mechanism-20261020/audit-failures.jsonl`, and sanitized transcripts are in `docs/results/merge-m0-m2/m3-independent-audit-failure.log`. Partial output directories from failed runs were retained. The nonempty `v6` partial and the earlier successful `v7` duplicate are archived under the ignored local `runs/m3/mechanism-20261020/audit-attempt-outputs/`; the final successful output is `docs/results/m3-mechanism-audit-final/`.

One manually appended local failure row used a mistyped placeholder timestamp. It was not rewritten; the immediately following append-only correction records the actual clock time and explains the error. The sanitized public failure note identifies this correction.

Targeted regression coverage is in `tests/test_m3_independent_audit.py`; the focused run passed 26 tests. The first full-repository attempt was sandbox-blocked for six loopback-only HTTP tests (338 passed, 1 skipped); the sanitized result is `docs/results/merge-m0-m2/pytest-m3-postrun-audit.log`, and byte-for-byte raw output is local at `runs/m3/mechanism-20261020/logs/pytest-m3-postrun-audit-sandbox-failure-raw.log` (SHA-256 `be07885249fe2d706425bdf6c55803bde474a269b25cc605cb753ff9fb282bdd`). The same full suite passed with loopback test-server permission: **344 passed, 1 skipped**, recorded in `pytest-m3-postrun-audit-escalated.log`. No model call or external network was involved.
