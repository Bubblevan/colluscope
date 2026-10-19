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

## Static-probe no-call boundary

The static probe records `server_started=false` and `model_weights_loaded=false`. No credentials were queried. The checked-in candidate config remains default-denied. A later separately approved startup attempt is recorded below; it did load the model locally but issued no HTTP/model request.

## Bounded-preflight attempt 02: blocked before launch

The user's 2026-10-19 request authorizes the frozen local compatibility preflight only. Before launch, port 8080 was found listening on `0.0.0.0` under PID 12152, `ApplicationWebServer.exe`, associated with service `NIApplicationWebServer`; its executable path and command line were unavailable. To avoid contacting or stopping an unrelated service, no HTTP request was sent and llama-server was not started. Model completions: 0. The model and launcher hashes were rechecked; a new metadata-only identity probe confirms the selected GGUF and 53-file server bundle remain unchanged. Full raw evidence and reproduction details are in `runs/m1_p0_local/gguf-preflight-iteration-02/`. This is a blocked attempt, not a failed model-compatibility result.

## Bounded-preflight attempt 03: 8081 owner gate timed out

The user selected a separate 8081 endpoint for the bounded local preflight. A run-scoped config was created at `runs/m1_p0_local/gguf-preflight-iteration-03/configs/m1-p0-8081-preflight.toml`. Its only deltas from the default-denied local candidate are `preflight_enabled=true`, the run-scoped preflight approval ID, and the loopback URL/launch port 8081. `model_calls_enabled=false`; full-pilot and M2 approvals remain absent. The default config and all frozen prompts, rewards, conditions and samplers are unchanged.

**Exact invocation used:**

```powershell
python scripts/run_m1_p0_local_preflight.py --config runs/m1_p0_local/gguf-preflight-iteration-03/configs/m1-p0-8081-preflight.toml --out runs/m1_p0_local/gguf-preflight-iteration-03/run --approval-id USER-APPROVED-8081-PREFLIGHT-2026-10-19
```

The run loaded the frozen GGUF using the inspected `llama-server.exe` and emitted `model loaded` plus `listening on http://127.0.0.1:8081` in `run/logs/llama-server.stderr.log`. `run/launch.json` records PID 12636, executable path, and exact command. The startup gate's PowerShell PID-owner poll nevertheless observed no listener for 180 seconds and stopped only its own process. A contemporaneous independent shell query displayed `127.0.0.1:8081` owned by PID 12636; that discrepancy was captured in terminal output but the polling script did not retain per-poll snapshots in this first version. It is not evidence that the owner gate is reliable. No `/props`, `/apply-template`, `/tokenize`, or completion request was sent: 0 logical HTTP requests, 0 HTTP attempts, 0 local completions, 0 external/paid calls, and 0 research episodes. This is a runtime-attestation failure, not a model-compatibility failure.

The raw run package includes the approval/config record, environment and exact asset hashes, prompt/observation/schema inputs, server stdout/stderr, GPU samples, failure, shutdown, telemetry summary and a SHA256 manifest. The server exited with code 1 after the runner terminated its own PID. The manifest lists every package file other than itself. The run's sampled host-wide GPU values were 15,855 MiB free before startup, 10,395 MiB while the server was running, and 15,533 MiB after shutdown. The process was not attributed to those GPU samples, and the sampler mislabeled live samples as `prelaunch`; no GPU-fit conclusion is supported.

**Counterexample history:**

- The first full-suite run had 6 local HTTP tests fail with Windows `WinError 10013`, 129 passed. The terminal excerpt is retained at `runs/m1_p0_local/gguf-preflight-iteration-03/logs/initial-loopback-suite-failure-excerpt.txt`. The same HTTP module then returned 7 passed, and the full suite returned 135 passed; no test was removed.
- The first proposed in-process `GetExtendedTcpTable` owner check failed with `ERROR_ACCESS_DENIED` (`[Errno 5]`); the failure is recorded at `logs/listener-owner-api-failure.txt`.
- A `netstat -ano` child-process canary first returned no owner row for its live child listener, then a later isolated rerun passed. Both records remain in `logs/`; the first failure is a counterexample and the later pass does not erase it.
- The final offline suite returned 136 passed in 10.82s (`logs/offline-suite-final.log`). A green suite does not resolve the live owner-attestation discrepancy. The script source was changed after attempt 03; the package's `environment.json` records the Git HEAD but does not hash the exact dirty runner source used at launch. Therefore the attempt itself is not byte-for-byte replayable from its manifest.

The **current post-attempt** runner file SHA256 is `924581c540ca77dd85aa4efa1afd264a6e429bcb0416422b73a7fbd697027d34`; this identifies the checked-in candidate after later owner-probe changes and is not claimed as the source hash used in attempt 03. The run-package `manifest.json` SHA256 is `3f1d0f85e28865dc9cc495916f302f21a10fb95b36a9454f8e1fd634b7759ef2`; the approved config SHA256 is `2210db1f9d2a9948bf2fbb4fafc3d630075345784b10599b556d99c1e77b5ee6`.

**Current decision:** NO-GO for claiming a successful live preflight. Do not rerun the model startup until the PID-owner check is stable under the runner's own child-process canary, per-poll evidence and source fingerprint are recorded before launch, and phase labels are correct. The 25-episode Pilot and M2 remain unauthorized.

**Manifest verification for the run package:**

```powershell
$run = (Resolve-Path 'runs/m1_p0_local/gguf-preflight-iteration-03/run').Path
$manifest = Get-Content (Join-Path $run 'manifest.json') -Raw | ConvertFrom-Json
$entries = @($manifest.files.PSObject.Properties | Where-Object MemberType -eq 'NoteProperty')
foreach ($entry in $entries) {
    $path = Join-Path $run $entry.Name
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $entry.Value.sha256) { throw "SHA256 mismatch: $($entry.Name)" }
}
"Verified $($entries.Count) files"
```
