# Independent scientific critic — B5 raw-response audit v5

**Scope:** sanitized v5 result, packet v2, analyzer, tests, registered protocol and amendments. The reviewer did not open local raw runs, request/response bodies, or private-message text and did not rerun model calls.

## Verdict

`SUPPORTED` for the narrow finite raw-output label-variation claim; no remaining material flaw was identified in the v5 public audit path.

## Checks

- The public `audit_pairs()` path takes a schedule path and verifies the preregistered SHA; the CLI uses this route and records `frozen_schedule_verified=true`.
- The schedule validator requires 48 pairs with 24 for each permission.
- Historical predictions, current results, and current attempt-start rows reject duplicate request IDs; tests cover all three maps and replacement schedules.
- V5 matches earlier sanitized replays on 19 label disagreements, 29 agreements, all transition and reference-equality counts, 48 valid rows, and zero raw/stored mismatches. The CSV is byte-identical across the versions.
- The reviewer did not execute the 12 tests; the saved test output reports 12 passed.

## Scientific limits

The result concerns finite historical/current response differences under equal request bytes and reported fingerprints. It does not isolate the cause, establish population stochasticity, or explain the earlier evidence-view effect. The next study, if separately authorized, should repeat within cases while varying message content, event structure, completeness/provenance, and length separately.
