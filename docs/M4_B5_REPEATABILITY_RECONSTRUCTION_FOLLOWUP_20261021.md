# M4 B5 Repeatability Candidate — Independent Source Reconstruction

**Date:** 2026-10-21
**Evidence class:** offline reanalysis
**New model/API calls:** 0
**Scientific outcome:** the request-profile collision is independently reproduced; the scientific reason for future monitor calls remains limited and requires new scoped authorization.

## Question and counterexample

The prior profile audit counted exact request-body hashes from the prepared manifest. The main risk was that the shared Public-only body came from an error in that manifest or request compiler rather than from the source evidence projection. The falsifier was a source-to-request reconstruction that produced either different Public-only request bodies for the two contexts, or failed to match the prepared request bytes.

## Independent reconstruction

`scripts/audit_m4_b5_repeatability_profiles_from_source.py` independently rebuilds the B5 evidence projection and canonical Chat Completions body. It does **not** call `compile_evidence_projection`, `deepseek_monitor_v1._request_row`, or the M4 request compiler. It reuses `prepare_full_research_monitor._m4_sources` only to map the frozen local M4 T/B/E records into the monitor-source shape. It checks frozen source, system-prompt, schedule, and request-manifest hashes, then reconstructs every scheduled view/repeat and compares the resulting SHA-256 to both the sanitized manifest row and the Git-ignored request bytes.

The script emits only hashes, counts, and validation status. It processes privileged historical messages in memory to reconstruct the real request body, but never writes or prints their text.

## Results

| Check | Result |
|---|---:|
| Source contexts | 24 |
| Reconstructed assignments | 144/144 |
| Reconstructed body hashes matched prepared bodies | 144/144 |
| Distinct public-only bodies | 23 |
| Distinct privileged-original bodies | 24 |
| Public body shared across source contexts | 1 |
| Privileged body shared across source contexts | 0 |
| Body shared across the two views | 0 |
| Assignments per body profile | 46 profiles × 3; 1 profile × 6 |

The two linked public-only source-unit hashes produce the same independently rebuilt evidence projection and complete request bytes. Each source unit still has its own, different privileged-original request. This confirms that a Public-only monitor receives identical bytes for these two records and cannot distinguish their private histories from request content. The candidate's primary denominator of 23 unique Public-only profile clusters is therefore appropriate; the 24 context transitions remain descriptive and share one baseline.

This is a finite input-identifiability fact. It does not predict whether a provider will return the same answer for byte-identical requests, establish why previous outputs changed, or support a collusion/intent label.

## Research direction and paper value

Three directions were compared against existing evidence and the separate-context Scientific Critic review already archived at `docs/results/research-sprint-20261021/scientific-direction-review-followup-20261021/independent-scientific-critic-review.md`:

- **A — B5 view sensitivity and all-present failure.** The historical 20/24 B5 Public-only/Privileged prediction changes with unchanged references are real finite observations. The 120-request balanced control's 40/40 `present` outputs, 20/40 exactness, and the 40/40 deterministic rule baseline establish a failure mode, not an LLM advantage. More context-access or Extract-and-Evaluate claims overlap Arike et al. A narrow repeatability screen could establish whether same-view response variation is large relative to view-profile differences, but it cannot isolate message semantics and is not by itself a strong paper contribution.
- **B — shared private target reward × communication-stage Agent behavior.** The prospective M1-100 9/15 versus 0/15 target-execution pattern is post-hoc and bundled with shared-target knowledge and an extra message stage. A matched replication on new matrices could add actual behavior evidence, but communication effects are already studied in auction and long-horizon settings; the increment must be a narrowly stated package interaction, not a semantic communication or collusion claim. Its execution requires a separate local-model scope and a more demanding protocol.
- **C — evidence sufficiency and identifiability.** The 12 scripted matched-world pairs support a finite example: 8/12 pairs differed on some determinate sequence element and 2/12 on the complete sequence. The deterministic construction is useful as a Track 2.3 claim-boundary control, but is weak as a standalone discovery and does not justify more model calls.

The independent reviewer ranked C first for low cost, then B, then A, while warning that C is not paper-worthy by itself. I retain A's 144-attempt exact-repeat candidate only as the smallest diagnostic that directly tests whether the real M4 view contrast exceeds within-profile variation. Its success would justify a cautious reliability claim for this fixed task; it would **not** solve the all-present mechanism, demonstrate LLM value over the rule baseline, or establish a novel general monitor effect. B remains the more promising empirical paper direction, but is not ready for execution under current authorization.

## Authorization reconciliation and decision

The user reply “批准此范围” names `m4-b5-context-sensitivity-campaign-v1`, a 232-request / USD 0.90 scope. The registry records that experiment as completed and its 232-request grant as fully consumed. The reply cannot be transferred to `m4-b5-view-repeatability-v2` (144 attempts, USD 0.35) or to the prospective M1 behavior replication. No new model request was sent.

The repeatability candidate remains unregistered and undispatched. It also transmits 144 appearances of historical private-message events to the official provider. A fresh scope must name this candidate and its private-evidence transfer explicitly. At review time 2026-10-21 01:48 UTC, the [official pricing page](https://api-docs.deepseek.com/quick_start/pricing/) lists 01:00–04:00 UTC on weekdays as peak; no dispatch may occur in that interval. Any later dispatch also needs a current price/model-alias check and all existing fail-closed runtime gates.

**Decision:** `PASS` for independent source-to-body verification; scientific claim remains `INCONCLUSIVE`; no GO for new inference under the current consumed authorization. Preserve the 144-attempt candidate for review, but do not escalate to the 728-call factorial or claim it will explain every B5 failure.

## Reproduction and preserved failure

```powershell
python scripts/audit_m4_b5_repeatability_profiles_from_source.py
python scripts/audit_m4_b5_view_repeatability_preparation.py
python scripts/researchctl.py audit
```

The first run of the new script failed before reading source data because the repository root was absent from `sys.path`; that sanitized failure is preserved in `docs/results/research-sprint-20261021/m4-b5-profile-collision-audit-20261021/source-reconstruction-initial-import-failure.log`. After the minimal import-path correction, all 144 reconstructions passed. The source output is `docs/results/research-sprint-20261021/m4-b5-profile-collision-audit-20261021/source-reconstruction-audit.json`; the command stdout is preserved alongside it. The source/output files contain no private message text or credentials.
