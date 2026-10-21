# DeepSeek Real Coordination Pilot V5 — Decision

**Operational decision: BLOCKED. Scientific outcome: EXECUTION_BLOCKED.**

The frozen 40-request V5 run attempted only `v5-C1-delivered`. DNS resolution failed before HTTP, so no model response or behavior is available. The registered rule requires stopping; the other 39 rows remain assigned and unattempted. The V5 batch will not be resumed or retried. V4 remains separately closed.

No conclusion follows about DeepSeek's fact-use ability, shared incentives, peer communication, coordination, or intent. The immediate no-proxy checks later passed, consistent with an intermittent local resolver path, but the root OS/network cause is not identified.

The analyzer's hash-mismatch warning is a known false positive: independent raw-byte SHA matches the attempt-start record; the transport terminal omits the hash. The frozen analyzer remains unchanged.

**Next action:** diagnose and test a no-proxy transport that resolves once and uses that exact address for TLS with `api.deepseek.com` SNI/hostname verification, using only offline/fake-server tests. Any subsequent real-model run must be a separately versioned registration; do not reuse V5's logical request.
