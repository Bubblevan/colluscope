# DeepSeek Real Coordination Pilot V2 — Evidence

**State:** terminal transport failure on the first authorized request; no model response was received and the remaining schedule was not run.

## Frozen registration

- Branch: `codex/deepseek-real-coordination-40-20261021` (push this freeze before dispatch).
- Corrected experiment ID/path: `deepseek-real-coordination-40-v2`.
- V1 is retained and closed `EXECUTION_BLOCKED`; its path mismatch caused **0 requests**. See `docs/results/deepseek-real-coordination-v1/PREFLIGHT_PATH_MISMATCH.md`.
- Registered V2 preregistration SHA-256: `5ee25c260849579e9dfc037b583e4d3d66f37d9317ff1e148550742566f2ce65`.
- Schedule SHA-256: `755e857840bab9ddf74ba6a9197fbd71d579228ca83bc579d8441d1e82c66092`.
- Configuration SHA-256: `aac32166ca21b41790654f6f97be615475df9bc49da89788a44572dc5b75bb77`.
- Protocol SHA-256: `a172cafe61760d085b624467e354ab3ee03f773783c0e4b57ffb9099560c72d3`.
- Authorization batch: `DS-FLASH-REAL-COORD-V2-40-20261021`; SHA-256 `05ac7ab9dce3b6dd569b50210ac7da358e5316fb7627ffc5ade3d817585db858`.
- Model: DeepSeek Flash only, official `api.deepseek.com`; temperature 0, thinking disabled, strict function calling, 256 output-token cap, 90-second timeout, zero retries/replacements.
- Tokenizer SHA-256: `81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99` (source commit `935817c66f5d6e64838f419692545f06787e485f`).
- Environment: Python 3.12.4; `tokenizers 0.19.1`, `jsonschema 4.19.2`, `pytest 9.1.1`.

## Offline checks

| Check | Result | Evidence |
|---|---|---|
| Python compile | Pass | `docs/results/deepseek-real-coordination-v2/pycompile.log` |
| Targeted adversarial tests | **17 passed** | `docs/results/deepseek-real-coordination-v2/targeted-pytest.log` |
| Schedule/config freeze | Pass | `docs/results/deepseek-real-coordination-v2/freeze-check.log` |
| Runner check-only payload | `PASS_OFFLINE_PREFLIGHT`, 0 calls, 40 cap, $0.50 cap | `docs/results/deepseek-real-coordination-v2/runner-check-only.log` |
| Runner check-only process status | **Exit code 2 despite PASS payload**; known CLI mapping defect: `main()` treats an absent `stop_status` as a stop. It does not affect the live call path or any experiment input. Preserved in `runner-check-only-exit.txt`; not represented as a clean command exit. |
| Registry audit | Pass, no integrity errors | `docs/results/deepseek-real-coordination-v2/registry-audit.log` |
| Raw-storage boundary | `logs/deepseek-real-coordination-v2/` is ignored by the repository's existing `/logs/` rule; directory did not exist at preflight. |

All local source/model/control checks were completed without a model request. `researchctl audit` reports **1,156** previously used project requests and **$0.133568658** cumulative cost. V2 is capped at 40 requests / $0.50, leaving four requests unused under the 1,200 project ceiling. Even the batch reservation keeps the cumulative cost well below the $2.50 ceiling.

## Dispatch gate

The run schedule starts with four authoritative delivered/absent fact controls. Any incorrect answer, invalid or truncated output, HTTP/transport failure, provider identity mismatch or interrupted request stops all remaining calls. A valid control is not evidence of game-task capability; it only allows the frozen 36 game requests to proceed. Raw prompts, responses and private messages stay local in the ignored ACL-restricted logs directory.

The CLI exit-code defect is operationally misleading but did not change the preflight payload. The frozen batch was pushed at `31b7ebf3aa82b7dd656b3b944183fa0a92a23fc3` before dispatch.

## Live execution outcome

The first scheduled request (`C1-delivered`) was handed to the HTTP transport at `2026-10-21T04:53:40.218509+00:00`. Local hostname resolution failed for `api.deepseek.com` with Windows error 11001 (`getaddrinfo failed`) before any HTTP connection was established.

- One physical request attempt is recorded against the 40-request batch; there were **0 HTTP responses**, **0 returned model generations**, and **USD 0.00 actual external cost**. The conservative reserved peak cost for this attempt was USD 0.0009816; this is not a charge.
- The other 39 assigned requests remain unattempted. The four-control gate was not passed; the 36 game requests did not run. No retry or replacement was made.
- The raw request is 996 bytes and matches the `attempt_started` SHA-256 `e80ed1e34d72e8056fc1a572af2f29778b9ce2aa2a8bc0ad94409c523744bd9f`. There is no response `.bin`; the error metadata has null HTTP status/hash and `auth_header_saved: false`.
- Run artifacts remain local at `logs/deepseek-real-coordination-v2/`, ignored by Git and ACL-restricted to the local `bubblevan` account.
- The runner then hit a secondary recovery validation defect: the transport-error terminal row omits `request_sha256`, while `_attempt_rows()` requires it on the terminal row rather than falling back to the already matching start row. This caused a process exit before remaining assigned rows could be progress-terminalized. The original frozen source and raw files were not modified.

This is an execution failure, not a failed model capability control. It gives no evidence about fact use, peer communication, incentives, coordination, or collusion. The full attempt record and stop decision are in `docs/results/deepseek-real-coordination-v2/ATTEMPT_001_TRANSPORT_FAILURE.md` and `docs/DEEPSEEK_REAL_COORDINATION_V2_DECISION.md`. The terminal one-row sanitized request ledger is `docs/results/deepseek-real-coordination-v2/model-request-ledger-sanitized.json`.
