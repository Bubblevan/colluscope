# Versioned cycle evaluators

## Version 1

`evaluate_cycle.py` is the original frozen schema v1 gate. Its SHA-256 is
pinned in `scripts/researchctl.py`; keep its bytes and pin unchanged for prior
records and handoff imports. It checks protocol/record integrity, not
scientific truth.

## Version 2

`evaluate_cycle_v2.py` is the current versioned schema v2 gate. The CLI pins its
SHA-256 separately. It adds typed scientific outcomes, claim-level updates,
structured material-update evidence, immutable approval batch checks,
project-wide limits, and a hash-pinned request ledger with one row per physical
attempt and per-attempt approval-expiry checks.

Version 2 distinguishes a scientific outcome from an operational disposition.
It does not certify that a hypothesis was truly supported or refuted, that a
reviewer was actually independent, or that a report is novel. Those remain
scientific judgments. The critic artifact and its evidence references make
those judgments reviewable; they do not make them machine-verifiable.

No version of this evaluator executes experiments. The current repository has
no request dispatcher, so expiry/budget checks operate on registration and
terminal records. A future runner must enforce authorization and atomic budget
reservation before every request before claiming pre-dispatch safety.

Never change a versioned evaluator or its pin to make a particular record pass.
Introduce a new version, retain prior evaluators and records, document the
policy change, and review it against `docs/RESEARCH_RISK_REGISTER.md`.
