# Monitor DeepSeek Recovery Diagnostic v2

## Purpose

This is a bounded prospective interface diagnostic for the failed 856-request Monitor protocol. It is not the full B2–B5 evaluation and does not authorize external API traffic. Its purpose is to determine whether a corrected DeepSeek request configuration yields enough complete, parseable outputs on a predeclared positive and hard-negative pair to make a later explicitly approved experiment technically assessable.

The existing 856 request/response corpus is immutable. It is not repaired or rescored by this protocol.

## Frozen request protocol

The checked-in freeze is `configs/monitor-recovery-v2.toml`; the exact 16-row schedule is `configs/monitor-recovery-diagnostic-v1.json`; prompts are under `prompts/sprint-baseline-v2/` and task definitions remain from `prompts/sprint-baseline-v1/tasks.json`.

| Parameter | Frozen value |
|---|---|
| Model alias | `deepseek-flash` |
| Endpoint | `https://api.deepseek.com/chat/completions` |
| Thinking | explicitly disabled (`{"type":"disabled"}`) |
| Temperature | `0.0` |
| Output cap | 256 tokens |
| Input byte and conservative token bound | 8,192 each |
| JSON mode | `response_format={"type":"json_object"}`; full JSON example and schema labels appear in prompt |
| Logical / physical requests | 16 / 16 |
| Attempts per request | 1; zero retries and zero replacements |
| Hard peak-cost reserve | USD 0.0442368; hard cap USD 0.05 |
| Price basis | peak input cache-miss USD 0.30 / million and output USD 1.20 / million, checked 2026-10-20; must be rechecked before any future request |

Budget calculation:

```text
16 * (8192 * $0.30 + 256 * $1.20) / 1,000,000 = $0.0442368
```

This is a worst-case reserve under the frozen bounds, not a usage or invoice claim. The official [DeepSeek thinking-mode documentation](https://api-docs.deepseek.com/guides/thinking_mode/) describes the explicit disable parameter and reasoning-token behavior. The official [JSON Output documentation](https://api-docs.deepseek.com/guides/json_mode/) describes JSON mode and its limits. The official [Chat Completions API reference](https://api-docs.deepseek.com/api/create-chat-completion/) defines the request fields. The official [pricing page](https://api-docs.deepseek.com/quick_start/pricing/) is the source for rates; no later execution may rely on a stale snapshot.

## Frozen 16-row diagnostic content

- Four privileged explicit-sequence rows: B4/B5 paired on synthetic positive `SC-POS-01` and hard negative `SC-NEG-02` (proposal without acceptance).
- Four privileged acceptance rows: the same positive and hard-negative cases, B4/B5 paired.
- Eight public-harm rows: positive and negative controls under Public-only and Privileged permissions, B4/B5 paired.

The request body contains only the model-visible evidence and task. It excludes the case reference, treatment/construction fields, reference answers, welfare-gap and target-execution labels. The preparation test independently checks the exact 16 bodies, evidence hashes, permissions, method/view mapping, and absence of banned reference markers.

## Gate and scoring boundary

The dispatch is disabled unless `--live`, a separately approved nonempty ID, and a matching receipt are supplied. Before any credential is read, the runner reconstructs all 16 requests, checks the frozen hashes and input bounds, and verifies that the complete schedule fits the budget. Raw requests and responses must remain in the Git-ignored ACL-restricted run root. Authentication headers are never saved. The local environment credential is read in memory only and removed from process environment at completion.

The independent audit requires 16 unique starts and terminals, exact request/response hash agreement, allowed returned model identity, no retry, no saved authentication header, and complete output (`finish_reason=stop`) that parses. The downstream compatibility gate additionally requires at least 15/16 complete parseable rows, no more than one `length` termination, and parseable B4 and B5 rows for both the positive and hard-negative explicit-sequence pair. Prediction correctness is **not** a dispatch compatibility gate; a parsed but wrong prediction must remain an observable model error for a later independently frozen scorer.

The run manifest freezes hashes for the runner, independent auditor, transport implementation, projection/scoring code, prompt/task files, schedule, configuration, and synthetic controls file, together with the Python version. The independent auditor fails closed on any later source/config hash drift.

No monitor request was sent for this protocol. A later call must be explicitly authorized; price, endpoint, credential source, alias/fingerprint, hashes, privacy and cost cap must be revalidated at that time.

Future command shape, not authorization:

```powershell
python scripts/run_monitor_recovery_diagnostic.py --live --approval-id <separately-approved-id> --authorization-receipt runs/full-research-execution-20261020/monitor/recovery_diagnostic/authorization-receipt.json
python scripts/audit_monitor_recovery_diagnostic.py --run runs/full-research-execution-20261020/monitor/recovery_diagnostic
```
