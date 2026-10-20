# Research registry

`state.json` is the current handoff projection. `budget.json` is the current
authorization snapshot. New experiments are stored as
`experiments/<ID>/preregistration.json` and, after a terminal review,
`experiments/<ID>/closure.json`. The CLI never starts an experiment.

The registry is intentionally empty at bootstrap: the separate in-progress
Codex task named by the user has no verified terminal artifact in this
checkout. Import only its sanitized closeout after it finishes; do not invent
a starting hypothesis from a provisional result.

Use `python scripts/researchctl.py status` to inspect state,
`python scripts/researchctl.py import-closeout <file>` to import a terminal
sanitized result from the separate in-progress Codex task,
`python scripts/researchctl.py register <file>` to validate and freeze a
preregistration, `python scripts/researchctl.py close <file>` to validate and
record a terminal review, and `python scripts/researchctl.py audit` to check
the ledger and hashes. The frozen evaluator checks protocol/record integrity;
it does not certify scientific validity.

`import-closeout` records a completed prior run without falsely preregistering
it after the fact. Its historical calls are explicitly excluded from the new
cycle authorization. The imported packet must point to hash-pinned sanitized
protocol, result, and independent-audit files; raw data paths are rejected.
The packet uses `schema_version`, `handoff_id`, `title`, `terminal_decision`,
`evidence_classes`, one `evidence_summaries` entry per class (each with a
summary and denominator), `terminal_summary`, `preregistration_refs`,
`sanitized_artifacts` (role/path/SHA-256), historical call/cost totals,
`authorization_status`, `raw_data_local_only: true`, limitations, and one
recommended next action. The evaluator rejects summaries that combine or omit
an evidence class.

## Record fields

A preregistration JSON uses schema version 1 and includes:

- `experiment_id`, `title`, `evidence_class`, research question, hypothesis,
  at least one competing explanation, and hash-pinned prior evidence;
- `protocol`: sample selection, intervention, held-constant factors, primary
  outcome, denominator, success/failure/ambiguous gates, analysis plan,
  reproducible command, runtime identity, and hash-pinned frozen inputs;
- `budget`: maximum calls, external spend, and wall-clock minutes; and
  `authorization`: whether approval is required, its ID if already granted,
  and the exact scope. A registration is never approval.
- optionally `closes_current_handoff: true` when the registered artifact is the
  terminal closeout for the separate task recorded in `state.json`.

A closure JSON must preserve the evidence class and record the decision,
observations, denominator, scientific update, actual calls/cost, retained
failures, actual wall-clock time, review mode/finding, hash-pinned sanitized
outputs, and exactly one next action with its evidence class, budget, and
approval requirement. For
`review_mode: independent`, include a hash-pinned `review_artifact`.

Paths under `runs/`, `logs/`, `reference/`, `.git/`, `.aws/`, `.codex/`, or
`.env` are rejected. Store raw requests, private messages, credentials, and local identity records only in
the existing ignored and access-controlled locations; register sanitized
reviewable artifacts instead. Historical calls do not count as current
authorization and must remain linked to their existing run records.
