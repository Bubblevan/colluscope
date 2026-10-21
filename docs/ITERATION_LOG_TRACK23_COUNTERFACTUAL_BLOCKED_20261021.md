# Track 2.3 counterfactual-delivery pilot — execution blocked

- **Date:** 2026-10-21 (Asia/Shanghai)
- **Experiment:** `track23-counterfactual-delivery-v1`
- **Authorization:** `DS-FLASH-TRACK23-900-20261021` (closed and non-reusable)
- **Scientific outcome:** `EXECUTION_BLOCKED`

## Result

The pilot assigned 56 requests. One physical attempt started and terminalized as
`TRANSPORT_ERROR` before an HTTP response; zero model responses, valid actions,
or assessable contexts were produced. Fifty-five assigned requests remained
unstarted. Python `socket.getaddrinfo` failed while the PowerShell DNS resolver
returned records. Execution stopped after this first failure under the frozen
no-retry rule. No custom transport or resolver workaround was attempted.

This is an execution failure, not a behavioral null. It provides no evidence
for or against message-mediated action and does not change the prior
communication-causality assessment. The attempt ledger and blocked-pilot
record are retained under `docs/results/track23-counterfactual-delivery-v1/`;
the closure is recorded in
`research/experiments/track23-counterfactual-delivery-v1/closure.json`.

## Budget and next action

The project-wide cumulative ceiling is 4,800 model calls and $2.50. This
cycle's separate 900-attempt/$1.80 authorization is closed; its one attempted
call is included in cumulative usage. The live execution path is stopped.
Continue with offline integration of the existing M1/M3/M4 evidence and this
execution boundary into the Track 2.3 paper. Do not retry the assigned request.
