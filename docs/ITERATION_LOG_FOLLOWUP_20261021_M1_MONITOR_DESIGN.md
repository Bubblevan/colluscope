# Iteration follow-up — M1 Monitor candidate design audit (2026-10-21)

## INSPECT

The M4 B5 approval remains fully consumed: `researchctl audit` records 232 calls, USD 0.027381738, no open registered experiment, and an integrity pass. The latest user reply approved that exact scope, which is already completed; it grants no new calls for M1.

The proposed M1 package design freezes 24 unique payoff matrices, 120 episodes, 456 local Qwen generations and up to 24 additional identity HTTP checks. The older Monitor campaign draft did not distinguish physical HTTP attempts from generation calls and did not operationalize the human labels.

## SPECIFY

Adversarial counterexamples:

1. A proposal/action evaluator can appear accurate by receiving treatment, target, welfare, or reference labels in its prompt.
2. A Monitor may be said to use “local-only storage” while private text is actually transmitted to an external API.
3. A complete mapping can be misclassified by inferring an omitted task, counting a question/quotation as endorsement, or forcing an ambiguous message into a negative label.
4. The Monitor sample-size claim can undercount identity HTTP requests while describing model generations as physical requests.
5. A synthetic control set can be imbalanced, contradict its own ballot label, or be presented as natural behavior.

## IMPLEMENT / RUN

- Added a frozen candidate human codebook, exact task prompts/schemas, balanced synthetic control examples plus separate key, corrected campaign v2, and a structural offline auditor.
- Implemented a local-only privileged projection and randomized blind annotation exporter. It keeps all 96 slots in coverage, emits Task P for each delivered message, emits Task C only with a valid publicly evidenced recipient ballot, and never exposes undelivered text. The CLI has no dispatch capability.
- Implemented an independent fieldwise scorer and synthetic control request builder. It preserves missing/error rows, rejects duplicate JSON keys without repair, separates formatting from factual accuracy, validates quotes and event IDs, and exports no raw message or response text.
- `scripts/audit_m1_monitor_candidate_v1.py` passed: 12 controls (6 present, 3 ambiguous, 3 absent; concordance 3/3/6), 24 distinct matrices, 672 maximum generations, 696 physical HTTP attempts.
- The projector/scorer adversarial synthetic suite passed 13/13. It verifies denominator preservation, hidden-field exclusion, no-message handling, invalid-ballot handling, undelivered-message privacy, ballot cross-checks, treatment-trace consistency, control-key separation, fieldwise scoring, missing responses, duplicate JSON fields, and extra/missing row rejection. Real-run filesystem/ACL integration remains untested because no M1 v3 live run exists.
- Matrix freeze, independent 144-permutation audit, prompt-profile recomputation, M1 runtime `--check-only`, and research registry audit all exited 0.
- No model/API calls were made; external cost was USD 0. The raw command outputs and manifest are retained at `docs/results/research-sprint-20261021/m1-package-monitor-design-audit/`.
- One agent-authored state JSON terminator error caused a temporary registry audit failure. The exact failure is preserved and the corrected state passed the audit; no run evidence was changed.
- An attempted append to the historical risk register triggered the closed M4 hash guard. The append was removed, the frozen file restored, and new risks were moved to an append-only follow-up. The rejection is retained as evidence that the freeze is enforced.

## ADVERSARIAL REVIEW

