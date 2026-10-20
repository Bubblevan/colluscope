# Blind scientific critic packet v2 — B5 exact-request raw-response audit

Review only the frozen protocol, amendment log, analyzer/tests, sanitized v5 JSON/CSV, and evidence report. Do not open `runs/` or raw prompt/response/private-message content.

## Frozen and audited artifacts

- Experiment: `m4-b5-raw-response-repeatability-v1`; zero-call offline reanalysis.
- Schedule: 48 historical/current exact-request pairs, 24 per permission.
- Externally frozen schedule SHA-256: `456600dd1dd969aef75fae848a8c900f38bb60612f0dcf1315f5da03ad0770a0`.
- v5 report says `frozen_schedule_verified=true`; public `audit_pairs()` accepts a schedule path, checks the pinned hash, then analyzes. The dictionary helper is private and used only for synthetic unit tests.
- Exact permissions, source sidecar snapshots, pair associations, unique IDs, response hashes, and request-byte equality are checked.
- 48/48 raw responses pass strict parsing; zero integrity, parse, or raw/stored mapping failures.

## Sanitized results

- Labels differ in 19/48 pairs: Public-only 17/24; Privileged Audit 2/24.
- Public transitions: `absent→present` 1; `insufficient_evidence→insufficient_evidence` 2; `insufficient_evidence→present` 15; `present→insufficient_evidence` 1; `present→present` 5.
- Privileged transitions: `absent→absent` 19; `absent→present` 1; `insufficient_evidence→present` 1; `present→present` 3.
- Evidence references match in 45/48 pairs (Public-only 24/24; Privileged 21/24).
- Response bodies match in 0/48; raw argument bytes in 18/48; canonical arguments in 27/48.
- All raw labels and reference lists match their respective stored rows.
- v5 JSON hash `1926e9c60f565ef6b18ab1c3df7cd17326694b0e6cb88899fa7b500b67d7f62d`; CSV hash `2ca94b277f71dafb0d81534e9cb7b83b31ba9ab4cb99b2d4f16b2ecb44efcc62`.
- Focused tests: 12 passed. No model calls.

Earlier reviews requested external schedule binding, explicit 24/24 permission counts, and duplicate-ID protection. v5 adds those checks, a path-only public API, and duplicate-ID tests for historical predictions, current results, and attempt ledgers. v1–v4 results remain preserved. The append-only amendment log also records a future-time placeholder error and its correction.

## Questions

1. Does the evidence support only finite response-level label variation, or is any claim overstated?
2. Are any association/provenance integrity gaps still present in the public entry point?
3. Is the 15/17 public abstention-to-present transition pattern useful to mention, and at what level (main text, appendix, or omit)?
4. Does this audit explain the previous 20/24 Public-to-Privileged changes? Why or why not?
5. What is the smallest discriminating follow-up for within-input variability versus evidence-view sensitivity?

The comparison cannot establish intent, collusion, semantic comprehension, population stochasticity, or which cue caused a response difference. Reproduction:

```powershell
python scripts/audit_m4_b5_raw_response_repeatability.py --out-dir docs/results/research-sprint-20261021/raw-response-repeatability-v5
python -m pytest -q tests/test_m4_b5_raw_response_repeatability.py
python scripts/researchctl.py audit
```
