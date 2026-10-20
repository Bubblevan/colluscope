# M4 / Monitor Protocol Recovery Decision

**Decision date:** 2026-10-20
**Recovery branch base:** `517d28793b82137ec26d3aef9cb23672c6668dfd`
**Model/API calls in this recovery task:** 0

## Gate decision

| Gate | Decision | Evidence and boundary |
|---|---|---|
| Historical M4 artifacts preserved | **PASS; full legacy verifier replay BLOCKED by pinned-source drift** | The original 24 assignments, 24 `INVALID_JSON` terminals, 0 linked actions and 0 settlements remain untouched. Read-only forensic audit classified 24 complete schema-valid JSON suffixes after one exact wrapper; these are forensic candidates, not retroactive actions. A direct old-verifier replay refuses the modified source hash, and that failed check is preserved rather than bypassed. |
| Historical Monitor requests reconstructed | **PASS** | 856 raw requests were replayed: 715 `length`, 141 `stop`, 145 JSON-shaped outputs, and 141 complete stop-plus-JSON outputs. All payloads omitted thinking and JSON response-format fields and used a 128-token output cap. |
| M4 v4 offline implementation gate | **PASS for fixture-backed software path** | Exact wrapper parser, `reasoning_format=deepseek` at both launch and request layers, strict action/schema validation, no repair/retry, valid `no_message`, fake HTTP integration, and frozen-source hash checks passed. Full suite: 512 passed, one opt-in Windows listener-owner-table test skipped. This is not real llama.cpp compatibility evidence. |
| M4 v4 real compatibility diagnostic | **READY FOR SEPARATE APPROVAL; NOT RUN** | Frozen 18-call diagnostic covers six message, six ballot, and six positive-control requests. No receipt was created and no generation was made. Passing requires all 18, including all failures, to terminalize and all 18 to validate. |
| DeepSeek Monitor v2 bounded diagnostic | **READY FOR SEPARATE APPROVAL; NOT RUN** | Frozen 16-request diagnostic, zero retries/replacements, $0.05 hard cap; $0.0442368 worst-case reserve at the 2026-10-20 rate snapshot. Recheck official price and identity before any call. |
| M4 behavioral Monitor phase | **NO-GO / NOT_RUN** | The actual gate read the independent audit and raw episodes: 24 assigned, 0 response-action links, 0 recomputed settlements, 0 completed valid-ballot episodes. It returns `NOT_RUN` before credential loading or transport and records 0 calls. |
| Full B4/B5 matched-world phase | **NO-GO / NOT_RUN** | The required paired diagnostic certificate does not exist. The downstream gate returns `NOT_RUN` before credentials or transport and records 0 calls. |
| Real behavior, factual Monitor accuracy, collusion/intent | **UNKNOWN / NO CLAIM** | No new inference occurred. Historical M4 is incomplete; historical Monitor completion rates do not establish factual correctness, citations, detector performance, or latent intent. |

## Root-cause judgment

For historical M4, the highest-confidence immediate cause is a client/parser protocol mismatch: `reasoning_format=none` left a `<think>` envelope in `message.content`, while v3 required the entire content field to be JSON. The exact JSON suffix is schema-valid in 24/24 responses. We have not established a llama.cpp parser defect, strict constrained-decoding behavior, or model-level instruction failure. The v4 parser is a prospective, narrowly scoped compatibility change and must be tested against the pinned real server before any behavior experiment.

For historical Monitor, provider-default thinking combined with a 128-token completion cap is a plausible explanation for the 715 length terminations; omission of JSON mode is also a protocol defect. The existing data do not isolate these factors. The v2 proposal changes all of these in a new protocol and has no real output evidence yet.

## Conditions before any next request

1. The user must separately authorize the precise diagnostic (local M4 only or external DeepSeek Monitor), request cap, privacy/storage terms, and run window. The checked-in approval-receipt templates are operator attestations; they are not cryptographic authorization and do not replace user approval.
2. For the local M4 diagnostic, verify the exact GGUF, llama.cpp binary/build, tokenizer, template, listener ownership, local-only endpoint and private ACL. Stop on any identity or egress mismatch.
3. For the external Monitor diagnostic, recheck official price/model behavior, exact endpoint and returned-model allowlist, credential source, budget reserve and data-transmission permission. Stop on auth, identity, cost, privacy, or request-hash mismatch.
4. Keep all 18 M4 or 16 Monitor slots assigned; zero retries and replacements. Any started request is terminal even on failure.
5. Do not run the 24-group M4 behavioral schedule or the 856-row Monitor phase unless the diagnostic certificate passes its frozen coverage gate and a further explicit user authorization covers those experiments.

## Reproduction commands

```powershell
python scripts/audit_protocol_failures.py
python -m pytest tests/test_m4_action_interface_v4.py tests/test_recovery_gates.py tests/test_monitor_recovery_protocol.py tests/test_run_full_research_monitor_gate.py -q
python -m pytest tests/test_m4_live_runtime.py -q
python -m pytest -q
```

Raw pytest logs, the current dependency-gate result, and a SHA-256 inventory of the recovery evidence are under `docs/results/m4-monitor-recovery-20261020/`. The failed full legacy audit replay is separately recorded in `test_logs/historical-m4-independent-audit.log`; use the exact run-pinned source snapshot to repeat that verifier, not the modified working tree. None of the listed successful replay/test commands sends a model/API request. The two future `--live` command forms in the protocol documents remain inert absent explicit approval and a matching receipt.

## Final decision

**GO only to present the two bounded diagnostics for user review and approval. NO-GO to start either diagnostic in this task. NO-GO to M4 behavior monitoring or the full paired Monitor comparison.** Preserve the 24 historical M4 failures and 715 historical Monitor truncations. No M1/M2 progression is started.
