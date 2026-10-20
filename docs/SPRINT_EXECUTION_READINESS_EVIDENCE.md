# Sprint Execution Readiness Evidence

**Run date:** 2026-10-20 (Asia/Shanghai)
**Scope:** offline artifact replay, deterministic/mock runtimes, local identity inspection, and the dated M4 v2 local tokenizer/template parity diagnostic below.
**Model generations / completion calls:** 0. **External inference calls:** 0. The complete 96-prompt token-only run used one server launch; earlier failed owner-detection/controller attempts are retained separately and some loaded the server without issuing HTTP requests.

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

### Positive-control v2 follow-up

The v1 failure is preserved. A separate candidate config changes only `XXXX` to `NONE` (`configs/m4-positive-control-v2.json`); both strings are four characters, and `NONE` is not mapped to either task action. `scripts/verify_m4_token_matching.py` uses the exact rendered system/user prompts, embedded GGUF tokenizer and frozen chat template to reproduce the old 0/24 match and test all 24 v2 groups. Result: v1 **0/24** (183 information vs 184 neutral tokens), v2 **24/24** (183 vs 183). Test result: **2 passed**, including the exact local GGUF integration gate. Receipt: `docs/results/sprint-execution-readiness/m4-positive-control-v2-token-match.json`; test log: `m4-token-match-tests-final.log`.

This is not a live server parity result. It does not modify v1 or wire the candidate into the frozen v1 runtime. It establishes only that the prospective v2 positive-control pair has equal local-tokenizer prompt lengths. The separate focal Proposal/Neutral difference persists; overall M4 remains NO-GO for real inference.

### M4 v2 candidate: live llama.cpp template/token-ID parity (2026-10-20)

This bounded diagnostic loaded the already-frozen local Qwen3-8B Q4_K_M GGUF in llama.cpp build 10068, bound only to `127.0.0.1:8081`, disabled warmup and used `--offline`. It did **not** call any generation/completion endpoint. All prompts came from the versioned deterministic Mock run `runs/m4/offline-mock-v3-candidate`; this is a fixed-stimulus compatibility check, not an Agent behavior run.

| Pair / endpoint comparison | Result |
|---|---:|
| Positive-control v1 information vs `XXXX` neutral, local GGUF tokenizer | 0/24 exact; 183 vs 184 tokens (the prior failure is reproduced) |
| Positive-control v2 information vs `NONE` neutral, local GGUF tokenizer | 24/24 exact; 183 vs 183 tokens |
| Focal Proposal vs v2 retained-history neutral, local GGUF tokenizer | 24/24 exact; family-specific pairs 528/528, 529/529, 530/530, and 533/533 |
| Server-rendered prompts equal the frozen local chat-template strings | 96/96 exact |
| llama.cpp server token-ID arrays equal the frozen local GGUF arrays | 96/96 exact |
| Local HTTP accounting | 192 started / 192 terminal / 192 HTTP 200; 96 `/apply-template` + 96 `/tokenize`; zero other routes |
| Server ownership and cleanup | 192 pre-request exact-owner checks plus 2 startup polls; post-run exact PID absent, no port-8081 listener, temporary API key absent |

The local v1-to-v2 audit and server receipt record the frozen model SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`, llama-server SHA-256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`, runtime bundle SHA-256 `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759`, tokenizer SHA-256 `06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f`, and chat-template SHA-256 `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361`. The exact request/response ledger SHA-256 is in the machine-readable independent receipt.

**Preserved runner failure:** after all 192 successful HTTP responses and normal server/key cleanup, Windows PowerShell 5.1 raised `ArgumentException: Argument types do not match` while constructing the final report's inline `if` value (`scripts/verify_m4_llama_token_parity.ps1`, line 321 in the run). The unhandled error and cleanup observations remain in the ignored local run directory. The independent auditor then compared all 96 raw template and tokenization responses against the frozen input manifest and verified all response-body hashes. The report writer was repaired by precomputing PowerShell arrays and scalar fields outside the ordered hashtable; parser and report-shape smoke checks passed. The 192-request run was not repeated, so the receipt status is explicitly `PASS_LLAMA_SERVER_TOKENIZER_PARITY_INDEPENDENT_REPLAY_RECOVERED`, not a runner-reported pass.

This GO is narrow. M4 v2's fixed positive-control stimuli and fixed Mock focal stimuli now have exact local-server parity. Natural LLM-generated proposal text has not been generated or checked, so the focal token-count equality is not guaranteed for a future real Agent run. `NONE` remains an explicit no-valid-signal marker, not a no-message condition. No behavioral result, information-use result, collusion label, Monitor result, or permission to start the 264-generation pilot follows from this diagnostic.

Committed sanitized receipts: `m4-v2-token-match-audit.json`, `m4-v2-server-tokenizer-parity-audit.json`, `m4-v2-mock-audit.json`, and `m4-v2-token-parity-runner-failure-history.json`. Captured command output is in `m4-v2-targeted-tests-final.log`, `m4-v2-local-token-audit.log`, `m4-v2-mock-audit.log`, `m4-v2-server-parity-audit.log`, and `m4-v2-finalizer-smoke.log`. Raw prompts, private Mock observations, response bodies, and the API key file (now removed) were not committed. The raw run tree remains ignored and ACL-restricted.

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
