---
name: result-interpretation
description: Interpret ColluScope outcomes, failures, denominators, and evidence limits without reducing them to a score.
---

# Result interpretation for ColluScope

Use this after an experiment, offline replay, or engineering gate reaches a
terminal state. Read its preregistration, complete assigned-row ledger,
independent audit, `research/memory.json`, and relevant risk entries.

## Required output

1. Report assigned, started, attempted, completed, assessable, failed, and
   unstarted counts separately where they apply.
2. Assign exactly one typed scientific outcome: `SUPPORTED`, `REFUTED`,
   `INCONCLUSIVE`, `INVALID_EXPERIMENT`, `EXECUTION_BLOCKED`, or
   `RESOURCE_BLOCKED`. Record operational review disposition separately.
3. State what observation changed, what it rules out, which alternatives remain,
   and what failure or missingness could change the interpretation.
4. Recompute the primary outcome from hash-pinned inputs where feasible. Keep
   synthetic controls, real-agent behavior, engineering preflight, monitor
   evaluation, and offline reanalysis separate.
5. Update claim-level research memory with cited evidence and one next action.
   A successful parser or integrity gate is not a scientific result.

## Example anchor

The separate 856-row Monitor run has 715 outputs ending at a 128-token length
cap and no common completed-and-assessable B4/B5 pairs. Its method contrast is
not estimable. Keep it separate from the 628-request DeepSeek-first run, which
has 126 assessable pairs; never combine their denominators to make a larger
sample.

Preserve all invalid rows and failure histories. Never repair output after
seeing the result, infer latent intent from observable behavior, or call a
provider without separate current authorization.
