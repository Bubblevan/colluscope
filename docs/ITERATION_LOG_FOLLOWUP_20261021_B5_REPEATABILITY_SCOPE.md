# Iteration follow-up — M4 B5 scope reduction

**Date:** 2026-10-21
**Evidence class:** offline reanalysis and protocol preparation
**Model/API attempts:** 0
**Decision:** prepare one 144-attempt repeatability candidate; no registration or dispatch.

## INSPECT

The user's reply approved only `m4-b5-context-sensitivity-campaign-v1`, with a 232-attempt / USD 0.90 ceiling. The registered campaign is already closed: 232 attempts, USD 0.027381738 actual cost, no retries/replacements, scientific outcome `INCONCLUSIVE`. Its approval is consumed. The state and closure confirm that a separate 464-attempt proposal is not included in that approval.

## SPECIFY

The useful unresolved M4 question is whether the finite Public-only versus Privileged-original label contrast exceeds same-view response variation. A separate synthetic prompt-order × tool-enum factorial answers a different question and is not needed to resolve this interpretive blocker. The counterexample is straightforward: exact repeated requests within a view vary as much as the cross-view majority labels, or the earlier cross-view contrast does not recur.

## IMPLEMENT / RUN

Prepared a hash-only 24-context × 2-view × 3-repeat schedule, deterministic shuffle seed `20261022`, for 144 assigned requests. The schedule builder verifies paired context coverage and unique assignment IDs; its output excludes payloads, references, raw case IDs, and private messages. It is marked `draft_not_registered_not_authorized`. Schedule SHA-256: `37cce3e98a0493cb26e6610cdc823aa5cc7a1303086f7943ed269b895441e099`. Reproduction: `python scripts/freeze_m4_b5_view_repeatability_v2.py`.

This iteration made zero provider requests. It did not read or copy private message bodies. Candidate budget is 144 physical attempts, zero retries/replacements, and USD 0.35 maximum, with an off-peak recheck required before registration. Privileged prompts would transmit 144 private-message event appearances; separate explicit authorization is required.

## ADVERSARIAL REVIEW

- The two views differ in more than message meaning: permission, event inclusion/metadata, serialization, wording, and token length remain bundled. A stable contrast would be a response difference between evidence packages, not semantic comprehension or causality.
- Three repetitions per context/view permit a descriptive unique-mode comparison but do not establish population-level stochasticity or provider-internal state.
- A mutable model alias and matching reported fingerprints do not guarantee identical weights or hidden serving state.
- Failed, malformed, interrupted, or unstarted slots must remain in the 144 assigned denominator; the proposed runner is not yet implemented.
- The prior A1 neutral arm and 320-request synthetic order factorial are deliberately deferred; they are not silently counted as part of this candidate.

## DECIDE

The prior 232-attempt approval cannot be reused. Keep the long-term research program active and the new candidate unregistered. Before any run, implement and offline-audit an append-only runner, recheck official model/pricing/window identity, and obtain new explicit authorization for this exact experiment and the stated private-text transfer.

## REPORT

The next single action is to implement and offline-audit the bounded repeatability runner for the frozen hash-only schedule. No additional scientific conclusion is claimed by this protocol refinement.
