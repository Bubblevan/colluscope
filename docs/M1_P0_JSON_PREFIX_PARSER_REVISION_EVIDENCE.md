# M1-P0 JSON-prefix parser revision — run evidence

**Outcome:** the parser fix handled the exact observed prefix, but the bounded live preflight is **NO-GO** because a message compatibility probe returned `no_message` when it was explicitly required to exercise `send_message`. No research episode ran.

## What was observed

The parser now accepts exactly `<think>\n\n</think>\n\n` before one action JSON object. The actual ballot response in the retained run carried this prefix and parsed to a valid allocation. The second actual completion also carried the prefix and parsed to `{"type":"no_message"}`. The `send_message` preflight probe expected the other valid union branch and stopped on that mismatch. This demonstrates the prefix handling on two actual llama.cpp responses; it does not demonstrate that the positive `send_message` output path works in this model/runtime configuration.

## Run counts and scope

- Parser-V2 retry run: `runs/m1_p0_local/25ep-pilot-json-prefix-v2-retry1-20261019/run/`.
- Source commit used by the runner: `7da707a` (full SHA is in `environment.json`). Model, llama.cpp bundle, endpoint 127.0.0.1:8081, prompt/schema, seed, sampling, reward, conditions and communication schedule were unchanged from the preceding parser-V2 config.
- Run-scoped config SHA256: `31fe1cde2ce03e51631a0cf74db41954e80ec1ecdb0a83550ff3f695658965db`.
- Preflight result: `FAIL`, expected `send_message`, actual `no_message`. It used **5/6 logical requests, 5/12 HTTP attempts, 2/4 completions**. `/props`, `/apply-template`, `/tokenize`, and the ballot action checks returned successfully. The third action probe was not sent.
- Episode attempts/completions/failures: **0/0/0**. Pilot logical requests and HTTP attempts: **0/0**. No T/B/E episode data or monitor evidence exists. External and paid API calls: **0/0**.
- Server health and exact listener owner passed in the retry run. The immediately preceding attempt loaded the same GGUF but failed its loopback health check with `WinError 10013` before any HTTP request; its independent verifier reports a zero-request NO-GO package. That failure is separate and preserved.

## Integrity and reproduction

- Retry run manifest SHA256: `5144829e4fafa7a3422b12b83b1a5c927d2386605e7e3c29126540a355d29640`.
- Raw retry preflight ledger SHA256: `e9c9235ccf330eafd3fb2d341a06b09b7d46793913fb76c82ea39cf1d69f7c4b`.
- Independent action-mismatch verifier output is retained at `runs/m1_p0_local/25ep-pilot-json-prefix-v2-retry1-20261019/preflight-action-mismatch-verification.log`; it verified 24 run-manifest entries and six source files from the recorded commit.
- Offline regression: **159 passed, 1 skipped** after adding the independent no-go verifier test. The skip is the opt-in host-dependent Windows listener test. The run log is `runs/m1_p0_local/pilot-iteration-01-parser-revision/pytest-full.log`.

Commands:

```powershell
python -m pytest -q
python scripts/verify_m1_p0_runtime_start_blocker.py --run runs/m1_p0_local/25ep-pilot-json-prefix-v2-20261019/run
python scripts/verify_m1_p0_preflight_action_mismatch.py --run runs/m1_p0_local/25ep-pilot-json-prefix-v2-retry1-20261019/run
```

The action-mismatch verifier should return `PASS_PACKAGE_INTEGRITY__NO_GO_ACTION_MISMATCH`. That status means the failure evidence is intact; it does not mean the preflight passed.
