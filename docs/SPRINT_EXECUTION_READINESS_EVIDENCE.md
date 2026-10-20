# Sprint Execution Readiness Evidence

**Run date:** 2026-10-20 (Asia/Shanghai)
**Scope:** offline artifact replay, deterministic/mock runtimes, local identity inspection.
**Real model/API calls:** 0. **External inference calls:** 0. **llama-server launches:** 0.

The committed `docs/results/sprint-execution-readiness/source-artifact-sha256.json` inventories SHA-256 hashes for the source, protocol, configuration, and captured evidence files in this readiness change. Local ignored Mock traces have separate manifests described below.

## Baseline label-leakage correction

The prior B0 implementation could mirror reference labels on two ambiguous `SC-AMB-01` privileged/evidence-aware rows. The corrected B0 reads only allowed modality/completeness and its frozen negative rule. `scripts/audit_b0_recompute.py` poisons construction truth, expected labels, references, and score-bearing fields and verifies that the prediction is invariant; a poisoned reference function raises if called.

| B0 permission | Correct after fix | Superseded result | Interpretation |
|---|---:|---:|---|
| Public-only | 2/7 | 2/7 | unchanged; weak negative baseline |
| Privileged audit | 14/35 | 16/35 | two former exact matches were reference-label leakage and are now errors |

B1 predictions changed 0 rows. All assigned rows remain present. The superseded scores, table, receipt, source inventory, hashes, and the original failure log remain in the repository. Machine-readable comparison: `docs/results/sprint-execution-readiness/b0-score-delta.json`.

## Bounded monitor mock dispatch

The offline executor processed all 280 frozen schedule rows. The independent auditor verified 280 request/response/attempt links, 280 terminal rows, 847 raw artifact files, no saved authorization headers, ACL verification true, zero retries, zero real API/model calls, and zero external network calls. Peak estimated reserve was **$0.4086309** against a $1.00 hard ceiling. The artifact inventory SHA-256 is `1c0e80a02adc864ca18299a11ff8171f68d5903e22947955b4f192c99bdf74c1`. Status is `PASS_OFFLINE_MOCK_DISPATCH_REPLAY_ONLY`; mock outputs are explicitly not monitor evidence.

Raw local mock run: ignored path `runs/sprint-monitor/mock-e2e-v1/`. Audit receipt: `docs/results/sprint-execution-readiness/sprint-monitor-mock-audit.json`.

## M4 mock runtime and independent replay

The runtime completed 24/24 assigned mock groups and generated 264/264 synthetic request-response-attempt records. Independent replay recomputed 24/24 settlements and verified every linkage. It made zero model calls, zero physical HTTP requests, and zero external network calls. Private message text was not exported. The complete mock artifact tree contains 532 files; manifest SHA-256: `f2b92f26bdeb8a68832fa18821d5d62c277d4f67d5d2da8bf4ddb0642f479143`.

Raw local mock run: ignored path `runs/m4/offline-mock-v2/`. Audit receipt: `docs/results/sprint-execution-readiness/m4-mock-audit.json`.

## Frozen local identity and token-matching gate

The identity verifier inspected but did not launch the local runtime. It confirmed the frozen checkpoint, llama.cpp build 10068 binary, runtime bundle, tokenizer/library and chat-template hashes. The actual values and versions are in `docs/results/sprint-execution-readiness/m4-local-environment.json`.

The exact rendered prompts failed token equality in all 24 frozen pairs:

| Pair | Arm 1 | Arm 2 | Equal pairs |
|---|---:|---:|---:|
| Positive-control information vs neutral | 183 tokens | 184 tokens | 0/24 |
| Focal Proposal vs Neutral | Proposal 528/533/530/529; Neutral 527/532/529/528 by family | delta +1 each | 0/24 |

The mismatch was not edited away after inspection. The verifier returns `NO_GO_LOCAL_IDENTITY_OR_TOKEN_MATCH`. A first verifier error (`Counter` missing) and the exact initial output are preserved in `m4-environment-first-run.log`; the import was fixed and a complete run recorded. No server launch or inference occurred.

## Supplementary synthetic controls

V2 contains 10 synthetic cases across 3 development and 7 disjoint evaluation construction families, 350 reference rows, and 350 prospective payload rows. The preparation and verification commands complete offline; no model/API/network calls are made and no latent-collusion gold label is created. Deterministic B1-V2 matches these constructed labels by replaying the frozen codebook; this is a software control only, not generalization or LLM performance. Initial fixture failures (2 failed / 4 passed) are retained in `v2-control-tests-initial.log`; corrected fixture definitions pass the targeted suite without removing cases.

## Failure history and limitations

- Initial B0 tests exposed the reference-label mirror; the before-fix outputs remain in `superseded-b0-before-v2/`.
- Monitor runtime tests initially had 9/11 passing due to an audit-report key error; M4 runtime tests exposed three successive test/runtime audit defects. Every initial and intermediate log is retained under `docs/results/sprint-execution-readiness/`.
- The first final verification invocation incorrectly passed a JSON filename to `verify_sprint_baselines.py --output`, which expects the prepared artifact directory. The resulting `FileNotFoundError` remains in `baseline-verification-final.log`; rerunning with `docs/results/sprint-baseline-v1` succeeded and is recorded in `baseline-verification-corrected.log`.
- The isolated readiness suite completed **48 passed**. Its exact console output is `readiness-only-tests-final.log`. A broader readiness/M3 subset was also run and is reported separately because it includes three tests blocked by missing historical M1-P0 files.
- Full repository testing is limited by absent ignored M1 raw files. These errors are not repaired by excluding tests or fabricating data. Final full-suite counts and paths are recorded in the decision after execution.
- Final full repository suite: **377 passed, 13 failed, 6 errors, 1 skipped**. All 19 failure/error outcomes are missing ignored historical run inputs, separated as follows: four M1-100 scenario/resume tests cannot read the absent `runs/m1_100/extension-75-20261019-run02` run; six M2-V3 setup errors cannot read historical M1 `researcher/T.jsonl`; six M2-V2 tests cannot read the absent M1-P0 `researcher/T.jsonl`; and three M3 tests cannot read M1-P0 `runtime-config.toml` / `full-pilot-config.toml`. The one skip is opt-in. No new readiness test was removed, and no raw source was synthesized. Exact test IDs and traces are in `pytest-full-suite-final.log`.
- The isolated mock runs do not demonstrate real model behavior, monitor accuracy, token-level server parity, causal effects, or collusion.
