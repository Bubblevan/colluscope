# Iteration Log — Independent M4 Profile Reconstruction

**Date:** 2026-10-21
**Round:** validate the prepared 144-call repeatability candidate against source records
**Evidence class:** offline reanalysis
**New model/API calls:** 0

## INSPECT

The profile-aware manifest audit found 47 exact body profiles across 48 context/view cells. Its most consequential finding was one Public-only body shared by two contexts, assigned six repeated requests. The validity risk was that this duplication might be an artifact of the prepared manifest or the production request builder.

## SPECIFY

Falsify the profile-collision claim if an independent projection/request implementation produces different bytes for either context, or if it does not match the local prepared request bytes. Preserve the source M4 T/B/E rows, schedule, and request assignments; reveal only hashes/counts.

## IMPLEMENT / RUN

Added `scripts/audit_m4_b5_repeatability_profiles_from_source.py`. It independently implements the M4 B5 evidence allowlist and request envelope without calling the production projector or request compiler. It reuses only the existing M4 source loader for T/B/E source mapping. It reconstructed all 144 assigned bodies and matched all prepared hashes and local request files. It found 23 Public-only and 24 Privileged-original profiles, exactly one cross-context Public-only collision, no body shared across views, and the expected 46×3 plus 1×6 assignment distribution.

The first run failed on an import-path omission before source data were read. The minimal `sys.path` fix and complete sanitized traceback are preserved in `docs/results/research-sprint-20261021/m4-b5-profile-collision-audit-20261021/source-reconstruction-initial-import-failure.log`. The successful JSON and stdout are preserved in the same directory. No raw message text or credentials were printed.

## ADVERSARIAL REVIEW

The independent rebuild confirms the duplicate public input is not a manifest-only artifact. It does not make the two contexts independent observations and does not establish response stability. The three repeated calls per body in the draft can estimate only finite variation for the mutable DeepSeek alias and exact request bytes. The main views still bundle private text, event structure, completeness metadata, and token length. The deterministic public-harm baseline remains exact; therefore even a stable view contrast would not establish a need for an LLM to calculate welfare.

The A/B/C direction comparison remains: A is a narrow reliability diagnostic on a real anomaly; B has greater behavior-research potential but is confounded and requires new local Agent authorization; C is a useful finite Track 2.3 evidence-boundary control but too constructed to be the main result. The archived separate-context reviewer ranked C>B>A for cost while warning that C is weak as a standalone paper result.

## DECIDE

Operational decision: `PASS` for independent source-to-request verification. Scientific decision: `INCONCLUSIVE`. The 23-cluster analysis unit is justified. Retain the 144-call exact-repeat screen only as the next bounded diagnostic candidate; do not claim it will isolate message meaning or explain the all-present control. No inference is authorized by the user's reply naming the already completed 232-call `m4-b5-context-sensitivity-campaign-v1`; that grant is consumed and cannot be transferred.

## REPORT

One next action: obtain a fresh scope for `m4-b5-view-repeatability-v2` (maximum 144 physical requests, USD 0.35, official DeepSeek Flash, off-peak only, zero retries/replacements, expiry 2026-10-25T23:59Z, with explicit approval to send 144 private-message event appearances), or stop this monitor line and move to the separately scoped M1 behavior replication. No request was sent in this round.
