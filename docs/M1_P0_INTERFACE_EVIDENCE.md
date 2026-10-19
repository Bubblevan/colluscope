# M1-P0 Interface V3 — evidence report

**Cycle:** M1-P0-IF-V3-01  
**Protocol:** `m1-p0-interface-v3`  
**Baseline commit:** `657eab90356ce9137c2988aacb4b5b10d0402c28`  
**Evidence class:** offline software tests and integrity checks only  
**Real model calls in this cycle:** 0  
**Research episodes / monitor evaluations:** 0 / 0

## 1. Checkout and baseline audit

The audited checkout is `reference/m1-p0-local-qwen-integration`, branch `codex/m1-p0-local-qwen-integration`. It began clean at `657eab90356ce9137c2988aacb4b5b10d0402c28`. At inspection, the remote topic branch pointed to the same SHA. The separate parent checkout remained on `origin/main` at `190ea3cb4e5803bea3fede9a0eddbf8e4d57fe51`; it was not used as the implementation baseline.

Environment recorded in `runs/m1_p0_interface_v3/evidence/environment.txt` and `python-packages.txt`:

- Windows, 64-bit process architecture.
- Python 3.12.4, pip 24.0, pytest 9.1.1.
- No model server was started and no real model or external/paid API request was made.
- The suite's HTTP behavior is exercised with deterministic fake openers and local test fixtures. The opt-in host-dependent Windows listener-owner test remained skipped.

Baseline full suite on the clean source checkout: **159 passed, 1 skipped**. Raw output: `runs/m1_p0_interface_v3/evidence/pytest-baseline.log` (SHA256 `d357f5a6c4697e368f26ff261cc1dd4e177b91ec4d87c18dfe6c321353116b04`).

The M0 and M0.1 frozen docs/runs diff check returned exit code 0; see `m0-frozen-diff-check.log`. No M0/M0.1 source, trace, manifest, or report was modified.

## 2. Historical adverse evidence re-verified

The old run decisions and raw bytes remain unchanged. Independent verifiers were run before and after the V3 source changes:

| Historical package | Result | Verified facts |
|---|---|---|
| Strict-parser preflight with zero episodes | `PASS_PACKAGE_INTEGRITY__NO_GO_PREFLIGHT` | 50 manifest entries plus 24 copied-parent entries; 4 current preflight HTTP requests; 0 episodes; strict-parser failure retained. |
| Parser-V2 launch blocked before HTTP | `PASS_PACKAGE_INTEGRITY__NO_GO_NO_HTTP` | 21 manifest entries; 0 HTTP requests, 0 episodes; exact historical source files verified. |
| Parser-V2 valid `no_message` vs expected `send_message` | `PASS_PACKAGE_INTEGRITY__NO_GO_ACTION_MISMATCH` | 24 manifest entries and 6 source files verified; 5 logical / 5 HTTP / 2 completions; observed `no_message`; 0 episodes. |

Raw final post-change results are `verify-historical-strict-parser-no-go-final.log`, `verify-historical-zero-http-final.log`, and `verify-historical-action-mismatch-final.log`. Each verifier exited 0. `PASS_PACKAGE_INTEGRITY` validates retained failure evidence; it does not turn a historical NO-GO into a GO.

## 3. Change made and falsification results

V2 required an exact `send_message` output during the positive communication probe. The actual response was valid under the message action schema (`no_message`), so V2 stopped with an action-choice mismatch after parsing succeeded. V3 makes the gates orthogonal:

- A ballot request still requires a schema-valid ballot.
- A message request accepts either schema-valid action, `send_message` or `no_message`.
- Each probe records `requested_action`, `actual_action`, and `followed_instruction`; this diagnostic does not fail the schema/transport gate.
- `requested_action` is parsed from the frozen prompt's `preflight_probe_instruction` and cross-checked against metadata before any HTTP; an inconsistent diagnostic label is rejected before dispatch.
- A passing interface result is explicitly named `PASS_INTERFACE` and identifies `schema_transport_status: PASS`.
- If no real `send_message` output appears, its model-generation status is `UNVERIFIED`. Offline plumbing evidence is not inserted into a live run's status.
- The consumed 8081 preflight approval is blocked before creating a run directory. A historical pre-V3 Pilot preflight cannot be resumed under V3.

