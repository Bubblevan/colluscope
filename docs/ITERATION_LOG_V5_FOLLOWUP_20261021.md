# V5 iteration follow-up — 2026-10-21

- V4 remains closed after one pre-HTTP DNS resolver error; no behavior was observed.
- Verified the V4 runtime already uses `urllib.request.ProxyHandler({})`. A direct unauthenticated GET to the official endpoint returned HTTP 401, confirming transport reachability only.
- Registered V5 under a fresh experiment/request namespace; no V4 result is reused. Its frozen schedule assigns four capability controls then 36 game requests, with a maximum of 40 physical attempts, zero retries/replacements, a USD 0.50 peak-cost cap, and a hard stop on any failed control or integrity/transport gate.
- Offline checks: 33 tests passed, freeze check passed, runner check-only passed with zero model calls.
- First registry audit after appending to hash-pinned `docs/ITERATION_LOG.md` and `docs/RESEARCH_RISK_REGISTER.md` failed on their M4 campaign output hashes. Both files were restored; the full failure is preserved in `docs/results/deepseek-real-coordination-v5/offline_preflight_first_failure.log`.
- Next: rerun the clean registry audit, then push the full V5 freeze before executing.


## V5 run closeout — 2026-10-21

- **RUN:** The pushed V5 runner made one physical attempt for `v5-C1-delivered`, then stopped on `URLError: [Errno 11001] getaddrinfo failed`; zero HTTP responses, zero model completions, 39 unattempted rows. Three no-proxy DNS+GET probes immediately afterward passed DNS and returned HTTP 401; both configured WLAN resolver queries returned A records. No authorization header was saved.
- **ADVERSARIAL REVIEW:** Raw request bytes SHA matches attempt-start SHA. V5 analyzer's `request_hash_mismatch` is the same known false positive caused by missing hash on transport terminal records; frozen analyzer untouched. No behavior is inferable.
- **DECIDE:** Closed V5 as `BLOCKED / EXECUTION_BLOCKED`; V4 and V5 are separate, no retry or pooling. Registry audit PASS. Actual total use 1,159/1,200 requests; V5 cost $0.
- **Next:** Add an offline-tested direct, single-resolution IP transport that retains official hostname SNI and certificate verification, then decide whether a fresh V6 run is worth the remaining 41 attempts.
