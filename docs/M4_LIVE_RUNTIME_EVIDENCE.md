# M4 Live Runtime v3 — Offline Evidence

**Scope:** implementation and offline validation only. This record contains no new Agent generation, Monitor inference, model training, or external API call. Fake-server replies are fixtures, not model observations.

**Base commit:** `95cd6b5c5c0cc05ebf14a1be04052501b0602ad1`
**Topic branch:** `codex/final-sprint-execution-candidate-20261020`

## Identity receipt

`docs/results/final-sprint-candidate/runtime-identities.json` records the local host and Python version, reviewed configuration hashes, schedule sizes, and frozen asset verification. The observed environment was Windows 11 build 26200, Python 3.12.4, tokenizers 0.19.1, and Jinja2 3.1.4.

| Asset | SHA-256 |
|---|---|
| Qwen3-8B Q4_K_M GGUF | `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` |
| llama.cpp b10068 binary | `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb` |
| llama.cpp runtime bundle | `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759` |
| Embedded GGUF tokenizer | `06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f` |
| Chat template | `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361` |
| M4 v3 runtime config | `dccc96a68c09618c86e30427b0c8d22ce17170c59822720d1e079a0cf97f422a` |
| Sprint Monitor runtime config | `d6c41d412dc9b298e778ac6aa041668bd219dfff4ab15bba77e0d98f5b3ec079` |

The local files matched the checked-in freeze. This verifies artifact identity; it does not verify future server startup or model behavior.

`docs/results/final-sprint-candidate/candidate-artifact-sha256.json` inventories the candidate source, frozen inputs, reports, test logs, and retained failure records. The manifest excludes its own hash to avoid self-reference.

## Executed checks

| Check | Result | Scope |
|---|---|---|
| M4 live-runtime and Monitor-runtime focused suite | **54 passed in 146.14s** | Final post-fix run; fake HTTP / injected fake transport, parser, ledgers, gates and replay; no generated model output |
| Full repository suite with restored ignored historical data and host listener canary enabled | **447 passed in 227.19s** | Latest full-history integration on this Windows host |
| Full portable offline suite without the opt-in host listener canary | **446 passed, 1 skipped in 216.22s** | The skipped check is the explicitly opt-in host listener ownership canary |
| Redirect credential-isolation regression | **1 passed in 1.06s** after retaining the original fixture failure | Actual loopback HTTP; 302 does not reach credential sink |
| Sprint baseline artifact verifier | **PASS_OFFLINE_ARTIFACT_REPLAY_ONLY** | 8 scripted cases, 280 reference and scheduled rows, 21 historical source hashes; zero dispatch and model calls |
| Frozen M4 assets | **Verified** | File hashes and tokenizer/template metadata only |
| M4 v2 fixed-stimulus server/tokenizer parity | **Previously completed; not repeated** | Historical 192-request token/template diagnostic, zero generation requests |
| Monitor provider dispatch | **Not run** | 280-row schedule remains unexecuted |
| M4 Agent generations | **Not run** | 24 groups remain unexecuted in this task |

The full-history integration run used ignored local M1-P0/M2/M3 artifacts restored on this workstation; none of their raw content was added to Git. The portable run intentionally does not enable `COLLUSCOPE_LIVE_WINDOWS_LISTENER_TEST`; its one host-specific skip is reported as a skip, not a pass. Both exact raw pytest outputs are retained beside this document. The first portable run failed at the redirect security test because its fake handler did not consume the POST body; the failure is retained and classified in `failure-history-initial-20261020.md` and `pytest-portable-offline-failure-01.log`. After correcting only the fixture, the focused redirect test passed and both full runs passed. The exact focused and deterministic verifier outputs are `pytest-redirect-focused-final.log` and `baseline-verification.log`.

### Reproduction commands (PowerShell)

```powershell
$env:PYTHONPATH = 'src'
python -m pytest -q tests/test_m4_live_runtime.py tests/test_sprint_monitor_runtime.py
```

Full-history integration, including the host listener ownership canary:

```powershell
$env:PYTHONPATH = 'src'
$env:COLLUSCOPE_LIVE_WINDOWS_LISTENER_TEST = '1'
python -m pytest -q
Remove-Item Env:COLLUSCOPE_LIVE_WINDOWS_LISTENER_TEST
```

Portable offline suite:

```powershell
$env:PYTHONPATH = 'src'
Remove-Item Env:COLLUSCOPE_LIVE_WINDOWS_LISTENER_TEST -ErrorAction SilentlyContinue
python -m pytest -q
```

Frozen identity verification and CLI surfaces:

```powershell
$env:PYTHONPATH = 'src'
python scripts/run_m4_live.py --help
python scripts/audit_m4_live.py --help
python scripts/run_sprint_monitor.py --help
python scripts/audit_sprint_monitor_live.py --help
```

## What the tests falsified

- A completed group append followed by a crash before the group-terminal append must recover from the durable episode without reissuing any model request.
- A terminal HTTP attempt with a missing Monitor progress row must be restored as terminal; request/response bytes must hash back to the terminal ledger.
- A timed-out, malformed, truncated, rejected, interrupted, or server-error request consumes its assigned slot. No retry, replacement, inferred action, or favorable-outcome resampling occurs.
- M4 ballots, request bodies, observation hashes, response parser results and group terminal rows must replay consistently. Welfare, optimum, regret, private bonus and realized scores are recomputed from frozen matrices and raw ballots.
- The M4 fake server must reject a wrong listener, unexpected endpoint, changed checkpoint/runtime identity, redirect, tampered source bytes, or a request beyond the cap.
- Monitor must reject model alias/fingerprint drift, malformed usage/cost accounting, missing raw response bytes, and hidden reference fields. Raw and gated predictions remain separately recorded; private synthetic evidence appears only in the privileged projection.
- Credentials are absent from saved request/response and attempt ledgers. Monitor authentication is obtained only from `DEEPSEEK_API_KEY` after production gates; M4 creates a local key and removes it during cleanup.

## Retained failures

Initial and intermediate failures remain in `docs/results/final-sprint-candidate/failure-history-initial-20261020.md` and the attempt logs. They include a GGUF tokenizer metadata-key mismatch, test fixture/syntax defects, a raw transport-error hash mismatch, a request-count expectation mismatch, and an initial Windows loopback sandbox/listener fixture failure. Each correction has a regression test. No failed row or historical test was deleted to improve the final count.

Earlier full-history runs are also retained: 430 passed/103.73 seconds, 445 passed/125.81 seconds, and 447 passed/206.54 seconds. The latest full-history run is 447 passed/227.19 seconds. Earlier counts and the portable failed attempt are not overwritten.

## Interpretation boundary

These results establish that offline software paths, fake HTTP integration, budget gates, persistence, recovery, and deterministic replay work on the tested host. They do not establish Qwen behavior, DeepSeek Monitor quality, natural-proposal token balance, behavioral treatment effects, or collusion. The M4 run still has a shared-target confound: A and B know the same rewarded allocation, so independent agreement without a communication intervention cannot identify communication-induced coordination. The old fixed-stimulus token-parity result is not evidence of natural proposal token equality.
