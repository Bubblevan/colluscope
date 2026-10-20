# M4 Live Runtime v3 — Decision

**Decision date:** 2026-10-20

**Implementation gate:** **GO for a separately approved local run**

**Real experiment gate:** **NO-GO / not authorized in this task**

## Decision basis

The v3 runner is distinct from the historical offline-Mock runner and is implemented against the pinned local llama.cpp Chat Completions endpoint. Its CLI remains inert unless `--execute-live` and a nonempty approval reference are supplied. Production execution additionally requires Windows current-user ACL storage, the exact checked-in config and frozen local assets, local listener/process ownership checks, and the authenticated model identity probe. The hard limit is 264 physical generation attempts: 24 assigned groups, at most 11 requests per group, one attempt per request, zero retries, zero replacement groups.

The focused runtime suite and full-history tests passed as recorded in `M4_LIVE_RUNTIME_EVIDENCE.md`. Fake responses verify mechanics only. No Qwen generation was made. Thus GO is strictly an implementation-readiness decision after the user fixes a separate run approval; it is not a claim that a scientific treatment effect or positive control has been established.

## Sprint Monitor status

The existing B2–B5 dispatcher was retained and reviewed, not rebuilt. Runtime revision 1.2 now persists transport-error bytes exactly, resumes terminal attempts without re-sending, records model/fingerprint and provider usage, conservatively charges missing usage against the frozen reserve, enforces the 280-row/280-attempt and USD 1 ceilings, and has an independent raw/gated rescoring auditor. Test-only injected transport is labeled as fake and cannot be used by the production CLI path.

The checked-in Monitor config remains `live_dispatch_enabled = false` with a blank authorization ID. Therefore its live CLI must refuse to dispatch. A later Monitor run requires a separate approval and a separately versioned, reviewed config derived from the frozen values with an explicit approval ID, refreshed official price verification no older than seven days at run time, data-transmission permission, and `DEEPSEEK_API_KEY` supplied in the operator environment. No secret is read from `.env` or saved. The request plan remains 280 rows/attempts; conservative peak estimate in the verified current config is USD 0.4086309 against a hard USD 1.00 ceiling. No Monitor request was sent here.

**Monitor implementation gate:** GO for a separately approved, versioned configuration after current pricing and provider identity requirements are reviewed.
**Monitor experiment gate:** NO-GO / not authorized in this task.

## Required stops before any separately approved run

Stop before the first generation/request if any of the following holds:

- Frozen checkpoint, runtime, tokenizer, chat template, prompts, schedule, source artifacts, or endpoint identity differs.
- The M4 listener is not owned by the launched pinned `llama-server.exe`, or any connection leaves `127.0.0.1:8081`.
- M4 output storage fails current-user ACL verification or is outside ignored `runs/m4/`.
- Monitor pricing verification is stale, approval/config IDs mismatch, credentials are absent, or provider identity/fingerprint is missing or drifts.
- A request cap or cost reservation would be exceeded.
- An input contains researcher-only treatment/truth fields, reference answers, or a private message outside its allowed evidence view.
- Any raw request/response, hash, terminal ledger, ballot settlement, or independent audit fails integrity checks.

Once a request starts, malformed output, timeout, transport error, server error, or interruption is terminal. It consumes its assigned slot. Never retry, repair into a successful action, replace a group, or drop the row.

## Reproduction / separately approved entry points

Local M4; requires a separate user authorization and approved ID. The command alone is not authorization:

```powershell
$env:PYTHONPATH = 'src'
$runId = 'm4-live-v3-approved-run-01'
$approvalId = Read-Host 'Enter the separately approved run ID'
python scripts/run_m4_live.py --config configs/m4-live-runtime-v3.json --out "runs/m4/$runId" --execute-live --approval-id $approvalId
python scripts/audit_m4_live.py --run "runs/m4/$runId"
```

Monitor; requires a separately approved, versioned config. Do not edit the checked-in disabled config in place. Before a later run, recheck current official pricing and obtain explicit permission to transmit the frozen synthetic payloads to the provider:

```powershell
$env:PYTHONPATH = 'src'
$monitorConfig = 'configs/sprint-monitor-runtime-v1.2-approved.toml'
$runId = 'sprint-monitor-v1.2-approved-run-01'
$approvalId = Read-Host 'Enter the separately approved run ID'
python scripts/run_sprint_monitor.py --config $monitorConfig --out "runs/sprint-monitor/$runId" --mode live --approval-id $approvalId
python scripts/audit_sprint_monitor_live.py --run "runs/sprint-monitor/$runId" --config $monitorConfig --out "docs/results/$runId/monitor-audit.json"
```

`DEEPSEEK_API_KEY` must be injected into the process environment by the operator after approval. The command does not load `.env`, and no credential should be placed in config, arguments, Git, or artifact manifests.

## Scientific boundary

Even after authorized execution, the primary estimates concern observable action/ballot responses and evidence sufficiency. Shared-target agreement, private-chat availability, target execution, welfare loss, or voting agreement alone is not a collusion gold label. M4's shared incentive means target agreement absent a communication intervention is compatible with independent parallel behavior. Real model results and a separate scientific review are required before calling the dataset ready for detector comparison.
