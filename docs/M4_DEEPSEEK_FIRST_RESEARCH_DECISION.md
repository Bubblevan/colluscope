# DeepSeek-First M4 / Monitor — Integrated Decision

**Current state:** `GO_COMPATIBILITY_PILOT_AFTER_FREEZE_PUSH_AND_OFFICIAL_PREFLIGHT`  
**Real model/API calls:** 0 at the time of the current freeze candidate.  
**Scope:** the user's later explicit one-run authorization in the attached DeepSeek-first execution task; no approval is inferred for anything beyond that exact bounded schedule.

## Decision rules

1. The compatibility pilot must pass on one selected interface. JSON fallback is permitted only on explicit raw evidence that Strict Function Calling is unsupported. A parse error, factual error, timeout, generic 400/500, identity mismatch, or invalid output never triggers fallback or a retry.
2. The first two preselected M4 groups must complete and pass independent replay of raw request/response hashes, context permissions, action records, message delivery, sealed ballots, settlement, welfare, incentives, and Public-only E before bulk M4 proceeds.
3. The Agent request count must remain ≤264 and the shared request/cost ledger ≤900 / USD 5.00. Any started ambiguous request remains unknown and is never resent.
4. Monitor may be frozen only after 24 Agent groups independently replay. Monitor scaling past the first six groups requires an assessable same-item/task/permission B4/B5 pair with both raw responses valid. No such pair means stop Monitor inference.
5. Failures and assigned denominators remain visible. A successful software/interface gate is not proof of collusion, intent, an Agent population effect, or a general-purpose detector.

## Current GO/NO-GO status

The offline implementation has passed its final full repository suite (**547 passed, 1 opt-in host-dependent check skipped in 137.34s**) and the targeted frozen-plan suite (**35 passed**). The committed 30-slot plan must still reproduce byte-for-byte after staging. This is **GO for the authorized compatibility pilot only after** the source freeze is committed and pushed and the official pricing, identity, endpoint and credential-presence preflight passes. These are software and interface gates, not behavioral evidence. No model result has been observed, so the current scientific evidence state remains **NO-GO for any behavioral claim**. Any failed pilot or later stage gate stops the single run at that boundary.

After execution, replace this status only with the exact gate outcomes, raw-audit SHA256s, assigned/completed/failed call counts, usage/cost, and reproduction commands. If any gate fails, record the precise stop and do not continue later phases. This decision does not authorize a second run.
