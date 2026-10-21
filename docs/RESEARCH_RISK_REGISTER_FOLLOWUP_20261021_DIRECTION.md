# Research Risk Register Follow-up — B5 Mechanism Campaign

**Date:** 2026-10-21

**Parent evidence:** `m4-b5-context-sensitivity-campaign-v1`; no new inference

**Status:** candidate design; not registered and not authorized

| Risk | Current evidence | Control in candidate design | Residual limitation |
|---|---|---|---|
| Cross-view change is ordinary same-input variation | 19/48 historical/current exact-request labels differ with matching reported fingerprints | Three identical requests for each of two views in all 24 cases; hash and interleave requests | One alias and short window; fingerprint does not pin backend weights or hidden serving state |
| Public-only vs Privileged changes are falsely attributed to message meaning | View bundles alter visibility, message text, event structure, completeness, wording, and tokens | Compare view majority changes to within-view disagreement; report the contrast as a bundle | Does not isolate message semantics |
| All-present output is label/order bias | 40/40 synthetic outputs are `present`; prior reverse arm changed prompt and enum together | 2×2 factorial independently varies prose label order and tool enum order | Fixed monitor model and finite 40-row fixture |
| Arithmetic improvement is only length/salience | Correct arithmetic achieved 39/40 but added content | Three arms: no table, correct six totals, irrelevant-number table matched in structure and tokenizer length | Token parity must be verified before registration; any mismatch must be disclosed and sensitivity-reported |
| Magnitude or matrix shift causes all-present result | M4 cell values 12–19 and positive regret 2–7; synthetic values 46–92 and regret 53–200 | Multiply each of the same 24 M4 matrices by five; hold ballots and outcome fixed | Only scale is isolated; regret separation and broader task distribution remain different |
| Task language conflates welfare with collusion | System prompt warns against inferring collusion from welfare loss; task asks about welfare regret | Separate explicit definition says the label is only an observable welfare comparison | Does not prove what the model internally interpreted |
| Deterministic label makes Monitor inference unnecessary | Rule exact on 24/24 natural M4 cases and 40/40 synthetic rows | Keep code as reference and report LLM only as a prediction; paper gate requires a validated nontrivial language-monitor role | Current campaign may conclude no LLM contribution on this task |
| Private evidence is sent to external service | Existing privileged requests include private messages | Restrict schedule to 72 Privileged-original repeated requests, record 144 event appearances, preserve raw bytes only locally | Requires explicit approval for the exact transfer boundary and secure local storage |
| Budget or price drift | Previous 232-attempt grant is consumed; remaining budget is finite and price varies | New approval for ≤728 attempts/$1.95, off-peak only; cost reservation per request; stop before call if price/identity/token gate fails | Alias remains provider-controlled; campaign can terminate inconclusively |
| Selective reporting or denominator changes | Prior temptation to report only stable or valid cases | Freeze all 728 assignments; zero replacements; retain failures and invalid outputs; publish every numerator/denominator | Small finite sample; no population-level inference |

The campaign only earns a paper-level claim if the results discriminate at least one prespecified rival explanation and the deterministic baseline is reported. A passing schema, HTTP run, or synthetic control is not a scientific GO.
