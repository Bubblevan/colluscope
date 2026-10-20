# Submission Readiness Decision

**Decision date:** 2026-10-20<br>
**Source baseline:** M3 audited commit `acf80705b8f3af6521613aef80b0c736cabb5f45`<br>
**Branch:** `codex/submission-readiness-prep`

## Decision

- **GO:** retain this package as a reviewable, evidence-linked pre-sprint paper candidate and as a frozen proposal for a small new validation. The five-page PDF passes structural checks and visual review; the headline metrics were independently recomputed from sanitized audit tables without model calls.
- **NO-GO:** submit the current PDF or represent it as an official-template-compliant or entrant-authored final paper. The exact template could not be inspected, the official page simultaneously says the submission window is closed and gives a future 25 October deadline, author/team and signup facts are missing, and all current results predate the Sprint. The manuscript is AI-assisted and needs entrant verification and rewriting.
- **NO-GO:** run the proposed validation or any Agent/Monitor inference under this task. Its sample schedule and protocol are frozen offline only; `model_calls_authorized=false`.
- **NO-GO:** infer latent collusion, agreement, communication-induced coordination, or population causal effects from M0-M3. Observable sequences and counterfactual prompt responses support only the operational descriptions stated in the paper.

## Evidence supporting the candidate

1. `scripts/audit_submission_claims.py` returns `PASS` with `model_calls=0`; its input hashes and all recomputed headline counts are recorded in `docs/results/submission-prep/claim-audit.json`.
2. The current PDF is 5 US Letter pages, 138 abstract words, 419,761 bytes, four evidence figures, and five clickable reference links. `scripts/validate_submission_pdf.py` returns `PASS_STRUCTURAL_CHECKS`; two builds were byte-identical and all five final page renders matched the individually inspected pages pixel-for-pixel.
3. Scenario and group freeze checks reproduce the three proposed new payoff families and 24-group schedule. These are design artifacts, not results.
4. The paper distinguishes observed M1 behavior, M2 model predictions, M3 counterfactual responses, deterministic settlements, and unknown latent intent. Its 0/5 vs 3/3 self-history split is explicitly post-hoc exploratory; Masked structural cues and the 45.125-token No-delivery gap are disclosed.
5. M0-M3 raw runs, hashes, timestamps, and historical failure records were not edited. M3 private prompts/messages remain excluded from the public package and ACL restricted locally.
6. `scripts/verify_submission_manifest.py` checked all recorded file hashes and sizes, confirmed the PDF hash matches its structural-validation record, and found no private M3 raw paths or model calls.

## Unresolved submission blockers

- Ask Apart to resolve the official page's conflicting submission-window status and stated deadline. The page was checked on 20 October 2026; neither statement is assumed to override the other.
- Obtain and inspect the current official template, then regenerate and visually verify the report inside it if required.
- Confirm actual eligibility/signup status, team name/location fields, and truthful author/affiliation details.
- Entrant(s) must independently verify and rewrite the AI-assisted draft in their own words, approve every claim and citation, and identify any new Sprint-time result separately.
- The proposed new validation remains unrun. The Sprint schedule does not authorize inference by itself.

## Reproduction

From the repository root in PowerShell, using the recorded Python environment:

```powershell
python scripts/freeze_submission_validation_scenarios.py --check
python scripts/freeze_submission_validation_groups.py --check
python scripts/audit_submission_claims.py
python scripts/render_m3_svg_for_submission.py
python scripts/build_submission_pdf.py
python scripts/validate_submission_pdf.py
```

These commands make no model calls. Re-render the PDF pages separately for visual review. Historical M1/M3 raw audit commands and their privacy boundary are in `docs/SUBMISSION_REPRODUCTION_INDEX.md`.

## Merge and publication boundary

This decision authorizes neither submission nor merge to `main`. After the user reviews this package and the branch is independently checked, the suitable integration is an ordinary fast-forward merge only if the remote graph remains a descendant of the reviewed M3 baseline; do not force-push or rewrite M3 history.
