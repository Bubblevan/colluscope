# ColluScope M1-100 Evidence Package

**Run date:** 2026-10-19 (Asia/Shanghai)  
**Status:** 75 prospective episodes completed; 25 historical episodes independently rechecked; core raw-ballot audit passes with 19 explicitly disclosed stored harm-flag disagreements.  
**No M2 inference, training, or new model call was run.**

## Corpus and provenance

The corpus contains 100 episodes in two provenance strata. F0 contains the historical 25-episode M1-P0 pilot and is descriptive/development evidence only. F1 contains 25 new episodes for calibration. F2 and F3 contain 25 new episodes each for held-out group evaluation. The extension is prospective and was not generated under the original 25-episode protocol.

The 75 new assignments comprise 15 scenario/seed matched groups, each with all five intervention conditions. The three scenario families appear in all three new partitions, so F2/F3 hold out groups, **not unseen payoff families**. All five condition rows and their derived views remain with their matched group.

The F0 rows in the frozen M1-100 split manifest were inconsistent with the historical T records: the split file used the alias `icbcmatch_v1` and synthetic group IDs, while the immutable historical records identify `allocation-3agent-v1`. The original split file remains byte-identical. A separately versioned post-run correction preserves the historical alias and reconciles only F0 against the original T rows. It does not change F1-F3 assignments, treatments, prompts, model outputs, or labels.

## Execution counts

| Measure | Result |
|---|---:|
| New episodes assigned | 75 |
| New episodes completed | 75 |
| New episodes failed | 0 |
| New parser/action failures | 0 |
| Historical episodes changed or rerun | 0 |
| New ballot requests | 225 |
| New communication requests | 60 |
| New logical requests / returned model completions | 285 / 285 |
| Physical HTTP attempts | 285 |
| Retries | 0 |
| Paid or external model calls recorded | 0 |
| Combined historical + prospective corpus | 100 episodes; 380 episode-generation completions |

The 60 communication requests are the two message-stage requests in each of 30 chat-available episodes, including valid `no_message` actions. The 15 no-chat episodes had no communication request. The new run used 285/285 logical-request capacity and 285/570 physical-attempt capacity. Every logical request succeeded on its first attempt.

Usage was 137,034 prompt tokens, 10,714 completion tokens, and 147,748 total tokens. Median request latency was 0.944 seconds; median episode wall time was 3.260 seconds, with 287.835 seconds summed across 75 episode durations. The GPU sampler recorded 294 samples; peak used memory was 6,332 MiB and minimum free memory was 10,044 MiB on an NVIDIA GeForce RTX 4090 Laptop GPU.

## Frozen identities

| Item | Identity |
|---|---|
| Pre-response source commit | `d9a313732e86b34d301e8e090c8f910f8238b1c0` |
| Model | `E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf`; SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` |
| llama.cpp server | SHA-256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb` |
| Runtime bundle | SHA-256 `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759` |
| Tokenizer | SHA-256 `06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f` |
| Chat template | SHA-256 `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361` |
| Sampling | temperature 0; top-p 1; top-k 0; min-p 0 |
| Endpoint | authenticated local loopback `127.0.0.1:8081`; offline llama.cpp; no third-party fallback |
| Python / OS | Python 3.12.4; Windows 11 |

All 285 responses are recorded against the local authenticated endpoint and exact request/response hashes. The runtime used its offline mode and no external model fallback. No host-wide egress firewall rule was added, so this evidence supports “no external model calls recorded and all model requests addressed to the frozen local endpoint,” not a claim that the host had network egress disabled at the OS level.

## Independent verification

The standard-library independent auditor reconstructs all 75 settlements from raw ballots and the selected scenario matrix. It independently recomputes the six-permutation optimum, plurality and chair rule, public welfare, regret, bonuses, individual task quality, realized scores, target execution, message delivery, observation hashes, request links, generation seeds, monitor permissions, split membership, endpoint/runtime identity, and historical artifact hashes.

The final result is `PASS_CORE_RECOMPUTE_WITH_STORED_HARM_FLAG_MISMATCHES`: all 75 new settlements and all 25 historical settlements were rechecked; 75/75 new episodes are terminal; 285/285 request responses are accounted for; hidden treatment metadata and private message text are absent from Public E. The 19 stored `harmful_outcome` boolean disagreements are individually listed and do not replace the authoritative scenario-specific recomputation.

Public E has 75 episode index references to 51 unique, byte-identical payload rows. The runtime de-duplicates consecutive identical E payloads. The audit verified every index/hash and found all 24 repeated references confined to their original matched group; none cross a partition. There are 375 public event references (five events per completed episode) and zero private message events in Public E.

## Key artifact hashes

Run directory: `runs/m1_100/extension-75-20261019-run02/`.

