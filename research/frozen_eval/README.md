# Frozen cycle evaluator

`evaluate_cycle.py` is a standard-library-only gate for preregistration and
closure records. It checks evidence-class consistency, hashes, denominators,
retained-failure declaration, recorded resource use, reviewer disposition,
and the single-next-action contract. It does not score ColluScope behavior,
label collusion, certify an effect, or replace the existing source-pinned
experiment auditors.

Treat this evaluator as frozen policy. To revise it, create a new version,
retain the old evaluator and its records, document why the gate changes, and
review the change against `docs/RESEARCH_RISK_REGISTER.md`. The CLI pins this
file's SHA-256 before importing it. Never change the evaluator or its pin to
make a particular experiment pass.
