---
name: experiment-audit
description: Audit ColluScope preregistrations, evidence provenance, denominators, failures, budgets, and claim scope.
---

# Experiment audit for ColluScope

1. Read the registered protocol and current budget before looking at outcome
   scores. Confirm the evidence class and all frozen input hashes.
2. Distinguish assigned, started, attempted, completed, assessable, and failed
   rows. Reconcile raw request/response or deterministic replay receipts where
   permitted. Do not delete failures or silently repair outputs.
3. Check source/model/runtime identity, split integrity, permission boundaries,
   label leakage, duplicate units, paired coverage, and actual calls/cost.
4. Verify the independent audit against raw bytes or deterministic source data
   where available. A parser/transport pass does not establish behavior; a
   citation match does not establish factual support.
5. Attack the strongest conclusion with a shared-incentive, alternative
   mechanism, abstention, missingness, or privacy counterexample.
6. Write the closure record with `PASS`, `FAIL`, `AMBIGUOUS`, `BLOCKED`, or
   `PIVOT`, retain all adverse evidence, and state exactly one next action.
7. Run `python scripts/researchctl.py audit` after recording a closure. This
   audits registry integrity only; scientific validity still requires review.

Never call a live model or provider as part of an audit without separate
explicit authorization. Do not edit `research/frozen_eval/` to make a record
pass; propose a versioned evaluator change and preserve the earlier result.
