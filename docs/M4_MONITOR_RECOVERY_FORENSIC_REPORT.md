# M4 and Monitor Protocol Failure Forensic Report

**Date:** 2026-10-20
**Recovery base:** `517d28793b82137ec26d3aef9cb23672c6668dfd`
**Scope:** no-call forensic replay and offline software validation. No Agent generation, Monitor inference, provider request, training, or model change was performed in this recovery task.

## Executive finding

The historical M4 run is an interface failure, not evidence that the agents chose not to communicate. All 24 assigned message requests received HTTP 200 with `finish_reason=stop`, but the adapter passed a response body beginning with a `<think>...</think>` envelope directly to `json.loads`. An independent read of the bytes after the single leading envelope found one complete action satisfying the exact per-request frozen JSON Schema in all 24 responses. The envelope is consistent with the pinned llama.cpp `reasoning_format=none` behavior; the immediate failure is therefore a **runtime/parser protocol mismatch**. These data do not show that the model lacked the ability to follow the action schema, nor prove that llama.cpp enforced the requested schema.

The historical Monitor run has a separate request-configuration and output-budget failure. Every one of its 856 payloads omitted both the thinking-mode setting and `response_format`, and capped completion at 128 tokens. There were 715 `length` terminations and 141 `stop` responses whose content parsed as JSON. Four additional length-terminated responses happened to contain parseable JSON; they remain truncated and are not complete outputs. Parseability is only a format measure, not factual accuracy or evidence correctness.

## Frozen evidence and provenance

The historical M4 raw run remains at `runs/m4/full-research-execution-20261020-run03/`; the historical Monitor raw runs remain under `runs/full-research-execution-20261020/monitor/`. These trees are Git-ignored and were read-only inputs to this report. Raw prompts, private messages, model responses, credentials, and unfiltered request bodies are not copied into this report or the committed forensic projection.

The sanitized, deterministic audit output is `docs/results/m4-monitor-recovery-20261020/historical_forensic_audit-v2.json`. Its M4 source manifest SHA-256 is `872ed46a42ceb3b3a8c25e949c24ca9ba31a3cd8e1808bce46c6bc3ee0e4b9b8`. Every case in the projection carries request/response hashes and a hashed request ID rather than raw message text.

The SHA-256 inventory for this evidence package, frozen configs, source, tests and reports is `docs/results/m4-monitor-recovery-20261020/artifact-sha256.json`; it excludes its own hash. Verify each listed file from repository root with this PowerShell command:

```powershell
$manifest = Get-Content docs/results/m4-monitor-recovery-20261020/artifact-sha256.json -Raw | ConvertFrom-Json
foreach ($entry in $manifest.files) {
    $actual = (Get-FileHash $entry.path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $entry.sha256) { throw "SHA-256 mismatch: $($entry.path)" }
}
```

## M4 reconstruction

| Check | Independently reconstructed result |
|---|---:|
| Assigned groups | 24 |
| Message-A HTTP responses | 24 |
| Historical terminal status | 24 `INVALID_JSON` |
| HTTP / finish reason | 24 HTTP 200 / `stop` |
| Exact single leading `<think>` wrapper | 24/24 |
| Separate `reasoning_content` field | 0/24 |
| Complete action suffix passing that request's frozen JSON Schema | 24/24 |
| Candidate suffix action type | 23 `send_message`, 1 `no_message` |
| Historically recorded messages, ballots, settlements | 0, 0, 0 |

The action-type counts above classify bytes found after the wrapper. They are **not** retroactively promoted to recorded actions. Historical episode, ballot, settlement, and terminal records remain untouched and still contain 24 failures.

