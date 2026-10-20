# Research registry

The registry supports a persistent Codex `/goal` research cycle. The Goal is
the reasoning and continuation driver; this CLI records state and checks
provenance. It never executes an experiment, a registered command, a model call,
or arbitrary shell code.

## Current state

- `state.json` records the active cycle and continuation step.
- `memory.json` preserves claim-level beliefs, scope, and hash-pinned evidence.
- `hypotheses.json` holds at most three competing read-only candidate
  directions; only one can be selected for a formal cycle.
- `budget.json` holds the zero-call current authorization and project-wide
  ceiling. Immutable approval records, if separately authorized in the future,
  belong in `authorizations/<APPROVAL_ID>.json`.
- `handoffs/DEEPSEEK-FIRST-RESEARCH-01.json` is the terminal historical
  628-request closeout. Its approval is consumed. The separate 856-row Monitor
  result remains linked from state and research memory; neither run is merged
  with new cycles or with each other.

## Cycle records

New experiments are stored as
`experiments/<ID>/preregistration.json` and, after terminal review,
`experiments/<ID>/closure.json`; a `registration.json` sidecar pins their
preregistration hash and, after closure, its terminal hash. CLI writes are
serialized through an ignored cross-process registry lock. Current preregistration and closure records
use schema version 2 and the versioned evaluator
`frozen_eval/evaluate_cycle_v2.py`. The original schema v1 evaluator remains
unchanged at `frozen_eval/evaluate_cycle.py` for prior records and handoff
imports.

Scientific outcomes (`SUPPORTED`, `REFUTED`, `INCONCLUSIVE`,
`INVALID_EXPERIMENT`, `EXECUTION_BLOCKED`, `RESOURCE_BLOCKED`) are stored
separately from operational review disposition. A normal scientific outcome
does not complete the Goal. Closure records carry claim-level belief updates;
`memory.json` mirrors those updates and can be rebuilt from closed cycles.

Each approval batch has its own call/cost cap and expiry. A cycle's full
preregistered ceiling reserves capacity within that batch and within the
project-wide cumulative limit. Closures with physical model/API attempts must
include a hash-pinned sanitized request ledger, with a row for every attempt,
including failures. The evaluator verifies ledger row counts, costs, grant
scope, and per-attempt expiry timestamps. These are record checks, not
pre-dispatch controls; there is no runner today.

## Commands

```powershell
python scripts/researchctl.py status
python scripts/researchctl.py next
python scripts/researchctl.py import-closeout <sanitized-packet.json>
python scripts/researchctl.py register <preregistration-v2.json>
python scripts/researchctl.py close <closure-v2.json>
python scripts/researchctl.py audit
python scripts/researchctl.py sync-memory
```

`next` prints one required continuation step and does not dispatch it.
`sync-memory` rebuilds the cycle-memory projection from terminal closure files;
it does not change scientific outcomes. `audit` validates registry integrity,
hashes, denominators, grants, request ledgers, memory links, and total ceilings.
None of these commands certifies a scientific conclusion.

`protocol.reproduction_command` is inert audit text. A future runner may only
call an explicitly allowlisted experiment entry point; the current CLI does not
interpret command strings. Any runner must add an atomic pre-request budget
reservation before it can make paid or live calls.

Store raw requests, private messages, credentials, and local identity records
only in existing ignored and ACL-restricted locations. Register reviewed,
sanitized artifacts. Never promote evidence class or infer collusion/intent
from treatment, agreement, channel availability, welfare harm, or monitor
scores alone.
