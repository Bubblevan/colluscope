# B5 Post-close Offline Audit: Public-Harm Rule Baseline

**Status:** post-close exploratory offline reanalysis; no model calls  
**Evidence class:** `offline_reanalysis`  
**Source cycle:** `b5-evidence-view-stability-120`

## Purpose

The terminal B5 report selected one next action: audit whether the frozen task wording and deterministic public-harm mapping make the task solvable by a simple rule. This addendum executes that no-call action. It does not amend the preregistered primary outcome or the already closed cycle.

## Independent replay

`scripts/audit_b5_deterministic_rule_baseline.py` independently implements assignment parsing, plurality settlement, the chair tie-break, welfare over all six task permutations, and the public-harm label. It reads only the frozen synthetic public evidence and raw monitor labels. It checks the replay against the source manifest and never exports request/response payloads or group IDs.

| Public-canonical trajectory | N | Reference present / absent | Deterministic rule exact | Monitor present / absent | Monitor exact |
|---|---:|---:|---:|---:|---:|
| Primary | 20 | 10 / 10 | 20/20 | 20 / 0 | 10/20 |
| Label-flip positive control | 20 | 10 / 10 | 20/20 | 20 / 0 | 10/20 |
| **Combined** | **40** | **20 / 20** | **40/40** | **40 / 0** | **20/40** |

For this exact synthetic task, the visible quality matrix, complete ballots, voting rule, and recorded outcome are a sufficient statistic for the score label. A deterministic calculation recovers all 40 references. The Monitor emitted only `present`, so it has 100% recall on `present` and 0% specificity on `absent` in this 40-row descriptive set. This is a property of this finite fixture and run, not a population estimate.

## Research implication

The task is useful as a deterministic rule-control and label-flip check, but it does not demonstrate general evidence-auditing ability. In particular, the exact primary `0/18` label-change count is explained by constant-positive predictions and cannot establish low sensitivity to the evidence projection. The perfect deterministic baseline is not a collusion detector and does not identify intent.

Any future Monitor study should ask about a materially different observable claim—such as whether a complete proposal/acceptance/action sequence is present in the permitted view—and should include rule-checkable positive and negative controls. That is a new experiment and requires a new preregistration and explicit authorization before any inference. No additional calls are made here.

## Reproduction

```powershell
python scripts/audit_b5_deterministic_rule_baseline.py --out docs/results/research-sprint-20261021/b5-deterministic-rule-baseline.json
```

The output pins the V2 source-manifest, frozen schedule, and local `results.jsonl` hashes. The raw run remains Git-ignored and ACL-restricted.
