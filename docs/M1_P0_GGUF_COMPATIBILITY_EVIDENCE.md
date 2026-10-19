# M1-P0 GGUF Compatibility Evidence

**Evidence class:** static identity, offline unit/fake-HTTP checks, deterministic M0/M1-R scripted artifacts.
**Not evidence of:** real LLM behavior, server/model compatibility, collusion, detector performance, or GPU load fit.

## Environment and selected checkpoint

The frozen Qwen3-8B Q4_K_M checkpoint at `E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf` was re-read and rehashed. Observed facts: 5,027,783,488 bytes; SHA256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`; GGUF v3; 399 tensors; 28 metadata entries. The read-only metadata parser does not parse tensor descriptors or load weight data. Token arrays contain 151,936 entries, merges 151,387; the embedded chat template is 4,100 UTF-8 bytes.

Static tokenizer construction succeeded with Python 3.12.4, `tokenizers==0.19.1`, and `jinja2==3.1.4`. Embedded tokenizer identity: `06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f`; chat-template SHA256 `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361`. A local synthetic system/user prompt rendered and counted as 30 tokens. This is only the Python implementation's result; server parity is unverified.

Installed `llama-server.exe`: version 10068, commit `571d0d540`, Clang 20.1.8; launcher SHA256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`. Its directory contained 53 regular runtime files; combined deterministic bundle SHA256 `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759`. Static device enumeration listed `Vulkan1: NVIDIA GeForce RTX 4090 Laptop GPU`; no model was loaded. The two enumerators reported different memory totals; neither is a model-fit measurement.

The complete output is `runs/m1_p0_local/gguf-iteration-01/static-identity-inventory-final.json`; rerun with:

```powershell
$env:PYTHONPATH = 'src'
python scripts/inspect_local_gguf.py --config configs/m1-p0-llama-local-draft.toml --out runs/m1_p0_local/gguf-iteration-01/static-identity-inventory-reproduced.json
```

The script verifies the configured GGUF size/hash, selected tokenizer/template identities, launcher hash, complete runtime-bundle hash, version probe, and GPU target. It invokes only `llama-server.exe --version` and `--list-devices`; it does not start a server or load a model.

The source/config/prompt/test snapshot contains 33 files and has aggregate SHA256 `cefd5f0f15f28a2e1485e03d497388da22448b227d4d0a6d29b0eaead6e707bf`; the complete generated evidence package contains 84 files and has aggregate SHA256 `ad9ceec40388269ddbd15daa597a206fb759b9710713610e1ef590788b590ecf`. File-by-file hashes are in `source-snapshot.json` and `artifact-manifest.json`. The source snapshot is based on commit `1b36a6de6c8def8cee323a79e239e0e9dd60b37a`; it records that the worktree was dirty while outputs were generated, with each source file hash included.

## Official interface check

The exact inspected upstream source is [llama.cpp server documentation at commit `571d0d540`](https://github.com/ggml-org/llama.cpp/blob/571d0d540/tools/server/README.md). It documents a direct `response_format` schema field for JSON-schema output, `chat_template_kwargs`, `reasoning_format=none`, `/props`, `/apply-template`, and `/tokenize`. The pinned server source also exposes the routes and describes the relevant settings in [`server.cpp`](https://github.com/ggml-org/llama.cpp/blob/571d0d540/tools/server/server.cpp) and [`server-context.cpp`](https://github.com/ggml-org/llama.cpp/blob/571d0d540/tools/server/server-context.cpp).

These docs validate the proposed request shape, not the model-specific `oneOf` behavior. No actual server request was made, and the fake HTTP test cannot establish grammar acceptance, tokenizer parity, reasoning-mode behavior, or model revision from the server process.

## Offline tests and deterministic artifacts

| Check | Result | Raw evidence |
|---|---:|---|
| Full repository pytest suite | 128 passed in 12.75s | `pytest-full-delivery-final.log` |
| GGUF metadata/tokenizer/fake adapter tests | 26 passed in 0.29s | `pytest-gguf-focused-final.log` |
| M0 generation | 24 scripted episodes, 4 per C1–C6, four identical C1/C6 evidence pairs; no detection score claimed | `m0-reproduction-final/m0-20261019T035712Z/` and `m0-generation-final.log` |
| Independent M0 verification | PASS; all four views recomputed, oracle kept outside monitor input, file hashes checked | `m0-independent-verification-final.log` |
| M1-R deterministic Mock | 25 episodes (5 per frozen condition); 95 logical Mock requests, 95 attempts, 190 hard ceiling; settlement independently recomputed | `m1r-reproduction-final/` and `m1r-independent-verification-final.log` |
| Isolation/failure canaries | 11 traces and 18 checks PASS; all are runtime-plumbing tests | `m1r-canaries-final/` and `m1r-canary-generation-final.log` |
| llama.cpp adapter contract | fake opener only; direct schema shape, role mapping, local-only guard, timeout/retry, malformed outputs, usage/model drift, preflight caps, runtime bundle drift, and 95/190 backend ceilings | `tests/test_openai_compat_llamacpp.py` and focused pytest log |

The M0/M1-R scripted and Mock artifacts are not real LLM samples. They are not used as behavioral evidence or as labels for detector evaluation.

## Retained first-round failures

No failing result was deleted. `initial-failures.md` preserves the observed unit-test failures and the corresponding narrow fixes. The first adapter run exposed four issues (test fixture identity; parser versus adapter failure boundary; an incorrect endpoint error assertion; and missing tokenizer metadata on the preflight object). Later runs exposed path assertion and test-fixture mistakes; they were corrected without removing test cases. A preflight template-mismatch counterexample exposed that a validation error was not itself recorded as failed; the adapter now appends a failure record retaining the last raw response.

## Hard no-call boundary

The static probe records `server_started=false`, `model_weights_loaded=false`, `generation_calls=0`, `network_requests=0`, and `paid_api_calls=0`. No credentials were queried. No preflight, real model call, 25-episode real pilot, or M2 detector comparison ran. The candidate config remains default-denied.
