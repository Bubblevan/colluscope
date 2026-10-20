# Iteration Log Addendum — Scientific Direction Review

**Date:** 2026-10-21 local / 2026-10-20 UTC\
**Base:** `codex/deepseek-first-m4-research-20261020` @ `b63ab29249b56909e27e279a7269199b2e24b019`\
**Scope:** no-call research direction correction after the 232-request M4 B5 campaign closed. The prior approval is consumed; no new Agent or Monitor inference was attempted.

The historical `docs/ITERATION_LOG.md`, `docs/ITERATION_LOG_APPENDIX_20261021.md`, and prior risk addenda contain hashes referenced by closed cycles. They were left unchanged; this file is the new dated addendum.

## INSPECT

Highest research-validity risk: spending more calls on a public-harm label that is exactly computable from structured public records, while mistaking one-sided B5 predictions or finite label changes for evidence of monitor capability or collusion.

## SPECIFY

Counterexamples checked:

- The public-harm claim fails if any complete case lacks a unique public optimum or an independent ballot settlement disagrees with the recorded outcome.
- The synthetic rule baseline fails if a public-canonical label differs from an independently recomputed welfare regret.
- The A2 paired summary fails if there are not exactly 40 matched group × trajectory units with every assigned arm, or if the 20/20 label balance changes.
- A natural-language LLM-monitor claim is unsupported unless human coders can independently agree on proposal and action-concordance references, and the model is evaluated against a literal baseline and frozen capability controls.

## IMPLEMENT

- Added `scripts/summarize_scientific_direction_review.py`, which reads only sanitized score CSV/JSON summaries, records all source hashes in its manifest, checks complete A2 denominators, and emits no private text or raw payload.
- Re-ran the M4 public-harm independent audit and the 120-row synthetic deterministic rule baseline to new distinct output files under `docs/results/research-sprint-20261021/scientific-direction-review/`.
- Independently paired the A2 rows by `group_sha256_prefix × trajectory_sha256_prefix`; the correct 40-unit summary is recorded in `direction-review-current/evidence-synthesis.json`.
- Added a deterministic generator and checked-in draft matrix set for a prospective replication. It continues the frozen M1-100 SHA-256 candidate stream, rejects all F0–F3 permutation orbits, and reads no model outputs.
- Added a direction review, a non-blind separate-context critic report, a two-cycle execution-scope draft, and this risk addendum.
- Preserved all prior M0–M4 raw, prompt, schedule, and registered artifacts. Raw private messages remain local and are not included in Git artifacts.

## RUN

The no-call synthesis reports:

- 24/24 real M4 public-harm references independently reproduced; unique optimum in 24/24.
- B5 changes 20/24 Public→Privileged labels while references change 0/24; transitions are 15 `insufficient_evidence→absent`, 4 `present→absent`, and 1 `insufficient_evidence→present`.
- Earlier 120-call synthetic positive control: all 40 public-canonical model outputs were `present`, balanced reference labels, 20/40 exact; separate deterministic rule 40/40.
- Production A2 B5: 20/40 exact; arithmetic presentation: 39/40; bundled reversed prompt+enum order: 36/40 predictions change and 10/40 exact; V2-direct vs production B5: 5/40 predictions change with exactness unchanged at 20/40.
- Scripted visibility audit: 8/12 pairs differ on at least one determinate sequence item; complete-sequence difference in 2/12 pairs.
- Candidate matrices: three unique orbits, regrets 6/12/18, all six permutations checked; `--check` passes.
- The privacy scanner checked 48 local Agent messages against 915 public/non-ignored files; zero exact matches and no message text emitted.
- Model inference/API requests: 0. One read-only official DeepSeek pricing-page lookup was made; no research payload was sent.

## Failed attempts retained

An ad hoc aggregate first grouped only by the two trajectory hashes and collapsed 40 units into 2; it was discarded. Three subsequent quick summaries failed on undefined variable names or a Boolean passed to `sum`. The first candidate-generator run stopped on an incorrectly guessed source hash before writing; a later run wrote the JSON and then failed only while printing a relative path. These were corrected and all failure descriptions are in `direction-review-current/failure-history.log`. No source data or assigned row was removed or replaced.

## ADVERSARIAL REVIEW

- The arithmetic arm changes both content and length; its 39/40 score is not proof the model independently reasons over arithmetic.
- The reversed-order arm reverses both prompt and tool enum, so the 36/40 changes cannot be attributed to one ordering factor.
- The synthetic/production request comparison changes multiple fields and matrix distribution; the 5/40 changes do not prove or exclude a compiler explanation.
- Same request bytes and reported fingerprints still produced 19/48 raw-label differences in the historical/current comparison; hidden serving state is not identified.
- The B5 all-present label is a poor test of the model when a deterministic program gives 40/40; the nontrivial model task would be natural-language proposal/action extraction, which still needs human-gold labels.
- The separate-context reviewer recommended C for immediate efficiency and warned that the scripted result is not paper-worthy by itself. It had read the selected-hypothesis registry, so this is not blind confirmation.
- M1's 9/15 pattern remains a post-hoc package result, not a semantic communication effect. Shared target knowledge, message-stage salience, family dependence, and fixed temperature-zero behavior remain rivals.

## DECIDE

Keep B (private reward × chat-stage package) as the next prospective empirical question, because it is based on observed real-Agent actions and offers more paper-level potential than another deterministic public-harm Monitor call. Use C as the Track 2.3 evidence standard and a narrowly human-referenced proposal/action Monitor audit as the Track 2.2 contribution. Close A for this exact public-harm target; its 232-request campaign is inconclusive, and its task label needs no LLM when structured inputs are present.

No new experiment is registered or authorized. One unified proposed approval covers 456 local Qwen Agent requests plus 216 official DeepSeek Monitor requests, 672 total physical attempts, zero retries/replacements, $0.45 DeepSeek hard cap, off-peak only, through a proposed 2026-10-26 12:00 UTC expiry. Its two exact experiment IDs and full gates are in `research/drafts/m1-package-monitor-campaign-v1.md`. The 232-call grant cannot be reused.

## REPORT / next action

Review the two-cycle preregistration and human codebook against the frozen candidate matrices, then request one approval for both named cycles and the combined budget. Continue offline work and do not send inference requests until that approval exists. The autoresearch Goal remains active.
