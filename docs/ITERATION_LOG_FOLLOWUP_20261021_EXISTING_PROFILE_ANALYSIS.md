# Iteration Log — Existing Exact-Profile Reanalysis (2026-10-21)

## INSPECT

The previous offline source reconstruction verified 144 prepared request bodies for the unregistered M4 repeatability candidate. The parent 232-request M4 campaign is closed. Existing v5 response-repeatability artifacts already contain 48 exact historical/current request pairs, each with matching reported fingerprints and raw-byte replay checks.

## HYPOTHESIZE

H1: the current M4 view contrast is stable across repeated identical inputs.  
H2: exact-input response instability is common enough to rival or exceed view-profile contrast; mutable provider state remains a plausible explanation.  
H3: cross-run differences are time/provider-state specific and same-window repeated inputs could still be stable.

## SPECIFY

Use every 48 raw-audited historical/current pair. Collapse exact duplicate inputs by request-body SHA-256; retain the two-context shared Public-only profile once for profile-level counts and preserve 24 context rows for descriptives. Compare profile unanimity across both observations, then join the current A1 public/original labels by frozen hashed unit and body IDs. Do not interpret the post-hoc result as a same-window or causal test.

## IMPLEMENT / RUN

Added `scripts/audit_m4_b5_existing_repeatability_by_profile.py`. It pins the sanitized audit rows plus current campaign schedule/attempt/result hashes, checks 48 valid pairs and the full 232-row campaign denominator, and joins all 24 A1 context pairs without emitting evidence text. Initial run failed because the append-only request ledger has both `attempt_started` and `attempt_terminal` rows (464 total); that failure was corrected by validating the appropriate start-row count while keeping all terminal rows present. The final command completed and preserved JSON/stdout artifacts. No model/API request was sent.

## OBSERVED FACTS

- Unique exact Public-only profiles: 23; 17/24 assigned historical/current pairs disagree; 16/23 profiles are non-unanimous; 7/23 are unanimous.
- Unique exact Privileged-original profiles: 24; 2/24 pairs disagree; 2/24 profiles are non-unanimous; 22/24 are unanimous.
- Current Public-only/Privileged-original differences: 19/24 context pairs, or 18/23 unique public-profile clusters with at least one linked change.
- Across retained historical/current observations, only 7/23 linked clusters have unanimous labels for the public profile and all privileged profile(s); 5/7 determinate clusters differ by view, and 16/23 clusters contain a non-unanimous profile.

## ADVERSARIAL REVIEW

This is a post-hoc reaggregation of sanitized rows already independently checked against raw bytes, not a second raw-response replay. Historical and current requests came from different campaign periods. Equal request bytes and a reported fingerprint do not establish identical provider state. The response label is a mechanically computable public-harm category, not collusion or intent. `18/23` is not met here, but the registered 144-request candidate was never run; its within-campaign estimand is not falsified by this cross-run reanalysis.

## DECIDE

Scientific result: `INCONCLUSIVE` for whether the view contrast is stable or caused by evidence view. Research-priority decision: deprioritize the 144-request B5 repeatability candidate because existing exact-input comparisons already show substantial Public-only label instability and the target is rule-computable. Shift the next prospective question to the finite M1 private-reward × chat-stage package interaction, explicitly not to message semantics or collusion. The M1 runtime and 24-matrix schedule are ready for offline review, but the experiment is not registered or authorized.

## REPORT / ONE NEXT ACTION

Request a fresh, exact-scope authorization for `m1-reward-chat-24group-replication-v1`: up to 456 local Qwen generations, 480 physical HTTP attempts including identity checks, zero external cost, no retries/replacements, loopback-only endpoint, and a fixed expiry. Do not run until authorization, registration, and live identity gates all pass.
