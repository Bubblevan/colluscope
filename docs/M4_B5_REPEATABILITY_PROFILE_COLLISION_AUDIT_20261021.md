# M4 B5 Repeatability Profile-Collision Audit

- **Date:** 2026-10-21
- **Evidence class:** `offline_reanalysis`
- **Model/API calls:** 0
- **Source candidate:** `m4-b5-view-repeatability-v2`, not registered or authorized

## Finding

The earlier preparation audit verified 48 *context × view* cells and three identical request bodies in each cell, but did not count distinct model-visible bodies across cells. The profile-aware re-audit of all 144 prepared request bytes found:

| View | Source contexts | Distinct request-body hashes | Calls | Cross-context body collisions |
|---|---:|---:|---:|---:|
| Public-only | 24 | 23 | 72 | 1 body shared by 2 contexts |
| Privileged-original | 24 | 24 | 72 | 0 |
| Total unique body profiles | — | 47 | 144 | — |

The shared public body receives six assignments (three under each of two source-context IDs). The other 46 unique body profiles receive three assignments each. No exact body is shared across the two views. Thus the 144 assignments are still complete and correctly paired to all 24 frozen contexts, but they are **not 48 independent input profiles**. The duplicate is a property of the frozen public projection, not a model or transport failure.

Two different source-unit hashes map to the same Public-only body hash, while each maps to a distinct Privileged-original body. Consequently, a Public-only monitor receives identical bytes for those two contexts and has no input-level basis for distinguishing their private histories. This is a finite projection/identifiability observation; it says nothing about latent intent. A hosted model may still emit different outputs for identical requests, which the historical raw-response evidence already shows can occur across observations.

## Reconciliation and preserved failure

An exploratory cross-artifact join initially mapped each request-body hash to a single source unit and overwrote one of the two units sharing the public hash. It reported 47 linked rows and falsely suggested an incomplete 24-context join. The failure is retained at `docs/results/research-sprint-20261021/m4-b5-profile-collision-audit-20261021/initial-body-hash-join-failure.log`.

The corrected profile-aware auditor uses one-to-many body-hash mappings. Its output is `docs/results/research-sprint-20261021/m4-b5-autoresearch-continuation-20261021/repeatability-preparation-audit-v4.json`. It verified all 144 body hashes against the ignored local manifest, source hashes, 48 context/view assignments, 47 unique request-body profiles, 23/24 unique profiles by view, the 6-call duplicate profile, and Git-ignored raw storage. It did not print private payloads. The auditor reuses the frozen source runtime only to resolve source paths; it does not independently compile the prompt bodies.

The revised candidate protocol passes its frozen-input and structural checks. Registration remains blocked by the expected missing experiment-specific `approval_id`; no approval was fabricated. The first schema-validation failure (missing `protocol.frozen_inputs`) and corrected result are retained under `docs/results/research-sprint-20261021/m4-b5-profile-collision-audit-20261021/`.

## Required preregistration correction

Before any registration or new inference, the analysis must use unique request-body profiles as the repeatability unit and keep context pairings as a secondary descriptive view:

1. Preserve all 144 assigned attempts and all 24 source contexts.
2. Analyze 47 exact input profiles: 23 Public-only and 24 Privileged-original. One Public-only profile has six responses; the remaining profiles have three. Report both assignment-level and unique-profile denominators.
3. Define a public-profile cluster as one unique Public-only body and its linked Privileged-original profile(s). There are 23 clusters; one cluster links one public body to two distinct privileged bodies.
4. A cluster has a determinate paired mode only if the public profile and every linked privileged profile have unique modes. A cluster is changed if at least one linked privileged mode differs from the public mode. It is unstable if any profile within it has non-unanimous repeated labels.
5. Report the 24 context-pair transitions, but count the shared public baseline only once in the primary 23-cluster gates. Do not use context-level rows as independent evidence or compute population statistics.
6. Keep the previous protocol and v3 audit unchanged. The unregistered draft must be superseded by a versioned preregistration revision with these rules before approval/registration.

Using the same descriptive cutoffs as the earlier candidate, the revised gates are:

- **Stable package contrast:** at least 18/23 clusters have determinate paired modes, at least 6/23 clusters change, and changed clusters exceed unstable clusters.
- **Historical contrast not reproduced:** at least 18/23 clusters have determinate paired modes, at most 1/23 changes, and at most 6/23 clusters are unstable.
- **Otherwise:** `INCONCLUSIVE`. Identity drift, request-byte mismatch, or privacy failure invalidates the intended comparison; retain every assigned slot and stop.

These thresholds are finite descriptive decision rules, not significance tests. They do not isolate message meaning from permissions, event structure, completeness cues, wording, salience, or length.

## Reproduction

```powershell
python scripts/audit_m4_b5_view_repeatability_preparation.py
python scripts/researchctl.py audit
```

The profile-aware audit is read-only and made zero model/API calls. The schedule and request-manifest hashes remain unchanged: `08e9b6d72862629f1e3e2fa3f02f3dcaee41a6356ad874cdd7cecc6d9ac93f3e` and `6d26f48244bd06d93b29d58d02d69f03fe49d6db967b74cae0618ccfdfaf760a`.