Targeted offline suite after prompt-binding hardening: **84 passed, 1 skipped**. Raw output: `pytest-focused-v3-final.log`. The prior pre-binding targeted result (**83 passed, 1 skipped**) remains in `pytest-focused-v3-pre-prompt-binding.log`.

Counterexample coverage and result:

| Counterexample | Observed result |
|---|---|
| Probe asks for `send_message`; fake server returns valid `no_message` | `PASS_INTERFACE`, `followed_instruction: false`, raw completion retained, `positive_send_message_model_output: UNVERIFIED`. |
| Probe asks for each message branch and fake server returns the requested valid branch | `PASS_INTERFACE`; diagnostics match the requests. This remains fake-transport evidence only. |
| Message request returns an extra field | Hard parser failure after 5 HTTP calls; malformed raw response retained; later completion is not dispatched. |
| Fake HTTP `send_message` passes through runtime | A's text reaches B only; it appears in A's own ballot history and B's peer history; it does not enter C's observation; event export respects the explicitly enabled auditor permission. Five fake completions, zero real calls. |
| Requested-action metadata says `send_message`; prompt explicitly requests `no_message` | Rejected before any HTTP; no completion or setup request is dispatched. |
| Frozen `oneOf` alternatives use distinct required `type.const` values | Schema invariant passes for `send_message` / `no_message`; a mutated overlapping discriminator is rejected by the targeted counterexample test. This protects the static union-equivalence assumption, not the upstream server. |
| Reuse the prior 8081 approval | Rejected before output-directory creation. |
| Resume the retained V2 failed preflight as V3 | Rejected as protocol-version mismatch; historical package remains independently verifiable. |

The frozen V2 assertion snapshot was run once against the V3 implementation to retain the transition counterexample: its two obsolete `status == PASS` assertions failed because V3 returns `PASS_INTERFACE`. The raw failure is `pytest-legacy-status-expectation-counterexample.log`; the exact baseline test snapshot is `legacy-status-expectation-tests.py`. This was a test-contract update, not a removed research sample.

The first full-suite attempt also caught V2 continuation being accepted far enough to fail on changed prompt-evidence fields (**1 failed, 162 passed, 1 skipped**). That raw result is `pytest-full-v3-protocol-resume-failure.log`. The continuation path now rejects old protocol artifacts explicitly; the corresponding test expects the rejection. No historical run bytes or gate verdict changed.

At the initial V3 code freeze, the focused suite was **84 passed, 1 skipped** and full suite **164 passed, 1 skipped in 17.63s**; both raw logs remain unchanged. The pinned-source review then added one local schema-invariant counterexample. The final focused rerun is **85 passed, 1 skipped in 4.85s** (`pytest-focused-v3-upstream-final.log`); the adapter module alone is **31 passed in 0.44s** (`pytest-upstream-schema-focused.log`); final full offline suite is **165 passed, 1 skipped in 16.80s** (`pytest-upstream-schema-full.log`). The single skip is the opt-in, host-dependent Windows listener-owner integration check (`COLLUSCOPE_LIVE_WINDOWS_LISTENER_TEST=1`); it was not needed for the offline fake-transport gate and is not claimed as passed. The earlier pre-binding full run (**163 passed, 1 skipped**) is retained as `pytest-full-v3-pre-prompt-binding.log`.

## 4. Frozen input and source fingerprints

`runs/m1_p0_interface_v3/evidence/source-and-frozen-input-hashes.txt` records SHA256 values for the changed adapter/runner/tests, V2 prompt and schema files, draft configs, persistent goal, AGENTS charter, TRD, and V3 protocol. Prompt/schema/config bytes were not changed in this cycle. The exact attached-document copies match their source attachments byte-for-byte:

