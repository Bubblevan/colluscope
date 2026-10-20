# M4 B5 Context-Sensitivity Campaign — Decision

**Decision:** `AMBIGUOUS`
**Scientific outcome:** `INCONCLUSIVE`
**Operational outcome:** registered campaign completed; independent raw replay passed
**Authorization:** consumed; no further model requests authorized by this grant.

## What the evidence supports

The frozen 232-request campaign completed without execution failures, retry, or replacement. Independent replay verified the request schedule, hashes, source bindings, references, responses, and all terminal rows. On the 24 fixed A1 contexts, labels changed in 12/24 Public-only→Neutral pairs, 20/24 Neutral→Original pairs, and 19/24 Public-only→Original pairs. The preregistered directional gate was not met. The repeated exact input-pair profile varied, so the registered duplicate-sensitivity qualification also applies.

A post-hoc comparison found identical request-body bytes and identical reported system fingerprints in 24 historical/current pairs for each of Public-only and Privileged-original. Labels matched only 7/24 and 22/24 respectively. That observation is compatible with finite provider/model response non-repeatability; it cannot explain the cause or prove hidden serving state was otherwise identical. It means the observed cross-view label differences cannot be cleanly attributed to one input component from these single-call comparisons.

The A2 arithmetic and label-order arms show finite request-presentation sensitivity. The arithmetic table makes the deterministic target calculable from visible values, while the reverse-order arm bundled changes to both the prompt and enum. Neither arm supports claims of independent LLM reasoning or general monitor capability.

## What the evidence does not support

This campaign does **not** establish that the model understood the private-message semantics, that a monitor detects collusion, that the historical 20/24 contrast has been explained, or that any causal effect generalizes beyond these exact requests. `public_harm` is a mechanically reconstructed observable label, not a collusion/intent ground truth. The serving model is a mutable alias, not a pinned weight artifact.

The campaign therefore receives an operational integrity pass but a scientific `AMBIGUOUS / INCONCLUSIVE` decision. Passing transport, schema and hash checks does not upgrade the scientific result.

## Most valuable next research action

Stop model inference for this line until a new proposal is reviewed. If this question remains important, preregister a compact repeated-request design that interleaves exact duplicate requests within every view and across views, preserving the full request bytes and randomization order. This is needed to estimate within-request response variability before interpreting view contrasts. Keep A1's original/neutral token-length and wording confounds explicit; a future design must address them prospectively. Do not spend more calls on the existing A2 fixture unless a new falsifiable question is identified.

Any such work requires a new authorization with a fixed endpoint/model alias, request count, cost ceiling, expiry, and a registered protocol. No model call is made or authorized by this decision. Until then, continue only with offline analysis and manuscript correction.

## Reproduction and artifacts

```powershell
python scripts/audit_m4_b5_context_sensitivity_run.py
python -m pytest -q tests/test_m4_b5_context_sensitivity_audit.py tests/test_m4_b5_context_sensitivity_runner.py
python scripts/researchctl.py audit
```

The full counts, hashes, token deltas, row-level sanitized output, failure history, and independent critic scope are recorded in [`M4_B5_CONTEXT_SENSITIVITY_EVIDENCE.md`](M4_B5_CONTEXT_SENSITIVITY_EVIDENCE.md) and the linked audit artifacts. Raw request/response bytes and private-message contents remain in the local Git-ignored restricted run directory.
