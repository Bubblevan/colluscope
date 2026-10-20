# B5 Evidence-View Stability — Decision

**Experiment:** `b5-evidence-view-stability-120`  
**Date:** 2026-10-21 (UTC)  
**Scientific outcome:** `INCONCLUSIVE`  
**Operational disposition:** `AMBIGUOUS`  
**Calls after this decision:** 0

## Decision

The authorized diagnostic ran to its frozen 120-attempt cap: 120/120 requests received HTTP 200, with no retries, replacements, identity mismatches, fingerprint drift, request/response hash failures, or external fallback. The raw run remains in the Git-ignored, current-user ACL-restricted directory. A sanitized request ledger and independently recomputed score are recorded in the evidence package.

The scientific question is **not answered**. The primary pair changed in 0/18 assessable groups, with two pairs unassessable. But the positive control failed: each of the primary Public-only and label-flip trajectories had only 10/20 exact predictions, and 0/20 groups had both exact, opposite predictions. All 40 binary outputs in those two strata were `present`, while the frozen references were balanced. Therefore the apparent 0/18 stability is compatible with a one-sided prediction rule and cannot satisfy the preregistered low-instability gate.

Registry result: `AMBIGUOUS_POSITIVE_CONTROL_FAILED`. Scientific closure: `INCONCLUSIVE`. Do not convert the project-wide 1,200-call / $2.50 approval ceiling into extra calls for this experiment: the registered cycle cap was 120 / $0.25, this experiment is complete, and its registered authorization names only this diagnostic. No further model request is included in this decision.

## Supported observations

- 120 requests were assigned and attempted; all 120 returned HTTP 200.
- All outputs had the expected alias and a constant recorded system fingerprint.
- 116 outputs had binary label `present`; none had binary label `absent`; four returned `insufficient_evidence`.
- 120/120 citations referred to event IDs present in the corresponding visible projection. This establishes membership, not semantic support.
- Independent deterministic replay matched every frozen scoring reference.
- Provider-reported usage was 113,100 prompt tokens (71,040 cache-hit; 42,060 cache-miss) and 8,772 completion tokens. The official-rate estimate is $0.01178532, not an invoice; a conservative no-cache estimate is $0.02222820.

## Claims not supported

This run does not establish B5 evidence-view invariance, evidence-view sensitivity, general Monitor competence, B5 superiority, causal message effects, real-agent behavior, or latent collusion/intent. The bundled projection changes multiple input features at once. The deterministic public-harm reference is not a collusion gold label.

## Single next action

`continue_offline`: audit the frozen prompt, tool contract, and deterministic public-harm mapping to decide whether this task reduces to a rule baseline and whether the one-sided labels indicate a framing ambiguity. Preserve the current raw run and all four uncertainty outputs. Do not issue another Monitor or Agent call without a new, scope-specific approval and preregistration.

## Review status

Adversarial self-review was performed against the frozen gates, source manifest, raw request/response hashes, positive control, denominator, and competing explanations. No independent reviewer artifact is available in this task, so the result does not count as independently reviewed material progress in the registry.