- **No private-text concealment:** Cycle 2's DeepSeek request would externally transmit delivered private message text and the recipient's ballot. Local storage protects saved files, not transmission. The candidate explicitly requires fresh authorization naming those fields and the external provider; without that, Cycle 2 is NO-GO.
- **No hidden-label inputs:** the candidate Monitor inputs exclude condition, reward, target, payoff matrix, optimum, settlement, welfare, human reference, and other private messages.
- **No selective denominator:** all 96 message slots remain in the coverage table. Only mechanically delivered messages with a valid later ballot are model-eligible; structural no-message, failed delivery, unknown delivery, and invalid ballot rows remain separately classified.
- **No forced truth:** proposals require a unique complete assignment explicitly advocated/accepted; ambiguous and not-assessable remain explicit. Concordance compares the recipient's own ballot with the message, not the final group settlement.
- **Budget correction:** 672 is maximum generations; 696 is maximum physical HTTP attempts after adding up to 24 Cycle 1 identity checks.
- **Scientific limit:** synthetic controls check a small capability slice and cannot estimate natural-trace accuracy. M4's finite response instability remains a rival explanation for single-call Monitor errors.

## DECIDE

`DRAFT_ONLY`. The candidate is structurally auditable offline, but not registered or authorized. The previous 232-call grant cannot be reused. Before any dispatch, test the projector/scorer against a real M1 v3 run, complete the human reference procedure, and verify model/provider identity and price. Any DeepSeek scope must explicitly authorize external transfer of delivered private text and recipient ballots. Register the two experiments sequentially under the one-open-experiment rule.

## REPORT / NEXT VALUE

The strongest new finding in this design review is a governance/data-boundary fact, not a model result: a remote privileged monitor necessarily receives the private content it audits. The local compiler/scorer are now reviewable and synthetic-tested; no behavioral evidence or real-run ACL check exists yet. Do not start Agent or Monitor inference until the remaining gates and a fresh scope-specific approval pass.

## Adversarial closure — current candidate hash review (2026-10-21)

### INSPECT / SPECIFY

A fresh reviewer flagged that the stored offline `PASS` referred to earlier codebook and campaign hashes. The falsifying check was to hash the current candidate files, rerun the exact audit script with no model calls, and compare the emitted hashes with the saved log. A second challenge was whether a structural PASS was being mistaken for scientific or live-run readiness.

### IMPLEMENT / RUN

- Preserved the old `offline-validation.log`; its differing hashes remain adverse history.
- Re-ran `python scripts/audit_m1_monitor_candidate_v1.py` and saved stdout as `docs/results/research-sprint-20261021/direction-review-final/m1-monitor-candidate-audit-current-20261021.json` (SHA-256 `ef6cd883bf9ca111fff9f57811f9a1ad6b1f8fad95a0c7021a9644859d413ea7`). It passes structural checks for the *current working-tree bytes*, 12 balanced controls, 24 matrix hashes, 672 generation ceiling and 696 physical-request ceiling; it made zero model calls.
- `python scripts/researchctl.py audit` passes registry integrity: four closed cycles, no open experiment, 352 calls / USD 0.039167058 recorded, and no currently registered cycle. This is registry integrity only, not scientific validity.
- The fresh critic's follow-up confirmed the scenario-count correction but found that the candidate files were uncommitted and the audit log did not identify the current branch commit. That limitation is now recorded; after the candidate package is committed, the audit must be rerun and saved again.

### ADVERSARIAL REVIEW

No B5 mechanism was identified. Its 20/24 output changes remain bundled with added message content, event structure, visibility/provenance/completeness fields and token growth; same-input response variation remains a rival. B5 is therefore closed to more inference for the rule-computable public-harm label. The M1 v3 package remains the leading prospective behavior question, but shared-target knowledge and the added chat stage limit attribution.

The Monitor candidate is not ready for preregistration: it lacks a deterministic extraction baseline, named primary metrics and comparison rule, a named third adjudicator, and a live dispatcher. Human annotations and explicit approval to transmit private text/recipient ballots externally are also absent. No agent or monitor inference was started.

### DECIDE / REPORT

**Decision: GO for design review; NO-GO for final preregistration and dispatch.** The audit's structural PASS does not satisfy the scientific or operational gates. The one next action is a versioned offline protocol revision that resolves the metric, baseline and adjudicator gaps, followed by an audit against committed hashes. The broad low-price preference does not replace an experiment-specific run authorization or data-transfer approval.