The frozen v3 M4 request included `response_format=json_schema`, `chat_template_kwargs.enable_thinking=false`, and `reasoning_format=none`. The v3 `GenerationClient` validated the entire `message.content` as one JSON document and therefore rejected the leading wrapper. The pinned llama.cpp server documentation distinguishes `reasoning_format=none` (reasoning remains in `content`) from the `deepseek` mode (reasoning is separated into `reasoning_content`): [pinned llama.cpp server documentation at commit `571d0d5`](https://github.com/ggml-org/llama.cpp/blob/571d0d540df04f25298d0e159e520d9fc62ed121/examples/server/README.md). Current upstream [server API documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) also documents a request-level `reasoning_format` field; v4 therefore sets both the server-launch and request-level format to `deepseek`. The pinned build's actual Qwen3 response shape remains unverified until the bounded local diagnostic.

**Root-cause classification:** immediate cause = confirmed client/parser incompatibility with the returned message representation; contributing protocol choice = `reasoning_format=none`; upstream server defect = not established; model action-schema competence = not established; schema-constrained generation enforcement = not established. The observed action suffixes all happen to satisfy the schema, which supplies no counterexample capable of showing whether the server enforced it.

## Historical Monitor reconstruction

| Phase | Assigned requests | `length` | `stop` | Raw JSON parseable | Complete (`stop` + JSON parseable) |
|---|---:|---:|---:|---:|---:|
| Scripted controls | 280 | 264 | 16 | 17 | 16 |
| M4 trace evaluation | 504 | 381 | 123 | 126 | 123 |
| Matched worlds | 72 | 70 | 2 | 2 | 2 |
| **Total** | **856** | **715** | **141** | **145** | **141** |

Every payload had only `model`, `messages`, `temperature`, and `max_tokens`; `thinking` and `response_format` were omitted in all 856 requests. Temperature was 0 and `max_tokens` was 128. The 4 JSON-shaped outputs with `finish_reason=length` are counted as raw JSON parseable but not complete. This distinction is confirmed by raw response bytes, not by the prior summary report.

The official [DeepSeek thinking-mode guide](https://api-docs.deepseek.com/guides/thinking_mode/) states that thinking is enabled by default, can be disabled with `{"type":"disabled"}`, and uses reasoning tokens within the completion budget; temperature does not control sampling while thinking is enabled. The official [JSON Output guide](https://api-docs.deepseek.com/guides/json_mode/) documents `response_format={"type":"json_object"}`, requiring JSON-oriented instructions and warning that empty output may occur. These facts make default thinking plus a 128-token cap a plausible contributor to the high truncation rate. **The historical data alone do not isolate the contribution of thinking mode, output cap, and format mode.** The absence of `response_format` is verified from the actual payloads; it is not a claim that adding it alone guarantees schema compliance.

## Downstream consequences

The committed historical M4 trace audit is integrity-only: it reports 24 assigned groups, 0 response-action links, and 0 recomputed settlements. Therefore the M4 behavioral Monitor phase is `NOT_RUN`, with zero calls, until it has actual linked actions and replayable ballot settlements. A direct rerun of the legacy full verifier from the recovery worktree was attempted and failed closed because the run manifest pins the older `scripts/audit_m4_live.py` hash while this branch changes that script for v4 config detection. The source mismatch is preserved in `test_logs/historical-m4-independent-audit.log`; neither the manifest nor the old run was edited. The separate forensic raw-response replay succeeded. Full historical verifier reproduction requires the exact source snapshot pinned by that run plus local access to its ignored raw data.

The full historical B4/B5 matched-world phase is also `NOT_RUN` until a new diagnostic certificate shows assessable, parseable paired B4/B5 outputs on both the explicit-sequence positive control and the proposal-without-acceptance hard negative. The certificate gate checks coverage and raw hashes, not prediction correctness; a later scientific scorer must independently measure correctness, citation support, false assertions, and abstention.

`docs/results/m4-monitor-recovery-20261020/recovery_dependency_gate.json` records the actual current gates: both phases are `NOT_RUN`, both have zero new calls, and the M4 gate identifies zero linked actions/settlements and zero valid ballot episodes.

## Reproduction

From repository root in PowerShell:

```powershell
python scripts/audit_protocol_failures.py
python -m pytest tests/test_m4_action_interface_v4.py tests/test_recovery_gates.py tests/test_monitor_recovery_protocol.py tests/test_run_full_research_monitor_gate.py -q
python -m pytest tests/test_m4_live_runtime.py -q
python -m pytest -q
```

Outputs from this recovery task are preserved in `docs/results/m4-monitor-recovery-20261020/test_logs/`. The final full suite produced 512 passed and one explicit host-dependent skip in 134.46 seconds on Python 3.12.4 / Windows. The skipped test is `tests/test_m1_p0_preflight_runner.py:142` and requires an opt-in Windows listener-owner-table check. It is not counted as passed. `python scripts/audit_m4_live.py --run runs/m4/full-research-execution-20261020-run03` is expected to reject this modified worktree on its source-hash check; do not change the historical manifest to make it pass. The historical audit JSON and the recovery's independent forensic replay are the currently available sanitized receipts.

## Interpretation boundary

No new LLM call was made. Fake HTTP integration replies exercise software paths only. There is no newly observed agent behavior, monitor prediction, causal effect, collusion label, or detector-performance result. The next uncertainty-reducing step is a separately approved, bounded compatibility diagnostic—not an automatic replay of the 24 failed groups and not the full M4 or 856-request Monitor schedule.
