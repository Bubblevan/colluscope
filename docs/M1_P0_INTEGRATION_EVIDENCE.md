# ColluScope M1-P0 Integration Gate Evidence

**Starting commit:** `5786852f8280af94256c2f9a16f7e872ffdd9146` (`codex/m1-r-runtime`).
**Working branch:** `codex/m1-p0-integration-gate-578`.
**Evidence scope:** offline tests, deterministic Mock episodes, and fake in-memory HTTP responses only. No local model server or LLM request was made.

## Environment and source state

The clean worktree was created from the exact accepted commit in a separate Git worktree at `D:\MyLab\colluscope\reference\m1-p0-gate`. The environment is recorded in `../runs/m1_p0/prechange/environment.txt`; baseline regression output and V1 artifact verification are in `../runs/m1_p0/prechange/`. V1 original run and canary manifest bytes were checked before and after verification and remained unchanged.

## Actual commands and results

All commands below run from the new worktree root in PowerShell. Set `PYTHONPATH` before invoking package/tests.

```powershell
Set-Location D:\MyLab\colluscope\reference\m1-p0-gate
$env:PYTHONPATH = 'src'
python -m pytest -q
python -m colluscope m1r --config configs/m1-r-offline-v2.toml --out runs/m1_p0/<new-run-dir>
python -m colluscope verify-m1r --run runs/m1_p0/<new-run-dir>
python -m colluscope m1r-canary --config configs/m1-r-offline-v2.toml --out runs/m1_p0/<new-canary-dir>
```

Evidence log files preserve both the first failed attempt and final successful runs:

| Check | Result | Raw record |
|---|---:|---|
| Baseline suite at accepted V1 source | 70 passed | `../runs/m1_p0/prechange/pytest-baseline.log` |
| Iteration after first implementation | 70 passed | `../runs/m1_p0/prechange/pytest-after-runtime-scaffold.log` |
| First new adapter test run | **1 failed, 7 passed**; test fixture used a context shorter than its configured max output | `../runs/m1_p0/iteration-01/pytest-vllm-adapter.log` |
| Corrected adapter unit suite | 8 passed at that iteration | `../runs/m1_p0/iteration-01/pytest-vllm-adapter-retry.log` |
| Final local-backend suite | **13 passed**; includes config round-trip, returned-model mismatch, raw failure retention, thinking-mode field, and shared budget checks | `../runs/m1_p0/iteration-01/pytest-vllm-thinking.log` |
| V2 targeted tests before final audit | 4 passed | `../runs/m1_p0/iteration-01/pytest-v2-canary.log` |
| First full v2 CLI generation | **failed independent verification** because verifier incorrectly expected C to have a private-message action | `../runs/m1_p0/iteration-01/m1r-v2-generation.log` and partial `../runs/m1_p0/v2-mock-run/` |
| Targeted tests after C-boundary correction | 4 passed | `../runs/m1_p0/iteration-01/pytest-v2-verifier-fix.log` |
| Pre-verifier-fix full suite | **86 passed**; intermediate result, not release evidence | `../runs/m1_p0/iteration-01/pytest-full-final.log` |
| Final full repository suite after explicit thinking-mode config | **88 passed** (delivery rerun: 2.73s) | `../runs/m1_p0/iteration-01/pytest-full-delivery.log` |
| V2 25-episode generation + automatic verifier | **PASS**, 25/25, 5 per condition, 95 logical Mock calls, 95 attempts / 190 ceiling, zero external/paid calls | `../runs/m1_p0/iteration-01/m1r-v2-generation-final-gate.log`; run `../runs/m1_p0/v2-mock-run-final-gate/` |
| Standalone V2 verifier | **PASS**, all file hashes, settlement, E projection, group hashes and V2 self-history recomputed | `../runs/m1_p0/iteration-01/m1r-v2-verification-delivery.log` |
| V2 adversarial suite | **PASS**, 11 traces / 18 assertions | `../runs/m1_p0/iteration-01/m1r-v2-canaries-final-gate.log`; cases `../runs/m1_p0/v2-canaries-final-gate/` |
| Independent V2 canary verifier | **PASS**, 11 traces / 18 assertions; source snapshots match current source | `../runs/m1_p0/iteration-01/m1r-v2-canaries-verification-delivery.log` |
| Historical V1 artifacts | **PASS**, 25-episode V1 run and 10-trace V1 canary still verify; manifests unchanged | `../runs/m1_p0/prechange/frozen-v1-verification.log`; regression `test_historical_v1_run_and_canaries_remain_verifiable_without_rewrite` |

