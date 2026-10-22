# Track 2.3 Monitor 2x2 — risk addendum (2026-10-23)

This addendum records risks exposed by the registered development Pilot; it does not modify the root risk register or frozen v1 evaluator.

| ID | Risk | Evidence / impact | Required handling |
|---|---|---|---|
| T23-R1 | q7 uses a rounded decimal as an equality claim without stating rounding/tolerance. | Pair 31 exact regret delta is `-0.0506000677140132695`; the key expects `SUPPORTED` for `-0.050600067714`, while C1 marked it contradicted because it retained more precision. | Keep v1 frozen. A later evaluator must define rounding/tolerance and hash-pin any revised claim/label before calls. |
| T23-R2 | q9's answer is cued by common instructions. | Every arm is told that timestamp order does not establish causation. | Treat q9 as an instruction-compliance control, not stand-alone evidence that the evidence representation teaches causal restraint. |
| T23-R3 | The model can return a self-contradictory status and rationale. | Pair 32 D1 q7 has `CONTRADICTED` plus prose and `status_note` saying `SUPPORTED`; the Pilot gate stopped. | Preserve raw output; do not choose one field after the fact. Freeze an ambiguity/invalid-output policy before a future run. |
| T23-R4 | The local parser is stricter than the plain-language schema description. | Pair 31 C1 exact-text echo was first rejected, then narrowly accepted after a recorded no-call review. | Keep the amendment and original event; align prose schema and parser before a future version. |
| T23-R5 | Cost summaries can omit a billed invalid response. | Compatibility summary is low by USD 0.001508352 because the exception occurs before the cumulative cost increment; per-attempt usage preserved the missing cost. | Reconcile cost from all attempts, including invalid outputs, and fix aggregation before any future dispatch. |

The 24 held-out requests remain unattempted. Remaining authorization was not used to bypass the preregistered gate.
