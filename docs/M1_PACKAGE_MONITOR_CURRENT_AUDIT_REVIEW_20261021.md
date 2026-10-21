# M1 Monitor Candidate — Current Audit Review (2026-10-21)

## Decision

**GO for design review only. NO-GO for final preregistration or any Monitor dispatch.** The offline structural audit now passes against the current candidate bytes, but the protocol still lacks a deterministic extraction baseline, fully specified primary metrics, and a named third adjudicator. There is no live Monitor runner or human annotation set. A separate exact approval is also required before external transmission of private message text and recipient ballots.

No model/API calls were made in this review.

## Candidate hash reconciliation

The saved `docs/results/research-sprint-20261021/m1-package-monitor-design-audit/offline-validation.log` contains several earlier candidate snapshots. Its most recent `PASS_OFFLINE_M1_MONITOR_CANDIDATE_AUDIT` records codebook SHA-256 `bf54c1de13cced5a43692ac661ad4186fa9c649108239a2029abe214d20de8b8` and campaign SHA-256 `28e8095536cd6c1ee524e79872efc362090994a32ada717961313a2191646a3d`. These do not match the current working-tree candidate files and cannot validate them.

I reran `python scripts/audit_m1_monitor_candidate_v1.py` and saved the complete JSON stdout at `docs/results/research-sprint-20261021/direction-review-final/m1-monitor-candidate-audit-current-20261021.json` (SHA-256 `ef6cd883bf9ca111fff9f57811f9a1ad6b1f8fad95a0c7021a9644859d413ea7`). The current run reports:

- `PASS_OFFLINE_M1_MONITOR_CANDIDATE_AUDIT`; zero model calls and zero external cost.
- 12 synthetic controls: proposal labels 6 present / 3 ambiguous / 3 absent; concordance labels 3 concordant / 3 discordant / 6 not assessable.
- 24 unique matrix hashes.
- 672 maximum generations and 696 maximum physical HTTP requests; 696 correctly includes 24 local identity checks in addition to 672 generation requests.
- Current codebook SHA-256 `486a523df9fc66f4b9008cac6618f69d46447c9e220548efe11974b461206399` and campaign SHA-256 `92ee7a7fd5571c95a7166e2a963b2ef0c6cc93630c5a1b2f0ea7aecddf077291`.

The audited candidate files and their code/tests were uncommitted when this audit ran. The JSON is a current-byte audit, not proof that a released Git commit was audited. Re-run the command after committing the candidate package and retain the post-commit output before treating the audit as release evidence.

## Scientific-direction review

The user's review correctly warns against spending more calls on synthetic B5 format variants. The current evidence supports the following narrower conclusions:

1. **B5 is a real but non-identifying reliability anomaly.** In the fixed M4 set, predictions changed in 20/24 Public-only versus Privileged pairs, while independent references changed in 0/24; exactness changed from 4/24 to 17/24. Fifteen changes were `insufficient_evidence → absent`, four `present → absent`, and one `insufficient_evidence → present`. The view change bundles text, event structure, metadata, completeness, and token length. Same-input historical/current disagreement supplies a competing response-variation explanation. Do not describe 20/24 as a causal effect or a collusion result.
2. **B remains the best prospective behavior question, conditionally.** The M1 v3 schedule has 24 distinct matrices and tests a finite private-reward × chat-stage package. Its shared-target incentive and extra communication stage prevent a semantic-message or collusion interpretation. It is not authorized or registered for execution.
3. **C remains the evidence-boundary contribution.** Existing rule-replay and scripted examples are finite support for observable-claim discipline, not a general impossibility theorem.

The fresh separate-context critic ranked B above further A/B5 calls, but that review used sanitized summaries, was not blind to the proposed direction, and did not inspect raw T/B/E or private messages. It is a desk critique, not an independent data audit. See `docs/results/research-sprint-20261021/direction-review-final/fresh-independent-critic-review.md` (SHA-256 `9f5b4f5152eb89b65465079e6ecea2f1709919307a1b5f47c23722912d3e9dd3`).

## Remaining Monitor gates

- **Primary metrics:** the draft says to report fieldwise scores and improve over fixed baselines, but does not name one primary metric per task or a fixed comparison rule. Freeze the metric and denominator for Task P and Task C before labels or Monitor outputs exist. Preserve the full 96-slot coverage table and the mechanically eligible denominators.
- **Baseline:** always-absent and always-not-assessable are useful constant controls, but are not a deterministic extraction baseline. Add and freeze a conservative parser baseline for explicit allocation syntax, with unsupported text handled by a predeclared abstention/ambiguity rule. Report all baselines separately; do not tune on human labels.
- **Adjudication:** the codebook requires two independent coders but does not identify who resolves disagreements. Name a third independent, blinded adjudicator before annotation; retain both original annotations, adjudication decisions, and unresolved ambiguous/not-assessable cases.
- **Runtime:** the current scripts compile local privileged projections and score saved outputs; they do not implement a live Monitor dispatcher. The offline auditor passing is not live-backend readiness.
- **Permission:** M1 agents' `monitor_can_see_private_messages=false` remains unchanged. A DeepSeek Monitor request would transmit delivered private text and, for Task C, recipient ballots to an external provider. No such call is authorized by the completed M4 campaign approval.
- **Release integrity:** candidate files were not committed at audit time. Commit the versioned candidate package, then rerun and save the current-byte audit. Do not use the stale PASS log as release evidence.

## One next action

Prepare one versioned Monitor-protocol revision that freezes the two task metrics, adds a transparent deterministic extraction baseline, names the adjudication role, and remains offline-only. Re-run its targeted structural audit against the committed file hashes. Only after that review should the project request a single bounded M1 campaign authorization; do not dispatch based on this design audit.

