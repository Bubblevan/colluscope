# Blind scientific critic packet — B5 exact-request raw-response audit

## Question

For 48 preselected historical/current pairs with identical request-body bytes and matching reported `system_fingerprint` values, do differences in stored public-harm labels originate in raw model tool-call outputs, or in parsing/scoring/row association?

## Selection and freeze

- The preregistration was registered before parsing any raw tool-call arguments.
- Selection used all matched M4 natural-trace B5 `public_harm` case/permission rows, then required exact request-body hash and matching reported fingerprint.
- It did not use stored labels, raw arguments, evidence references, or response bytes as selection criteria.
- Assigned denominator: 24 `public_only` and 24 `privileged_audit` historical/current pairs.
- Raw request/response files are retained in Git-ignored local storage. This packet contains no request IDs, source case IDs, prompt text, response text, evidence-reference strings, or private messages.

## Sanitized independent replay results

- All 48 request/response associations and selected file hashes verified.
- All 48 raw outputs passed a strict `report_evidence` tool-call parser; no duplicate JSON keys or schema repairs.
- Raw parsed label and evidence references matched the stored prediction on both sides of all 48 pairs (48/48 historical rows and 48/48 current rows).
- Binary label matched between the two raw outputs in 29/48 pairs and differed in 19/48: 17/24 `public_only`, 2/24 `privileged_audit`.
- Full response bytes were identical in 0/48 pairs; exact argument-string bytes were identical in 18/48; canonical arguments were identical in 27/48.
- Raw evidence-reference arrays matched in 45/48 pairs: 24/24 `public_only`, 21/24 `privileged_audit` (three privileged pairs differed). No reference strings are exported.
- Exact raw-label transitions (`historical → current`) were:

  | Permission | Transitions |
  |---|---|
  | Public-only | `absent→present` 1; `insufficient_evidence→insufficient_evidence` 2; `insufficient_evidence→present` 15; `present→insufficient_evidence` 1; `present→present` 5 |
  | Privileged Audit | `absent→absent` 19; `absent→present` 1; `insufficient_evidence→present` 1; `present→present` 3 |

- The versioned v3 sanitized output hashes are JSON `3fb81e3b538cc252991b84e46e6b03f8d01ab0d931429bff1c50442adbe671ff` and CSV `2ca94b277f71dafb0d81534e9cb7b83b31ba9ab4cb99b2d4f16b2ecb44efcc62`. The CSV is unchanged from v2; v3 adds aggregate reference-equality counts to JSON. No model/API requests were used for this re-export.
- Corrected source-snapshot gate and a tamper counterexample pass. Initial preregistration and first test failures are preserved in sanitized logs.

## Current interpretation under review

The finite label disagreements are present in raw generated tool arguments and are not caused by the retained parser/scorer mapping. This verifies response-level non-repeatability for these exact historical/current observations. It does not estimate population stochasticity or prove that sampling randomness caused the differences: the provider is a mutable alias, and matching reported fingerprints do not establish identical hidden serving state. It also does not explain why the earlier within-case Public-only/Privileged predictions differed, because those view inputs differ in messages, event structure, provenance/completeness cues, and length.

The transition table sharpens, but does not broaden, that claim: 15 of the 17 Public-only label disagreements are `insufficient_evidence→present`, while the 2 privileged disagreements are one `absent→present` and one `insufficient_evidence→present`. Therefore this audit does not support describing the variation as uniformly binary false-positive/false-negative switching. Evidence references were stable in all Public-only pairs but changed in three privileged pairs; all those raw references still match the corresponding stored rows.

The output label is a deterministic public-welfare regret category, not a collusion or intent label. A deterministic rule computes it exactly from the complete public record; this result does not establish any need for an LLM on this task.

## Critic questions

1. Does the evidence support the narrow conclusion above, or is any part overstated?
2. What plausible parser, association, or serving-state alternatives remain after this audit?
3. Does this audit provide useful scientific information, or only a necessary measurement-integrity check? Would it merit a main-paper claim?
4. Given the prior 20/24 Public-to-Privileged B5 label changes, what is the smallest next experiment that can distinguish message-content sensitivity from event-structure/completeness/length effects and within-view response variability? Identify a counterexample that should force an inconclusive result.
5. Is a deterministic rule baseline sufficient for all labels examined here, and what nontrivial role, if any, remains for an LLM monitor?

The review should not infer latent collusion, intent, semantic message understanding, or population-level behavior.

## Independent audit materials

- Frozen schedule: `research/schedules/m4-b5-raw-response-repeatability-v1.json` (48 assigned pairs; its source manifest binds the raw local files).
- Analyzer: `scripts/audit_m4_b5_raw_response_repeatability.py`; adversarial tests: `tests/test_m4_b5_raw_response_repeatability.py`.
- Versioned sanitized result: `docs/results/research-sprint-20261021/raw-response-repeatability-v3/`.
- Exact replay: `python scripts/audit_m4_b5_raw_response_repeatability.py --out-dir docs/results/research-sprint-20261021/raw-response-repeatability-v3`.
- Raw response bytes and private message text remain in Git-ignored local runs. The critic should not access `runs/` or seek raw text; evaluate the claim scope, selection logic, independent parser, source-hash gate, and sanitized counts only.
