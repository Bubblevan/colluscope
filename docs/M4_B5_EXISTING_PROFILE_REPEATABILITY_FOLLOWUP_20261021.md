# M4 B5 Existing-Profile Repeatability — Post-hoc Offline Reanalysis

**Date:** 2026-10-21  
**Evidence class:** `offline_reanalysis`  
**New model/API calls:** 0  
**Analysis status:** post-hoc exploratory; not a registered experiment  
**Scientific result:** `INCONCLUSIVE` on view attribution; existing exact-input response changes make the proposed 144-call repeatability screen lower priority.

## Question

Do the retained exact-input historical/current response comparisons already show enough within-profile variation to weaken an interpretation of the M4 B5 view contrasts as view-specific? Could that evidence reduce the value of the unregistered `m4-b5-view-repeatability-v2` 144-request proposal?

The falsifying counterexample to a stable-view reading is an identical Public-only request-body profile whose historical and current raw labels disagree. The analysis unit is a unique request-body hash, not a case label or assigned request row. The one Public-only body shared by two contexts is counted once.

## Inputs and method

The analysis joins three already frozen sources:

1. The v5 sanitized rows from the independent raw-response replay, which checked all 48 historical/current pairs against raw request/response bytes, reported fingerprints, strict parsing, and stored row associations.
2. The completed 232-request campaign's schedule, append-only attempt ledger, and result ledger. The 24 A1 contexts are joined by hashed unit IDs to exact request-body hashes; raw payloads are not read by this reanalysis.
3. The pre-existing exact-input audit outcome. Its public source hash pins every input; the script refuses changed files or incomplete denominators.

The script independently groups audited raw labels by exact request-body hash, verifies the current A1 labels against the raw-response audit's current labels, and links Public-only profiles to their privileged-original profile(s). It emits only hashes, denominators, counts, and canonical label-category summaries. It never reads or writes message bodies, request bodies, response bodies, or private text.

This is a post-hoc reaggregation of independently raw-audited sanitized rows; it is **not** a second raw-byte parser or a preregistered confirmation.

## Results

| Evidence | Public-only | Privileged-original |
|---|---:|---:|
| Historical/current exact-request pairs | 24 | 24 |
| Unique request-body profiles | 23 | 24 |
| Pairs with different raw labels | 17/24 | 2/24 |
| Profiles unanimous across all retained observations | 7/23 | 22/24 |
| Profiles non-unanimous across retained observations | 16/23 | 2/24 |

The one Public-only profile shared across two source contexts has four retained outputs (two contexts × historical/current); its labels split 2/2. The other 22 Public-only profiles have two observations each. Every privileged profile has two observations.

In the current A1 campaign, the Public-only versus Privileged-original labels differ in 19/24 assigned context pairs. After collapsing the shared public input, 18/23 unique public-profile clusters have at least one linked current view difference. When the historical and current observations are combined and a cluster is called determinate only if its public profile and every linked privileged profile are unanimous, only 7/23 clusters are determinate; 5 of those 7 have different public/privileged modes. Sixteen clusters contain at least one non-unanimous exact-body profile.

This does not satisfy the separate candidate's proposed `18/23` determinate-cluster criterion. That comparison is contextual only: the existing repeats are separated across campaigns and do not substitute for the proposed interleaved within-campaign repeats.

The scientific-critic checklist was applied as an adversarial self-review because this turn has no independent reviewer context. The sanitized critique is preserved at `docs/results/research-sprint-20261021/m4-b5-existing-profile-repeatability-self-critique.md`; it does not count as an independent review.

## Adversarial interpretation

The strongest observation is that same-body, same-reported-fingerprint Public-only outputs changed much more often than Privileged-original outputs in this retained cross-run comparison. This weakens a simple explanation that the current 19/24 context differences alone demonstrate an effect of viewing private evidence.

The following alternatives remain unresolved:

- The provider alias may have served different hidden model or system states despite matching reported fingerprints.
- The historical/current disagreement could reflect time, hidden provider state, decoding behavior, or another unobserved serving factor. It does not establish randomness or same-window instability.
- The view contrast remains bundled: permission, event presence, completeness, wording, salience, and token length differ. This reanalysis cannot isolate any one factor.
- `public_harm` is deterministically recoverable from public task and ballot records; this result does not show an LLM is needed for that label.
- The unit is a small finite set of repeated input profiles, not a population sample. No significance test or population statement is warranted.

Accordingly, the scientific outcome stays `INCONCLUSIVE`, not `REFUTED`. For resource allocation, a new 144-request B5 repeat campaign is **deprioritized** unless same-window response repeatability itself becomes the main claim. The more decision-relevant prospective direction is the already-reviewed M1 package interaction over 24 new payoff matrices, with its outcome limited to the finite assigned treatment package. The private-target/common-target and added-chat-stage confounds must remain explicit; the experiment cannot identify message semantics or latent intent.

## Reproduction

```powershell
python scripts/audit_m4_b5_existing_repeatability_by_profile.py
python scripts/researchctl.py audit
```

The report JSON and command log are `docs/results/research-sprint-20261021/m4-b5-existing-profile-repeatability-20261021.json` and `.log`. The first implementation run expected 232 request-ledger rows and failed because the append-only ledger correctly has 464 start/terminal events; the exact error and diagnosis are preserved in `docs/results/research-sprint-20261021/m4-b5-existing-profile-repeatability-20261021-failure-history.log`. The committed script now pins all five source hashes and checks all denominators and current-label joins.

## Authorization boundary and next action

The 232-request grant for `m4-b5-context-sensitivity-campaign-v1` is consumed and cannot cover a repeatability or M1 run. No new inference is authorized by this reanalysis. The M1 package candidate already fixes 24 matrices, 120 assigned episodes, 456 local Qwen generations, 480 total HTTP attempts including identity checks, zero external spend, zero retries, and zero replacements. On 2026-10-21, the local checkpoint SHA-256 and `llama-server.exe` SHA-256 were independently recomputed and matched the frozen config: `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` and `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`. Live process identity, endpoint ownership, and tokenizer/template parity remain unverified and must be checked by the gated runner after approval. The exact pending scope is in `docs/M1_PACKAGE_REPLICATION_AUTHORIZATION_REQUEST_20261021.md`; registration and final runtime identity checks must follow before dispatch.
