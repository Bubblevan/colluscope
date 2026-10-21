# Iteration Log Follow-up — M4 Repeatability Profile Clustering

- **Date:** 2026-10-21
- **Iteration:** audit the prepared repeatability denominator before registration
- **New model/API calls:** 0
- **Scientific outcome:** no new model-behavior outcome; candidate protocol correction required

## OBSERVE

The selected `m4-b5-view-repeatability-v2` candidate was prepared for 144 requests across 24 contexts and two views. Its earlier audit grouped rows by `(context hash, view)` and verified three equal request bodies in each of 48 cells. It did not count distinct request bodies across contexts.

## EXPLAIN

A hash-only audit of the prepared manifest found 47 unique model-visible request bodies: 23 Public-only and 24 Privileged-original. One Public-only body is shared by two different source-context hashes and receives six assignments. All other body profiles receive three assignments. No body is shared across the two views.

This creates a concrete dependence risk: the candidate's 24 context comparisons reuse one Public-only input as the control for two different privileged views. Counting both as independent evidence could overstate the number of distinct input-level contrasts. A second competing explanation remains the already observed response variation for identical request bodies; this structural finding does not show how any new response will behave.

## SELECT / SPECIFY

Retain the same 144 request assignments and frozen schedule, but change the planned primary unit before any registration or output: aggregate repeat behavior by unique body hash, form 23 Public-only profile clusters, and count the shared Public-only control once. Preserve all 24 context-pair transitions as secondary descriptive results with the shared-control link marked. A falsifying counterexample would be any body-hash collision missed by the revised auditor, or any future scoring output that counts the same public profile twice in its primary gate.

## IMPLEMENT / RUN

Updated the read-only preparation auditor to count unique bodies and cross-context collisions. The profile-aware replay returned `PASS_OFFLINE_PREPARATION_PROFILE_AWARE_AUDIT`: 144/144 body hashes verified, 48 context/view assignments, 47 unique bodies, 23/24 unique profiles by view, one public duplicate linking two contexts, 46 profiles with three assignments, and one with six. The fixed schedule and request-manifest hashes are unchanged. The first exploratory one-to-one join failure is retained at `docs/results/research-sprint-20261021/m4-b5-profile-collision-audit-20261021/initial-body-hash-join-failure.log`; corrected mapping is one-to-many.

Created `research/drafts/m4-b5-view-repeatability-v2-preregistration-r1.json` with profile-cluster denominators and gates. The original unregistered draft and prior v3 audit remain unchanged. No provider request was sent.

The first read-only schema check found that the revision had not copied the required `protocol.frozen_inputs` field; this was corrected and the initial validation failure was retained. The corrected validator then found only the expected `approval_id` requirement for a nonzero-call protocol. The candidate therefore remains unregistered until a fresh named authorization exists; the validation receipt is retained under `docs/results/research-sprint-20261021/m4-b5-profile-collision-audit-20261021/`.

## ADVERSARIAL REVIEW

The finding is limited to exact prepared request bytes and hash-only schedule identities. It supports a finite input-projection fact, not natural-agent behavior, monitor accuracy, message comprehension, or collusion. The primary analysis still compares bundled Public-only and Privileged-original packages. The auditor reads restricted request bodies locally to hash and inspect keys, but emits no messages or prompt text. This is an adversarial self-review, not an independent critic assessment.

## DECIDE / REPORT

The previous 144-call profile-blind draft is not ready for registration. The profile-aware revision preserves all assignments and controls the duplicated baseline in its analysis. The prior 232-call campaign authorization is consumed and does not cover the 144-call candidate. No model/API calls were made in this iteration.

**Exactly one next action:** obtain a new scope-specific approval for the revised `m4-b5-view-repeatability-v2` candidate (≤144 physical attempts, ≤$0.35, official DeepSeek Flash off-peak only, zero retries/replacements, expiry, and explicit transfer of 144 private-message event appearances); only then register the hash-pinned revision and rerun live pre-dispatch gates.
