# Attempt 001 — Transport Failure Record

Sanitized forensic summary of the first and only live invocation attempt. Original request bytes and append-only ledgers remain local under the Git-ignored run directory.

- Frozen pre-run commit pushed: `31b7ebf3aa82b7dd656b3b944183fa0a92a23fc3`
- Command: `python scripts/run_deepseek_real_coordination_v2.py`
- Start: `2026-10-21T04:53:40.218509+00:00`
- Assigned request: `C1-delivered` (first fact-delivery control)
- Requested provider/model: official DeepSeek endpoint, `deepseek-flash`
- Transport result: `URLError: <urlopen error [Errno 11001] getaddrinfo failed>`
- HTTP status: none
- Returned response: none
- Retry: false
- Client-reported external cost: USD 0.00
- Conservative peak-cost reservation: USD 0.0009816
- Process exit: 1, after the client recorded the transport failure and runner raw-request revalidation raised an exception

## Byte-level record

The local request file is 996 bytes. Its SHA-256 is `e80ed1e34d72e8056fc1a572af2f29778b9ce2aa2a8bc0ad94409c523744bd9f`, equal to the hash in the `attempt_started` row. The terminal row has no request hash, but records `TRANSPORT_ERROR`, null HTTP status, null response hash, zero elapsed seconds, and `auth_header_saved: false`. The corresponding response `.bin` file does not exist; only sanitized error metadata exists.

The raw request contains the frozen control prompt and tool schema. The API key is supplied as an HTTP authentication header by the client and is not persisted. The raw logs are protected by the run-directory ACL and ignored by Git.

## Failure classification

The exception shows that this process could not resolve the provider hostname. It does not identify whether the cause was local resolver configuration, network policy, VPN/proxy state, or another machine-level DNS issue. No evidence supports attributing the failure to model capability or provider behavior.

The runner's secondary exception is reproducible from source: `_attempt_rows()` validates each terminal request hash, but the shared client writes that hash only on `attempt_started` for transport exceptions; the verifier does not fall back to the matching start record. No subsequent request was issued. The registered V2 freeze is preserved unchanged.

## Stop accounting

The first control is unassessable, not passed or failed as a model behavior test. The early-stop rule leaves the other 39 assigned requests unattempted. No game-stage requests ran and no behavioral denominator exists. Under conservative registry accounting, one dispatched attempt is one model-request ledger row, while actual external cost remains zero.
