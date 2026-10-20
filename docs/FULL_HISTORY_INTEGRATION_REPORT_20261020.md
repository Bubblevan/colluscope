# Full-History Integration Test Report — 2026-10-20

## Result

The current checkout passed the full offline repository suite with historical M1 inputs restored:

- **404 passed, 0 failed, 0 errors, 0 skipped** in 74.17 seconds.
- Exit code: `0`.
- Tested code commit: `42ba9698f47b5c4d7b80862ed880029887061444`.
- Environment: Windows `10.0.26200.0`, Python `3.12.4`, pytest `9.1.1`.

The M4-focused runtime, scenario, and token-matching suite also passed: **20 passed**. That focused suite is included in the full-suite count and must not be added to it.

## Historical inputs and integrity

The test checkout initially lacked the real historical run directories because Git ignores them. The data were available in the local reference clone `reference/m1-p0-local-qwen-integration` at source commit `e9d8b57c679815776fb64e1c806a71484f51c155`.

Two complete data trees were copied byte-for-byte into the ignored paths expected by the current integration tests:

| Dataset | Files | Bytes | Local destination |
|---|---:|---:|---|
| Formal M1-P0 25-episode run | 34 | 1,360,644 | `runs/m1_p0_local/formal-25ep-pilot-20261019/run` |
| M1-100 extension run | 152 | 7,074,901 | `runs/m1_100/extension-75-20261019-run02` |
| **Total** | **186** | **8,435,545** | |

After testing, each source and local-copy file was independently SHA256 checked against the pre-copy manifest: **372 checks, zero mismatches**. The source clone commit remained unchanged. These raw directories stay local and Git-ignored; no private message text, model response, prompt, or raw run file was staged.

Evidence files:

- `docs/results/full-history-integration-20261020/history-source-manifest.json` — source commit and per-file path/size/hash manifest.
- `docs/results/full-history-integration-20261020/history-integrity-check.json` — post-test source and copy verification.
- `docs/results/full-history-integration-20261020/pytest-log-hashes.json` — hashes and sizes for the exact raw pytest outputs.
- `docs/results/full-history-integration-20261020/environment.txt` — Python, pytest, OS, and pre-restore path checks.
- `docs/results/full-history-integration-20261020/full-history-run-context.txt` — tested code commit and history source commit.

## Preserved initial failure and recovery

Before restoring history, the same full test command returned **384 passed, 13 failed, 6 errors, 1 skipped**. Those 19 failure/error outcomes were caused by absent ignored run inputs. Exact raw outputs remain byte-preserved under `runs/m1_p0_local/integration-test-evidence-20261020/` and are covered by the committed log-hash manifest.

After exact data restoration, the first full run returned **403 passed, 1 skipped**; the only skip was an opt-in Windows listener-owner integration check. That check passed when run alone. A final full-suite run with it enabled returned 404 passed. Outputs:

- `runs/m1_p0_local/integration-test-evidence-20261020/pytest-full-with-history.log`
- `runs/m1_p0_local/integration-test-evidence-20261020/pytest-windows-listener-integration.log`
- `runs/m1_p0_local/integration-test-evidence-20261020/pytest-full-with-history-and-listener.log`
- `runs/m1_p0_local/integration-test-evidence-20261020/pytest-m4-focused.log`

No failed tests were removed, skipped, or relabeled to obtain the final result.

## Reproduction

From the repository root, after restoring the two ignored source trees from the stated reference commit and confirming `history-integrity-check.json` reports `PASS`:

```powershell
python -m pytest -q
```

To enable the Windows-only listener-owner integration test in the same full run:

```powershell
$env:COLLUSCOPE_LIVE_WINDOWS_LISTENER_TEST = '1'
python -m pytest -q
Remove-Item Env:COLLUSCOPE_LIVE_WINDOWS_LISTENER_TEST
```

The opt-in test briefly launches Python's standard-library HTTP server at `127.0.0.1:8081` and checks the listener PID. It does not call llama.cpp, a model, or an external API. The test suite made **zero real model inference or external API calls**.

## Decision boundary

**GO:** current offline integration tests pass against the complete historical M1-P0/M1-100 inputs available in the local reference clone.

**Not established:** this test result does not authorize or validate new LLM inference, an M4 behavioral experiment, a monitor evaluation, or a collusion detector. It does not strengthen the behavioral or causal claims in the historical research.
