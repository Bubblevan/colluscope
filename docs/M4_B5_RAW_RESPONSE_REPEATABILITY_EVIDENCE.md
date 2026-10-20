# M4 B5 Raw-Response Repeatability Audit — Evidence

**Status:** finite raw-output variation confirmed; no new model/API calls.  
**Registered cycle:** `m4-b5-raw-response-repeatability-v1` (`offline_reanalysis`).  
**Frozen schedule SHA-256:** `456600dd1dd969aef75fae848a8c900f38bb60612f0dcf1315f5da03ad0770a0`.  
**Audited output:** `docs/results/research-sprint-20261021/raw-response-repeatability-v5/`.

## Question and selection

The preregistered question was whether stored label disagreements across historical/current B5 observations with exactly matching request bodies and matching reported `system_fingerprint` values were present in the raw tool-call arguments, or arose in parsing, scoring, or row association.

The frozen schedule contains 48 historical/current pairs: 24 `public_only` and 24 `privileged_audit`. It was selected by case hash and permission, exact request-body bytes, and reported fingerprint; it did not read labels, evidence references, response bodies, or tool arguments. All assigned pairs remain in the denominator.

## Independent replay method

The public auditor API accepts the schedule path and verifies its externally pinned hash (`frozen_schedule_verified=true` in the report), exact permission denominators, source sidecar snapshots, unique request IDs, pair associations, raw file hashes, exact request-byte equality, returned model/fingerprint and finish metadata. It then rejects duplicate JSON keys, requires one assistant `report_evidence` tool call, checks the strict label/reference schema, and compares raw parsed labels and references with stored rows. It never repairs an output. Only the internal helper used by synthetic unit tests accepts an in-memory schedule dictionary.

The auditor exports hashes, aggregate counts, row transition labels, and equality flags only. It does not export request/response bodies, arguments, request IDs, case IDs, or message text. Raw bytes remain in the Git-ignored local run directories.

## Results

| Measure | Public-only | Privileged Audit | Total |
|---|---:|---:|---:|
| Assigned pairs | 24 | 24 | 48 |
| Source/request integrity valid | 24 | 24 | 48 |
| Strict raw response parse valid | 24 | 24 | 48 |
| Raw label matches stored prediction on both rows | 24 | 24 | 48 |
| Raw label differs across historical/current pair | 17 | 2 | 19 |
| Raw evidence references equal | 24 | 21 | 45 |
| Exact tool-argument bytes equal | 3 | 15 | 18 |
| Canonical arguments equal | 7 | 20 | 27 |
| Complete response bytes equal | 0 | 0 | 0 |

Public-only transition counts were `absent→present` 1, `insufficient_evidence→insufficient_evidence` 2, `insufficient_evidence→present` 15, `present→insufficient_evidence` 1, and `present→present` 5. Thus, 15 of the 17 public-only disagreements were transitions from abstention to `present`; they are not all ordinary binary label flips.

Privileged Audit transitions were `absent→absent` 19, `absent→present` 1, `insufficient_evidence→present` 1, and `present→present` 3. One of the two privileged label-disagreement pairs also had different evidence-reference arrays. Every raw reference array still matched its corresponding stored row.

The independent audit returned `PASS_INDEPENDENT_RAW_RESPONSE_REPLAY`, `source_snapshot_hashes_match=true`, `frozen_schedule_verified=true`, zero integrity failures, zero strict parse failures, and zero raw/stored mapping mismatches. The frozen schedule builder was restored to its preregistered byte hash, and rebuilding it reproduced the same schedule hash. The v5 analyzer adds externally pinned schedule, denominator, and duplicate-ID gates; its focused suite passed **12/12**.

The independent critic's final v5 review found no remaining material flaw in the public audit path and confirmed that the substantive v5 counts match the earlier replays. The critic reviewed sanitized outputs and code but did not rerun tests or inspect raw runs; the test result comes from the saved local test log.

## Interpretation limits

This is finite response-level variation among retained historical/current observations for identical request-body bytes and matching *reported* fingerprints. It rules against the specific explanation that these 19 stored label disagreements were introduced by the retained parser/scorer mapping. It does not establish that hidden serving state, weights, or provider configuration were identical, and it does not identify randomness as the cause.

It does not explain the earlier Public-only versus Privileged B5 changes: those views differ in message text, event packaging, permission/completeness cues, and input length. The output label is a deterministic public-welfare category, not a collusion or intent label. The rule baseline can compute this target from the public matrix, ballots, settlement, and welfare; this audit is a measurement-integrity result, not evidence that an LLM is needed for that calculation.

## Reproduction

```powershell
python scripts/freeze_m4_b5_raw_response_repeatability.py --out docs/results/research-sprint-20261021/raw-response-repeatability-v5/rebuilt-schedule-check.json
python scripts/audit_m4_b5_raw_response_repeatability.py --out-dir docs/results/research-sprint-20261021/raw-response-repeatability-v5
python -m pytest -q tests/test_m4_b5_raw_response_repeatability.py
python scripts/researchctl.py audit
```

The builder command hashes retained response sidecars but does not parse response contents. The auditor command independently parses the raw response arguments. The initial preregistration failures, first fixture test failure, v1–v4 exports, critic findings, amendment timestamp correction, and a preclose registry-audit failure caused by appending to two hash-pinned historical documents remain preserved under `research/experiments/m4-b5-raw-response-repeatability-v1/` and `docs/results/research-sprint-20261021/`. The historical documents were restored byte-for-byte; the update moved to dated appendices; the final preclose registry audit passes.

### Artifact hashes

- v5 audit JSON: `1926e9c60f565ef6b18ab1c3df7cd17326694b0e6cb88899fa7b500b67d7f62d`
- v5 sanitized CSV: `2ca94b277f71dafb0d81534e9cb7b83b31ba9ab4cb99b2d4f16b2ecb44efcc62`
- Analyzer code at v5 replay: `fd15a28d7a680d6b440f59e01f5fc6b6fd4788c0f4cac7fc2c294d49146ee775`
- Focused tests at v5 replay: `127174fc411b786b826f47f478a2132423f8551b84d7218c5e148d653176f1d6`
- Frozen schedule builder: `194112dc47a7cab16b821b2519d5d4ee4f34e72dab45eb8cb672fe6a25613eee`
- Independent critic review: `docs/results/research-sprint-20261021/raw-response-repeatability-independent-critic-review-v2.md`
