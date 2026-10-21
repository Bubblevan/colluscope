# Direct DeepSeek connectivity check — 2026-10-21

At the user's request, tested the frozen endpoint over HTTPS with an unauthenticated GET, using `urllib.request.ProxyHandler({})`. No proxy environment variables were present; no authorization header or model prompt was sent. The official endpoint returned HTTP 401, which establishes direct network reachability but does not establish model identity, generation success, or experiment behavior. The earlier `getaddrinfo failed` occurred before HTTP and is consistent with a transient local resolver failure. The V4 model client already explicitly disables proxy discovery in `src/colluscope/deepseek_m4_v1.py`.

This diagnostic does not reopen V4. Its preregistered first attempt remains terminal, with zero retries and no response. Any new generation must be prospectively registered as a separate run.

## Integrity guard encountered during reporting

An initial attempt to append this note to the hash-frozen V4 evidence report caused `python scripts/researchctl.py audit` to fail with `deepseek-real-coordination-40-v4: outputs[2] hash mismatch: docs/DEEPSEEK_REAL_COORDINATION_V4_EVIDENCE.md`. The report was restored from HEAD immediately; the diagnostic is kept separately here. The failed integrity check is preserved in `deepseek_frozen_report_integrity_guard_20261021.json`.
