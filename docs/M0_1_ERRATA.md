# M0.1 Errata for the Frozen M0 Report

This note corrects two research-validity issues found in the independent review of commit `190ea3c`. It does not edit or regenerate the frozen M0 report, source snapshot, run directories, or hashes. This errata supersedes only the interpretations below when reading the M0 package.

## E1 — coalition proxy at the public optimum

[`world.py`](../src/colluscope/world.py) defines:

```text
coalition_value = 3 * I(A=T3) + I(B=T2)
```

The coalition target `(A=T3, B=T2, C=T1)` has proxy value **4**. The public optimum `(A=T1, B=T2, C=T3)` has proxy value **1**, not 0. The proxy difference is therefore **3 units**. Public team welfare is 14 at the target and 28 at the optimum, a 14-unit loss.

The sentence in the frozen [`M0_EVIDENCE.md`](M0_EVIDENCE.md) saying the proxy is 0 at the public optimum is incorrect. The code and oracle values are unchanged. More fundamentally, `coalition_value` is a script-side proxy; it is not a reward function delivered to an agent, does not specify an agent observation, and cannot show that a model would prefer or act on the target.

M0.1 tests assert the exact proxy and welfare values and separately check draft score arithmetic. No reward has been delivered to an agent. M1's draft incentive schedule is defined separately in `M1_PILOT_TRD.md` and `configs/m1-pilot-draft.toml`.

## E2 — direct C2 treatment language

The frozen M0 C2 trace includes “no agent-specific agreement is recorded” and “I independently follow ... as a simple heuristic.” These phrases disclose the construction label directly to a text-view monitor. The frozen traces remain intact so this failure is auditable.

The M0.1 generator changes only future/newly generated scripted text to neutral wording. Tests assert that the earlier phrases are caught as counterexamples and absent from all current case text. The C2 construction truth remains in the separate oracle; no label or case count is changed.
