# Independent critical review: shared-target message-content V1

- **Review date:** 2026-10-21
- **Review mode:** Independent subagent review of the supplied sanitized artifacts and manuscript; no model/provider calls and no file edits by the reviewer.
- **Verdict:** `SUPPORTED` for the narrow finite message-mapping response claim.

## Claim under review

In the three frozen allocation contexts served under the reported `deepseek-flash` alias, changing the allocation mapping in a researcher-scripted message changed the recipient's ballot to match that mapping.

## Evidence and scope

The preregistered pattern appears in all three contexts: visible-target/no-message ballots selected the target 6/6; hidden-target/no-message ballots selected neither target nor decoy (0/6 each); true-message ballots selected the target 6/6; and counterfactual-decoy-message ballots selected the decoy 6/6. All 24 assigned requests were completed and assessable, with no repeat disagreement. The 24 requests are nested in three contexts; repeats indicate response stability, not independent model instances or a population sample.

This result supports message-content response under these prompts and weakens shared-incentive-only choice as a complete explanation of these mapped ballots. It does not demonstrate spontaneous sender behavior, peer-specific social influence, an agreement, collusion, intent, harm, or generalization beyond these contexts and this provider-served alias.

## Adversarial findings

- **Novelty:** Existing literature already studies LLM collusion benchmarks and controlled communication interventions, including Colosseum, Cheap Talk, and long-horizon peer-intervention work. The defensible increment is narrower: a hidden-target allocation setting with a counterfactual false-mapping message that produces a target/decoy ballot reversal under a fixed shared incentive.
- **Strongest rival:** Generic recommendation or instruction following remains fully compatible. The separate source-framing study found similar mapping adherence under peer and task-aide labels (161/192 versus 168/192), with no preregistered peer advantage.
- **Causal identification:** The within-message true-versus-decoy mapping contrast is the informative contrast; the no-message arms are context controls. Message presence versus no message also changes text and length, so it should not be described as an isolated presence effect.
- **Labels and leakage:** Ballot-to-mapping agreement is an observable action label, not an intent or collusion label. The protocol reports token parity and hidden-target leakage checks, but the supplied sanitized package omits full prompts and raw response text, preventing independent verification of those checks and ballot reparsing.
- **Baseline and identity:** The design includes visible-target and hidden-target no-message controls. The provider alias and reported fingerprint identify this run, not immutable model weights.

## What could change the verdict

A raw-input/output audit showing that the true and decoy prompts differed outside the registered mapping, that the hidden target leaked elsewhere, or that assignment/parsing was wrong would undermine the claim. A peer-specific influence claim would require a source comparison holding the mapping and wording constant.

## One next test

The most direct next test is the proposed 30-request source contrast described in the content V1 closure: peer-proposal versus content-matched task-aide recommendations for target and decoy mappings, plus a hidden/no-message baseline, in three frozen contexts with two repeats per cell. It requires a fresh exact-scope authorization. It would test source sensitivity against generic recommendation following; it would not establish collusion or intent.

## Review boundary

This review is independent of the author-side analysis but is not an independent raw-byte audit. It reviewed the preregistration, closure, sanitized analysis and ledger, interpretation, manuscript, research memory, risk register, and cited related-work claims. Raw prompts/responses were unavailable in the review packet.
