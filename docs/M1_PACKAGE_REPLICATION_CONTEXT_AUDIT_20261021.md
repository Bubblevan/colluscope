# M1 Package Replication Context Audit — 2026-10-21

## Decision

Do not carry the three-matrix/eight-seeds-per-matrix draft (`v2`) forward unchanged. Before any new model response, its rendered-input profile audit found that 24 nominal matched groups contained only 36 unique initial message prompts and 18 unique C ballot prompts. A/B message prompts are identical when family, condition, chair, and agent match; seed and request ID are not in the prompt. C receives no private reward or private-channel indicator, so its prompt repeats across all four no-public-bonus conditions. Temperature is frozen at zero, so repeated prompt contexts are not defensible as independent behavioral contexts.

The v2 draft and its three matrices are retained unchanged as history. A v3 offline design replaces the repeated three-matrix schedule with 24 distinct output-independent matrices, one per matched group, balanced eight per target-regret stratum (6, 12, 18). The protocol remains 24 groups / 120 episodes / 456 local generations, but now exposes 96/96 unique initial message prompts and 48 unique C ballot prompts. C still has an exact same-input repeat across four no-public-bonus conditions in each group; that is a deliberate input-invariance negative control and must not be counted as 120 independent C contexts.

## Evidence and falsification

The profile auditor calls the existing frozen M1 renderer and hashes exact rendered text while excluding request IDs and seeds (neither is rendered). It does not save prompt content and does not predict any response.

| Candidate schedule | Groups / matrices | Initial message prompts, unique / assigned | C ballot prompts, unique / assigned | C same-input checks |
|---|---:|---:|---:|---:|
| v2: three matrices × eight seeds | 24 / 3 | 36 / 96 | 18 / 120 | 24 / 24 |
| v3: 24 matrices × one seed | 24 / 24 | 96 / 96 | 48 / 120 | 24 / 24 |

The schedule correction is output-independent and made before any new outcome. V3 is not claimed to create 24 statistically independent model responses: it creates 24 distinct payoff contexts for the matched package contrast. Every response-conditioned A/B ballot prompt still has to be hashed at call time. The exact C duplicates remain a within-group negative control. No request memoization or response reuse is allowed.

The 24 matrices were selected by a deterministic continuation of the existing SHA-256 candidate stream. The output artifact `research/drafts/m1-package-24-matrix-scenarios-20261021.json` has SHA-256 `79358acd02dcade31291e879d1d173e5e92e9bf5f57305c65a3d59f954ca502a`; it records every matrix, candidate index, canonical orbit, six permutation scores, unique optimum, target welfare, regret, +20 conflict, and seed/group/condition order. A separate verifier, `scripts/audit_m1_package_24_matrix_design.py`, independently regenerated the candidates and checked all 144 assignment scores, canonical-orbit exclusions, first-eight selection order, seed map, and condition schedule. Its result is saved at `docs/results/research-sprint-20261021/direction-review-followup/m1-24-matrix-independent-audit.json` (SHA-256 `e8e7def5f6621681a15bf648e8ef1fa228cb4cd872c7bcc4a23a17a7ecb8849f`). The frozen candidate file has no model-output dependency. The exact prompt-profile output has SHA-256 `f6d2c4d19f525c685dd25493cfe1319cbb72e491b3704ab490b27af28b1c7b2f`.

## Scope boundary

The proposed contrast remains the assigned private-target reward × chat-stage *package*. It cannot establish that an agent understood or followed message semantics, reached an agreement, colluded, or had a latent intent. The C repeated prompt can test visible-input invariance; it is not evidence about treatment awareness or hidden mechanism.

No model calls, external API calls, or Monitor evaluations were made. The design remains unregistered and unauthorized. The prior M4 approval is consumed and cannot be reused.

## Reproduction

```powershell
python scripts/freeze_m1_package_24_matrix_design.py --check
python scripts/audit_m1_package_24_matrix_design.py --check
python scripts/audit_m1_replication_prompt_profiles.py --check
python scripts/researchctl.py audit
```

The prompt-profile result is saved at `docs/results/research-sprint-20261021/direction-review-followup/m1-prompt-profile-audit.json`; the matrix schedule is saved at `research/drafts/m1-package-24-matrix-scenarios-20261021.json`.
