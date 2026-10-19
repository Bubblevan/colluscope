# M2 One-shot Execution Evidence

**Disposition:** the authorized local execution and independent integrity audit completed. The monitor produced **zero valid predictions**, so this is a failed output-interface pilot and does not support detector-performance or collusion claims.

## Authorization and frozen source

- User authorization: `USER-AUTHORIZED-M2-ONE-SHOT-2026-10-19`.
- Authorization attachment SHA-256: `c123839027ebba86cb7a2d29c12fbdf9f4ab3cccb5405a731f330a107554d8ed`.
- Frozen protocol: `colluscope-m2-one-shot-v1`; protocol document SHA-256 `36748d37b25c0f9679c92c4bfc4cfcda01abee6e3b088769ca7e04537d2235cb`.
- Final pre-inference source commit: `e26bbd6734cc774d6675bd17f742f742987f61b4`.
- Revision-2 freeze manifest SHA-256: `5078b990b2690fc5b5f2d050b993b8458683065a5474e2b6c44393b0e9d55428` (29 bound source/config/prompt/test artifacts).
- M1 source manifest SHA-256: `4e7868449a5e2bc3621fef4da4eaded4d710c15570dbf12f7d4ab215f3a4bb13`; source hashes were independently rechecked and remained unchanged.

The 100 source episodes retain their provenance: 25 historical F0 episodes and 75 prospective M1-100 episodes in F1/F2/F3. The split unit is the matched scenario/seed group. F0 is descriptive; F1 is calibration; F2/F3 were not requested until the calibration closure was written. Prior reports had already exposed F2/F3 outcomes, so they are exploratory holdouts rather than pristine confirmatory data.

## Frozen local runtime

| Item | Frozen identity |
|---|---|
| Model | Qwen3-8B Q4_K_M GGUF, `E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf` |
| Model SHA-256 | `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` |
| llama.cpp server | `C:\Users\bubblevan\AppData\Local\Microsoft\WinGet\Packages\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-server.exe`, build `b10068-571d0d540`, SHA-256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb` |
| Runtime bundle SHA-256 | `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759` |
| Endpoint | authenticated `http://127.0.0.1:8081/v1/chat/completions` |
| Tokenizer SHA-256 | `06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f` |
| Chat-template SHA-256 | `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361` |
| Sampling | temperature 0, top-p 1, top-k 0, min-p 0; reasoning disabled; context 4096 |
| Token bounds | 3072 input / 512 output; 60-second timeout |

No external model endpoint or provider fallback was configured; recorded model requests all used the local loopback endpoint. This does not claim host-wide network isolation. Recorded paid API spend was $0.

## Assigned evaluations, calls, and terminal outcomes

| Phase | Partitions | Logical evaluations | Unique payloads | HTTP attempts | Returned model responses | Terminal transport failures |
|---|---|---:|---:|---:|---:|---:|
| Calibration | F0 + F1 | 500 | 246 | 248 | 244 | 2 unique requests |
| Held-out | F2 + F3 | 500 | 277 | 281 | 273 | 4 unique requests |
| **Total** | F0–F3 | **1,000** | **523** | **529** | **517** | **6 unique requests** |

The 523 unique payloads represent 477 exact in-scope duplicate logical evaluations. The six failed unique requests each exhausted the frozen two-attempt transport policy, accounting for 12 physical attempts without a response. Every assigned evaluation has a terminal record: **980 invalid-output evaluations, 20 request-failed evaluations, zero valid predictions**. No invalid or unfavorable response was replaced. The 1,000 logical / 2,000 physical caps were not approached, and no unique request exceeded two attempts.

The independent call audit returned `PASS_M2_INDEPENDENT_CALL_AND_ARTIFACT_AUDIT`: 1,000/1,000 terminal evaluations, 523 prepared unique payloads, 529 recorded HTTP attempts, 517 response files, zero valid outputs, all request URLs on loopback, no external fallback, and $0 spend. It independently verified request-body hashes, response hashes, model/server/runtime identity, listener PID, phase order, retry bounds, and API-key cleanup.

## Preparation and privacy checks

The repaired no-call preparation produced exactly 1,000 unique `(episode, permission, view)` evaluation keys, 523 exact payloads, 477 deduplicated logical rows, and zero inputs over the token cap. The independent preparation verifier returned `PASS_M2_PREPARATION_PERMISSION_AND_HASH_AUDIT`, including:

- all 1,000 evidence inputs checked against source T/B/Public E;
- no hidden treatment/oracle metadata in monitor input;
- no cross-permission or cross-split payload reuse;
- unchanged Public E source bytes;
- current-user-only ACL verified on the run root and all six child directories;
- zero model calls during preparation.

The final local artifact inventory contains 1,450 files (excluding its own manifest); `runs/m2/one-shot-20261019/artifact-hashes.json` SHA-256 is `6d3f0d552aea565d80416a774d80e64710488318da274ef2053841f140d984b9`. The run tree is Git-ignored and local. Private message text and raw monitor responses were not committed or copied into these public reports.

## Failures retained

1. **Pre-inference schedule failure:** the first preparation attempt double-appended `structured_without_findings` and failed the 1,000-key invariant. The original freeze manifest, traceback, exit code, and a zero-request failure summary remain in `runs/m2/one-shot-20261019/stage1/`. A tested schedule helper removed the duplicate; the five views and all study settings stayed unchanged. The post-repair full test suite passed **226 tests, 1 skipped**.
2. **Pre-HTTP held-out launch failure:** the frozen runner counted `launch-*.json` files rather than `launch-*` directories and tried to recreate `launch-001`. The attempt exited before HTTP. To run the already-frozen held-out phase without changing frozen source, a temporary counter marker caused it to create `launch-002`; the marker was removed before audit. The traceback, zero-call accounting, and phase logs remain in `stage1/`.
3. **Output-contract failure:** all 517 returned completions were classified by the frozen validator as `invalid_output:json_parse_error:JSONDecodeError`. The post-hoc formatting diagnostic is explicitly non-authoritative and did not alter statuses or denominators; details are in `M2_BAD_CASE_AUDIT.md` and the local `stage1/posthoc-format-validation-diagnostic.json`.

## Reproduction commands

Run from the repository root after restoring the exact local M1 artifacts, GGUF, server, tokenizer, and runtime bundle:

```powershell
python scripts/freeze_m2_protocol.py --check
python -m pytest -q
python scripts/run_m2_monitor.py --prepare
python scripts/verify_m2_preparation.py --run runs/m2/one-shot-20261019
python scripts/run_m2_monitor.py --phase calibration
python scripts/freeze_m2_calibration.py --run runs/m2/one-shot-20261019
```

For the held-out run, this frozen runner needs a temporary launch-counter marker because of the documented directory-count defect. The actual run used:

```powershell
$marker = 'runs/m2/one-shot-20261019/launches/launch-001.json'
'{"purpose":"temporary-launch-number-counter-marker","not_a_launch_record":true,"remove_before_audit":true}' | Set-Content -Encoding utf8 -LiteralPath $marker
python scripts/run_m2_monitor.py --phase held_out --resume
Remove-Item -LiteralPath $marker -Force
```

Then run the independent scorer and auditor:

```powershell
python scripts/score_m2_monitor.py --run runs/m2/one-shot-20261019
python scripts/audit_m2_outputs.py --run runs/m2/one-shot-20261019
```

The historical command outputs and exit codes are in the local `stage1/` directory; the request/response ledgers and raw payloads remain in the ACL-restricted run directory. These commands document this completed run and must not be used to replace terminal outputs.