The failure logs remain in the evidence tree and are not counted as successful runs. The mistaken PowerShell verifier invocation, which wrote its Python source to a log without executing it, is retained as `m1r-v2-canaries-verification-delivery-command-error.log`; the corrected independent execution and PASS output are separately recorded. No difficult negative or failed case was removed. The final 25-episode Mock run has `behavioral_evidence_claimed=false`; identical T/B/E core hashes across v1/v2 are expected from the deterministic default Mock, while the prompt/observation hashes differ.

## Schema and self-message counterexamples

`test_v2_delivers_exact_action_schemas_and_rejects_schema_counterexamples` checks the exact five frozen prompt/schema file hashes, exact schema delivery, truncated JSON, extra keys, wrong action type, malformed allocations, empty messages, and absence of a condition label in the prompt. `test_v2_ballot_keeps_own_message_and_delivered_peer_suggestion_as_counterexample` supplies a promise, a conflicting delivered peer suggestion, and a contrary ballot; saved observation hash and record are checked. A tamper test removes the own action, recomputes both observation and file hashes, and confirms the independent semantic verifier still rejects it.

The retained canary `self_message_and_different_peer_suggestion` exercises the same case in the exported package. It does not claim a model understood the text: responses are deterministic injected Mock actions.

## Backend tests and limits

The 13 local-backend tests plus V2 runtime counterexamples use `FakeOpener`, not a socket. They verify exact local OpenAI-compatible request body, system/user mapping and thinking-mode field, explicit non-default test sampling values, configured timeout passed to transport, actual usage logging, raw response retention, truncation failure, one bounded timeout retry, 503-body retention/retry, local-only endpoint enforcement, tokenizer identity/context guards, model-config disabled-by-default, GET-only mocked preflight, returned-model mismatch rejection, config parsing, and hard request-budget rejection before the second HTTP dispatch. The fake `model_id="test/model"` is a unit-test fixture, not a selected experiment model.

`LocalVLLMBackend.preflight()` was tested only against injected fake `/version` and `/v1/models` replies. These are software tests, not P0-IV endpoint or model compatibility results. There is no selected real model/tokenizer, so no real structured-output request or cost result exists.

## Exact call and money boundary

- Current authorization and actual usage: **0 real model calls, $0.00 API spend**.
- Full pilot research request budget: 75 ballots + 20 A/B message turns + 0 comprehension probes = **95 logical requests**.
- Retry ceiling: two attempts/request, **190 maximum adapter attempts**, enforced by shared `RequestBudget` before backend dispatch. Preflight GETs and separately authorized structured-output probes require a separate ledger and budget.
- Local vLLM proposed API ceiling: **$0.00** (loopback only). Host/GPU compute cost remains unpriced. Token/compute maximum remains unknown until model, tokenizer, output cap, context and hardware are approved. Offline Mock `256` is not a real-model recommendation.

## Reproduction and hashes

```powershell
Set-Location D:\MyLab\colluscope\reference\m1-p0-gate
$env:PYTHONPATH = 'src'
python -m pytest -q
python -m colluscope m1r --config configs/m1-r-offline-v2.toml --out runs/m1_p0/reproduction-run
python -m colluscope verify-m1r --run runs/m1_p0/reproduction-run
python -m colluscope m1r-canary --config configs/m1-r-offline-v2.toml --out runs/m1_p0/reproduction-canaries
```

Output directories must be new/empty. Prompt/schema hashes are enumerated in `M1_P0_FROZEN_PROTOCOL_V2.md`. `v2-mock-run-final-gate/manifest.json` and `v2-canaries-final-gate/manifest.json` contain per-file SHA256 values and source snapshots. V2 source snapshot SHA256 is `7c94667273a797ab2d3b9ce0d0fa2aa69d7f16eb56f6ac076dc6c149996fcf30`. The V2 run-manifest SHA256 is `809f19f6783d94da6745b77726d286ff413edf9bca212a7637a4bab7b26c2386`; the V2 canary-manifest SHA256 is `a360d73512b8d97d25a7c5afdfb3812163c7a1cce9b7bf193eab4d9a9ff0eb6d`. The real-backend config-template SHA256 is `9380a13d16c943c5c46a6499a92d63ad92774fab9081b55d9f1d3c3af4037c0c`. At generation, the implementation was uncommitted (`working_tree_clean=false`); the artifact embeds a per-file source snapshot matching the frozen candidate, which is independently checked by the verifier. The exact branch HEAD is reported in the integration decision and delivery message after push.
