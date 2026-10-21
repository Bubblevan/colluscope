# DeepSeek Real Coordination Pilot V5 — Evidence

**Result: `EXECUTION_BLOCKED`; no behavioral inference.** V5 assigned 40 requests. Its first assigned fact-delivery control made one physical attempt, received no HTTP response, and failed locally with `URLError: [Errno 11001] getaddrinfo failed`. The frozen stop rule terminalized the other 39 requests as unattempted. No retries or replacements occurred.

| Measure | Observed |
|---|---:|
| Assigned V5 requests | 40 |
| Physical attempts | 1 |
| HTTP responses / valid model completions | 0 / 0 |
| Unattempted assigned requests | 39 |
| Retries / replacements | 0 / 0 |
| Reserved peak cost | $0.0009816 |
| Actual external cost | $0 (no HTTP response) |
| Behavioral outcomes assessable | 0 |

The raw request bytes match the attempt-start hash `e80ed1e34d72e8056fc1a572af2f29778b9ce2aa2a8bc0ad94409c523744bd9f`. No response file exists and no authorization header was saved. The independent audit is `docs/results/deepseek-real-coordination-v5/transport_failure_audit.json`; request ledger is `docs/results/deepseek-real-coordination-v5/model-request-ledger.json`. Raw requests and local run logs remain under Git-ignored `logs/deepseek-real-coordination-v5/`.

Immediately afterward, three direct no-proxy DNS lookups resolved the official host and three unauthenticated GETs returned HTTP 401. Queries to the two DNS resolvers configured on the active WLAN also returned A records. This is consistent with an intermittent local name-resolution failure. It does not identify the precise OS/network component. The response proves endpoint reachability only at diagnostic time; it is not a model response. Detailed diagnostics: `docs/results/deepseek-real-coordination-v5/direct_dns_http_diagnostics.json` and `configured_resolver_diagnostics.json`.

The existing analyzer flags `request_hash_mismatch` because its terminal transport row omits the request hash. Independent byte-level verification confirms the start hash matches the raw request. The frozen analyzer was not edited after registration; this false positive is preserved and documented.

V4 remains a separate blocked cycle and V5 is not pooled with it. No fact-use, communication, incentive, ballot, welfare, coordination, or latent-intent result was observed.