| Artifact | SHA-256 |
|---|---|
| Frozen run config | `f4bdc56254785b82e2d0a03748e65a49cf096b6e8602c1eec0d8786316277bad` |
| Scenario definitions | `08c7592b09289174e5413b265c95756a03df226259411b3a8ecfb4a7eb7ac625` |
| Original frozen split manifest | `8ebc47258ea3cfc7295e65242ddec8aee005ed5c59545edf1cc5bd1e40f1e159` |
| Post-run F0 correction | `e705a6dd55b31a53043b8cf7b99c5aae1ffc24d0d10798331154e74a35d7026e` |
| Frozen protocol | `8c64c562aae0c39d8bf45ef6858a0618068dadf5e8a747b97dd962c42accfcc4` |
| Assignment schedule | `b3c8a223dd8f1c5cfee25a997fc23e4460c6dc6d244c87f4b5879d9eb1bfde0b` |
| New T | `8b87aac873f403909b34b9a94fc13a2f7924968e370f320bbb293d53cef2cafb` |
| New B | `4d176ceb4d49abe60cde1a0159e1de21b3f603ac7f264b23bc544f3e686dfc87` |
| New Public E | `4fd2e03d77e18a6e2f5dbbd5c3571670c3590a58d58ddb4c691f4b9b482b8df3` |
| Per-episode E index | `257a47057da95a6e82ee1a5ce0f4b79dc9a61f412f92e7993cf45a34d0b69935` |
| Request/response records | `803e15a2bfaa10baa467b053d7bf3b3c99d9a3c0b150e490a91b88878c07680e` |
| Attempt-start ledger | `c7f143ae22e4b7cda1fe37ac2eb092b10f606facd879f8234227a0116f301ce6` |
| HTTP-attempt ledger | `7bad0374b56d70fa2fbff493f1526d646d2bdc5b8b302712010d8418a7e08a07` |
| Agent observations | `2bd6afd06e62222f993a2a5afab86b9ff49c273c1797c35e0f728bc835525825` |
| Progress ledger | `4c6afa20b6f550f5229c377dbb9e1588b52308478e5ea494507c1f289d9872b2` |
| GPU samples | `de866a6249ef61ab10b5b9b944284f7aa6289c4bb3361c5e7666be49d5f25b8e` |
| Full local corpus manifest | `4e7868449a5e2bc3621fef4da4eaded4d710c15570dbf12f7d4ab215f3a4bb13` |
| Final verification record | `607a8d913eeca2f0c9cb226b4eac7a18537574dd6bf2bc9a4f2dddde34dbd5db` |

Historical T/B/E remain at their original hashes: `30c397583618cbed20fa529cf4ac39e69caca43456d09abbddb25b1f6e888464`, `139c1bc09891276763223677ee88de6e45bdcee80a348fb64d2258b666b3014a`, and `90c962e43b9ea10e115c40d624effc307b9dc2994703e916947cc38d6155adef` respectively.

## Failure history retained

No failed or unfavorable episode was removed or replaced. Two pre-dispatch engineering failures consumed zero model calls: the first output path lacked a source-copy directory; the second run was stopped by a one-character server SHA pin mismatch before launch. The assigned schedule was preserved and the second run used the versioned pre-response revision. The independent audit then retained three failures: F0 group metadata mismatch (`audit-failure.json`, SHA-256 `dd4c6f5b77e91ba9d2cd05aae0835024010c9140e3b28276d5ae2d6582eb793e`); Public E deduplication cardinality expectation (`audit-failure-attempt-002.json`, `eb23fcedb91861ee0992f0ca5275339bc55e1c1209d40ef077ec41218258bab2`); and 19 incorrect stored harm booleans (`audit-failure-attempt-003.json`, `eaf786dbd345166284fc93cc7b90cff69486c1048f11e2932515f6dff611c8cf`). All corrections are post-run auditor/runtime-code revisions; none altered the model intervention or run data. The five revision records are under `frozen_protocol/postrun-audit-revision*.json`.

## Reproduction commands

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python scripts/freeze_m1_100_design.py --check
python -m pytest -q
python scripts/audit_m1_100.py --run runs/m1_100/extension-75-20261019-run02
```

The final full-suite output is preserved at `runs/m1_100/extension-75-20261019-run02/engineering/pytest-full-final-iteration-05.log` (**212 passed, 1 skipped**; the skip is the opt-in Windows owner-table integration test). The audit was run twice after final code freeze; both runs returned the same corpus-manifest hash and left T/B/E, requests, and all three audit failures unchanged.

The generation invocation was `python scripts/run_m1_100_extension.py --out runs/m1_100/extension-75-20261019-run02 --resume` at source commit `d9a313732e86b34d301e8e090c8f910f8238b1c0`; it reached all 75 terminal episodes. The completed run must not be regenerated. Raw private message text and full request records remain local under the run directory and are not committed or published by this evidence document.
