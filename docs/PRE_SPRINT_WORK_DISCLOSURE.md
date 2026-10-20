# Pre-sprint Work Disclosure and Provenance

**Disclosure frozen:** 2026-10-20. The official Sprint page says the event starts 23 October 2026. Nothing in this package changes historical timestamps, run IDs, seeds, model responses or commit history.

## Work completed before Sprint opening

| Workstream | Existing provenance | Nature of evidence | Must be described as |
|---|---|---|---|
| M0 | Scripted 24-case offline benchmark; final report and run evidence dated 18 October 2026. | Deterministic traces, views, and oracle constructions. No model inference. | Pre-sprint software/identifiability controls, not LLM behavior or detector performance. |
| M1-P0 / M1-100 | 25 historical local-model episodes plus a prospective 75-episode extension on 19 October 2026. | Real local Qwen agent outputs under the previously frozen synthetic-task conditions; raw records and audits have distinct provenance. | Pre-sprint agent behavior corpus. Do not call it Sprint data or say the 100 were generated under one identical protocol. |
| M2 | Previously authorized DeepSeek Flash monitor run and offline independent audit, completed before 23 October. | Actual monitor predictions on synthetic permission-filtered evidence plus deterministic audit labels; F2/F3 exposure and answer leakage are documented. | Pre-sprint monitor study, exploratory where specified. Structured 100% cell is answer-exposed, not independent reasoning. |
| M3 | Local Qwen3 within-checkpoint counterfactual-prompt run and independent audit dated 20 October 2026. | Actual message/action records for 12 groups; counterfactual ballot generations for eight eligible contexts; fixed-peer settlements are deterministic replays. | Pre-sprint mechanism probe. Three changed ballots are not Sprint evidence, general causal effects, or collusion labels. |
| Current submission-prep branch | Created after M3 and before 23 October; candidate dated 20 October 2026. | Scientific review, official requirement research, manuscript/PDF assembly, audit/check scripts, reproducibility docs, and an unrun proposed protocol. | Pre-sprint preparation. Do not claim this work as produced during the Sprint. |

All M0-M3 runs retain their original IDs, prompt/model hashes, logs and audit failures. The M3 source run is ignored and locally ACL restricted; this branch contains sanitized audit outputs and hash references, not raw private messages. No run timestamp or artifact is rewritten to appear newer.

## Work proposed for the Sprint

`docs/SPRINT_NEW_VALIDATION_PROTOCOL.md` and `configs/sprint-validation-groups.json` define a new, not-yet-executed validation using three new payoff families and 24 new scenario/seed group IDs. The full sample schedule was generated without model outputs. The manifest marks `model_calls_authorized=false`. No agent or monitor inference occurred while preparing this package.

During final review, the proposed scenario file's first metadata version mislabeled a per-recipient reward-rule score as a combined A+B score. The original v1 bytes and review record are preserved under `docs/results/submission-prep/failure-records/`; the v2 schema labels each agent's score separately from the combined A/B sum. No matrix, score rule, assigned sample, M0-M3 artifact or model response changed, and no inference occurred.

Any later run must have its own dated approval, source freeze, model/runtime identity, append-only calls/failures, pre-run data hashes and independent audit. It must be reported as Sprint-time work only if actually run during 23-25 October; otherwise the report must say when it was performed. No post-sprint run may be backdated or presented as a Sprint result.

## AI assistance and authorship

Codex assisted with source review, evidence cross-checking, drafting, code and PDF generation. This is an AI-assisted review candidate, not entrant-authored final prose. Actual author(s) must inspect the data and sources, revise the text in their own words, approve all claims and provide true names/affiliations/team details. The current page explicitly says the report must be the team's own writing and that generic AI-written submissions may not be scored.
