# Independent Scientific Critic Review — B5 Direction Refocus

**Verdict:** A is **refuted as the next primary paper direction**, but the critic recommends a small repeatability gate if we retain it as a validity concern.
**Review type:** sanitized, separate-context, read-only desk review; not blind to the repository's prior selection of B.
**Model/API calls, tests, edits:** 0 / 0 / 0.

## Reviewer assessment

The cause of B5 response variation remains inconclusive. The historical M4 comparison changed 20/24 labels, but the 232-request campaign did not separate semantic content, evidence packaging, token length, provenance cues, or provider variation. Exact request bytes with matching reported fingerprints still disagreed on 19/48 labels (17/24 Public-only; 2/24 Privileged-original), and only 7/24 case-level historical/campaign Public→Privileged transitions recurred.

The completed campaign's A1 changed labels on 12/24 Public→Neutral, 20/24 Neutral→Original, and 19/24 Public→Original comparisons. A2 production B5 predicted 35 `present` and 5 `insufficient_evidence` on the 40 balanced rows, scoring 20/40. Thus the all-`present` collapse from the earlier 120-request diagnostic did not reproduce identically in the later production-form campaign; neither run identifies its cause.

The balanced B5 controls further weaken A as a standalone contribution: the 120-request fixture predicted `present` on all 40 balanced rows (20/40 exact), while the deterministic rule matched 40/40 synthetic and 24/24 real M4 references. The 20/24 change remains a useful monitor-reliability observation, but this public-harm task does not show a distinctive need for an LLM.

The reviewer considered B to have greater empirical paper potential because it concerns real agent behavior: target execution was observed in 9/15 private-reward-plus-chat groups versus 0/15 in each other 2×2 cell. However, shared target knowledge and the extra chat stage remain confounds; M3 also does not isolate message meaning. B must be prospectively replicated and cannot support a collusion or intent claim.

C is a useful Track 2.3 claim framework, but the 12-pair scripted audit is a finite construction: equal Public-only projections in 12/12 pairs, determinate sequence differences in 8/12, and complete sequence differences in 2/12. It is not a general impossibility result or standalone Monitor-accuracy result.

## Recommended next test

If A is reopened, use an interleaved repeatability screen on the same 24 cases: Public-only and Privileged-original, three byte-identical requests per view (144 requests), randomized/interleaved within case. Compare within-view disagreement with per-case view-majority changes and score each output against the frozen deterministic reference. Continue with A only if the directional view change recurs and exceeds within-view variation. Even then, this does not isolate private-message meaning from event packaging.

The present campaign proposal adds a separate 320-request factorial because the all-`present` diagnosis has another unresolved defect: the earlier large output change reversed prompt order and tool-enum order together. Crossing those factors independently is the minimal counterexample test for that bundled explanation.

## Strongest counterexample and scope limits

The main counterexample to a coordination interpretation is M1-100 episode 013: positive welfare regret occurred under normal cooperation without private communication or target execution. The 9/15 M1 interaction remains compatible with independent action on a shared rewarded target.

The reviewer was not blind to the previously selected B hypothesis. It did not inspect protected raw message/request payloads, independently replay data, run tests, or make API calls. Treat this as a separate-context scientific desk critique, not raw-data validation, blinded confirmation, or a registry-qualified external review.