| Attached file | SHA256 |
|---|---|
| `COLLUSCOPE_PERSISTENT_RESEARCH_GOAL.md` | `1eac8a93730711d762131fbb2a92286d56c5e03319c07eb0aa31183ea4f48f82` |
| `CODEX_PERSISTENT_SETUP.md` | `32ab427235a0d86e4ebe0c2f0550e2e37838099680827274ae89a303513f6f3b` |
| `M1P0_NEXT_GATE_TRD.md` → `docs/M1_P0_INTERFACE_TRD.md` | `5ed87e3946cde5446d54e21b3c7739b667caeed5d38558bd4d5ce29aeae0dd79` |

The current implementation/frozen-input SHA values are included in `source-and-frozen-input-hashes.txt`; the consolidated `artifact-hashes.txt` covers those source files plus the raw evidence files. Hashes establish byte identity only, not behavioral or server validity.

## 5. Reproduction commands

Run from the repository root in the frozen Windows environment:

```powershell
python -m pytest -q
python -m pytest -q tests/test_openai_compat_llamacpp.py tests/test_m1_p0_preflight_runner.py tests/test_m1_runtime.py tests/test_m1_p0_local_pilot.py
python -m pytest -q tests/test_openai_compat_llamacpp.py
python scripts/verify_m1_p0_preflight_blocker.py --run runs/m1_p0_local/25ep-pilot-20261019/run-resume-01
python scripts/verify_m1_p0_runtime_start_blocker.py --run runs/m1_p0_local/25ep-pilot-json-prefix-v2-20261019/run
python scripts/verify_m1_p0_preflight_action_mismatch.py --run runs/m1_p0_local/25ep-pilot-json-prefix-v2-retry1-20261019/run
```

These commands replay offline tests and verify existing evidence only. The last two commands correspond to the final protocol-focused and upstream-schema counterexample logs. They do not start a model server or issue real completions.

## 6. Pinned upstream schema inspection

The server documentation and converter were inspected at the exact configured llama.cpp commit `571d0d540df04f25298d0e159e520d9fc62ed121` (inspection notes and pinned URLs: `runs/m1_p0_interface_v3/evidence/upstream-schema-source-inspection.txt`). The server README documents the direct chat-completions `response_format: {type: "json_schema", schema: ...}` form and the relevant `chat_template_kwargs` / `reasoning_format` fields. In the pinned `common/json-schema-to-grammar.cpp`, the converter recognizes `oneOf` and constructs an alternative/union grammar from its branches; the same conversion path handles literal `const` values, required object properties, closed objects (`additionalProperties: false`), and bounded strings used by the frozen communication schema.

For this specific communication schema, the two branches both require `type`, and constrain it to distinct constants (`send_message` and `no_message`). Thus the branches are disjoint, so an alternative grammar can represent either valid action even though it does not separately implement JSON Schema's general exclusivity check for overlapping `oneOf` branches. The local strict parser remains the post-response authority for exact shape validation. A targeted schema test additionally protects the branch-disjointness assumption.

This is static source/documentation evidence only. The actual configured llama.cpp process was not started or contacted in this V3 cycle. The installed server's request acceptance, generated grammar, enforcement at inference time, and positive `send_message` output remain **unverified**. Fake HTTP tests are not server evidence.

## 7. Evidence limits

- `PASS_INTERFACE` has been exercised only through fake HTTP/test fixtures. It is not an actual llama.cpp V3 preflight result.
- Actual model generation of a positive `send_message` remains **UNVERIFIED** under the retained local model/runtime. Do not repeat the old probe until one appears.
- No M1-P0/P1 episode, collusion label, reward-comprehension result, monitor input, detector score, M2 comparison, or causal effect was produced.
- The shared-target and extra-message-turn confounds remain as specified in the M1 runtime TRD.
