# M1-100 Raw Ballot Response Audit — Version 2 (2026-10-21)

**Evidence class:** offline reanalysis.  
**New model/API requests:** 0.  
**Review mode:** deterministic raw-response replay plus adversarial self-review; not an independent human Scientific Critic review.

## Why a version 2 replay was needed

The first ballot-decomposition analyzer read the runtime's `parsed_assignment` field and independently recomputed plurality. That supports settlement recomputation conditional on the stored parsed ballots, but it did not independently verify that the parser field matched each original model response. The initial version and its output remain preserved. This version reparses the raw response text using the frozen ballot object contract and accepts only the observed exact empty `<think>` wrapper before JSON. It then compares the re-parsed allocation with the stored parser field and uses the re-parsed value for settlement.

## Results

- 75/75 assigned episodes remained present and complete.
- 225/225 raw ballot responses parsed as the exact frozen ballot object.
- 225/225 raw-response assignments matched the stored `parsed_assignment` fields.
- 75/75 plurality/chair settlements recomputed from the reparsed raw ballots matched the recorded selected allocation.
- The action-level result is unchanged: 9/15 private-reward-plus-chat episodes had both A and B ballot the target and the target was selected; each other factorial cell had 0/15 joint A/B target ballots and 0/15 target selections. C's exact full ballot was invariant across the four factorial cells in 15/15 groups, C never voted target, and no target selection used a one-vote chair tie-break.

These are finite historical observations. The new matrices may have C target votes or chair-selected one-vote outcomes. A/B joint ballots remain compatible with shared-target parallel action and do not identify communication, collusion, agreement, or intent.

## Reproduction

```powershell
python scripts/analyze_m1_100_ballot_decomposition_v2.py
```

Version 2 writes sanitized outputs under `docs/results/research-sprint-20261021/m1-100-ballot-decomposition-raw-response-v2/`. Raw response text and private messages are not copied to these outputs. Version 1 results are retained under `docs/results/research-sprint-20261021/m1-100-ballot-decomposition/`; use version 2 when citing a raw-response replay.
