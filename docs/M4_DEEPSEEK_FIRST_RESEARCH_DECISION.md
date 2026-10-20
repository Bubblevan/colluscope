# DeepSeek-First M4 / Monitor — Integrated Decision

**Current state:** `GO_COMPATIBILITY_PILOT_AFTER_REFREEZE_PUSH_AND_OFFICIAL_PREFLIGHT`  
**Real model/API calls:** 0 at the time of the current freeze candidate.  
**Scope:** the user's later explicit one-run authorization in the attached DeepSeek-first execution task; no approval is inferred for anything beyond that exact bounded schedule.

## Decision rules

1. The compatibility pilot must pass on one selected interface. JSON fallback is permitted only on explicit raw evidence that Strict Function Calling is unsupported. A parse error, factual error, timeout, generic 400/500, identity mismatch, or invalid output never triggers fallback or a retry.
2. The first two preselected M4 groups must complete and pass independent replay of raw request/response hashes, context permissions, action records, message delivery, sealed ballots, settlement, welfare, incentives, and Public-only E before bulk M4 proceeds.
3. The Agent request count must remain ≤264 and the shared request/cost ledger ≤900 / USD 5.00. Any started ambiguous request remains unknown and is never resent.
4. Monitor may be frozen only after 24 Agent groups independently replay. Monitor scaling past the first six groups requires an assessable same-item/task/permission B4/B5 pair with both raw responses valid. No such pair means stop Monitor inference.
5. Failures and assigned denominators remain visible. A successful software/interface gate is not proof of collusion, intent, an Agent population effect, or a general-purpose detector.

## Current GO/NO-GO status

The first launcher invocation after commit `8c06ef5c5f73e0a221b4fe20305dbf68ab9f5e15` stopped with `UnboundLocalError` while creating the local pilot plan. The global request ledger was absent, so zero physical model/API requests were started. The traceback is retained at `docs/results/deepseek-first-m4/logs/orchestrator-preflight-unbound-write-once.log`. The shadowing import was removed and a mocked end-to-end pilot-startup regression test was added. The corrected candidate now passes **36 targeted tests and 548 full-suite tests (1 opt-in host check skipped)**; the regenerated plan matches byte-for-byte with SHA256 `21bddaccd2385bf730dd367085aaad804ce7fb43a0dc33080b41ce3219d7b935`. This is **GO for the authorized compatibility pilot only after** this corrected freeze is committed and pushed and official preflight is repeated. No model result has been observed; all behavioral claims remain NO-GO.

After the corrected freeze is pushed, repeat official identity/pricing/endpoint/credential-presence preflight before dispatch. After execution, replace this decision with exact gate outcomes, raw-audit SHA256s, assigned/completed/failed call counts, usage/cost, and reproduction commands. If any gate fails, record the precise stop and do not continue later phases. This decision does not authorize an additional run.
