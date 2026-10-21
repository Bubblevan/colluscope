# M4 B5 View Repeatability V2 — Offline Decision

**Decision:** `OFFLINE_CANARY_PASS / LIVE_DISPATCH_NO_GO`
**Date:** 2026-10-21
**Model/API calls in this implementation cycle:** 0
**New experiment registration:** none
**New authorization:** none

## Verified offline facts

- The candidate schedule has 144 assigned slots: 24 contexts × 2 evidence views × 3 repeats. Its internal schedule hash is `37cce3e98a0493cb26e6610cdc823aa5cc7a1303086f7943ed269b895441e099`; the serialized file hash is `08e9b6d72862629f1e3e2fa3f02f3dcaee41a6356ad874cdd7cecc6d9ac93f3e`.
- Offline preparation compiled 48 context/view request profiles and verified byte-identical request bodies across each set of three repeats. It found no model-visible schedule metadata, hidden reference keys, or credential markers.
- The largest conservative input bound is 12,104 tokens. At the frozen off-peak rates with 512 maximum output tokens, the full schedule reserve is USD 0.26585640; the candidate ceiling is USD 0.35. Pricing and peak hours must be checked again before any registration or call.
- Raw request bodies and canary responses remain under Git-ignored `runs/sprint-monitor/` paths. The production run directory ACL check succeeded for 292 objects and grants explicit full control only to the current user. Authentication headers are not written to artifacts.
- The local fake HTTP server returned 431 responses across canary run directories. Those responses are canned test fixtures, not model outputs: 429 valid parser fixtures, one malformed-output fixture, one HTTP 400 fixture, and two interrupted unknown-outcome slots. One stale test fixture contained a duplicate attempt-start row; the runner rejected it before another request. A fresh versioned fixture then exercised recovery without resending.
- The final focused suite passed **6/6** in 77.28 seconds. Earlier failures and their fixes remain in the canary folder. `researchctl audit` passes with no experiment open; the existing 352 model calls and USD 0.039167058 are unchanged.

## Failure analysis

The first canary exposed an error-classification bug: an HTTP 400 lacking usage metadata was classified as missing usage. The runner now prioritizes transport/HTTP failure. A later test run exposed two harness issues: the `ALREADY_COMPLETE` result omitted `unattempted=0`, and a reused interrupted-run fixture accumulated a duplicate start row. The result field and test fixture were corrected. The duplicate row remains in the old local canary trace; the runner rejected it and did not resend the slot.

The final test suite covers preparation and exact-repeat hashes, malformed model output retention, HTTP 400 terminalization, interruption recovery with no resampling, loopback-only fake transport, and refusal to dispatch an unregistered production experiment before reading provider credentials.

## Readiness boundary

The runner is implemented and offline-canary verified, but live dispatch remains **NO-GO**. The user's 232-attempt approval belongs to the already completed and closed `m4-b5-context-sensitivity-campaign-v1`; it cannot authorize this new experiment. The 144-attempt candidate is not registered, has no matching immutable authorization record, and therefore `--dispatch` must fail closed.

Before live dispatch, all of the following remain required:

1. Explicit approval naming `m4-b5-view-repeatability-v2`, at most 144 physical attempts, USD 0.35, zero retries/replacements, official DeepSeek Flash only, off-peak only, an expiry, and the external transfer of 144 private-message event appearances.
2. Final protocol registration that pins the offline request-manifest hash `6d26f48244bd06d93b29d58d02d69f03fe49d6db967b74cae0618ccfdfaf760a`, schedule, source/compiler/runtime hashes, and exact outcome rules.
3. Fresh official price/model-version and off-peak-window checks, plus confirmation that no external fallback is configured.

The candidate tests response repeatability for two bundled evidence packages. It does not test message comprehension, a causal communication effect, collusion, intent, or monitor superiority. No hidden label or private message is converted into a collusion gold label.

## Reproduction

```powershell
python scripts/freeze_m4_b5_view_repeatability_v2.py
python scripts/run_m4_b5_view_repeatability_v2.py --prepare
python -m pytest -q tests/test_m4_b5_view_repeatability_v2.py
python scripts/researchctl.py audit
```

Offline canary counts, hashes, and saved failure logs are in `docs/results/research-sprint-20261021/m4-b5-view-repeatability-v2-offline-canary/`. Protected request/response bytes remain local and are not part of the public evidence package.
