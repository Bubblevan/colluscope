# V5 iteration follow-up — 2026-10-21

- V4 remains closed after one pre-HTTP DNS resolver error; no behavior was observed.
- Verified the V4 runtime already uses `urllib.request.ProxyHandler({})`. A direct unauthenticated GET to the official endpoint returned HTTP 401, confirming transport reachability only.
- Registered V5 under a fresh experiment/request namespace; no V4 result is reused. Its frozen schedule assigns four capability controls then 36 game requests, with a maximum of 40 physical attempts, zero retries/replacements, a USD 0.50 peak-cost cap, and a hard stop on any failed control or integrity/transport gate.
- Offline checks: 33 tests passed, freeze check passed, runner check-only passed with zero model calls.
- First registry audit after appending to hash-pinned `docs/ITERATION_LOG.md` and `docs/RESEARCH_RISK_REGISTER.md` failed on their M4 campaign output hashes. Both files were restored; the full failure is preserved in `docs/results/deepseek-real-coordination-v5/offline_preflight_first_failure.log`.
- Next: rerun the clean registry audit, then push the full V5 freeze before executing.
