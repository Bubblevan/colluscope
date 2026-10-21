# DeepSeek Real Coordination V2 — Decision

**Decision: NO-GO / EXECUTION_BLOCKED.**

The first assigned fact-delivery control did not reach the provider. On 2026-10-21 at 04:53:40 UTC, the client recorded one physical request attempt for `C1-delivered`, then failed local DNS resolution for `api.deepseek.com` before an HTTP connection. There was no HTTP status, response body, model output, token usage, or billable inference. The run stopped; no retry or replacement was made.

## Counts

| Measure | Result |
|---|---:|
| Assigned logical requests | 40 |
| Physical dispatch attempts | 1 |
| HTTP responses received | 0 |
| Returned model generations | 0 |
| Estimated actual external cost | USD 0.00 |
| Remaining assigned requests | 39 unattempted |
| Behaviorally assessable fact controls | 0 |
| Agent-game episodes executed | 0 |

For conservative research-budget accounting, the registry counts a dispatched attempt, including a transport failure, as one request-ledger row. Thus one of the batch's 40 slots is consumed even though the provider returned nothing. The USD 0.0009816 peak-safe reservation is not an actual charge.

## Integrity and failure review

- The raw 996-byte request remains local and ignored by Git. Its digest matches the `attempt_started` row.
- Append-only ledgers record exactly one start and one terminal `TRANSPORT_ERROR`; there are no response bytes.
- The attempt record says `auth_header_saved: false`; the run-directory ACL grants full control only to the local `bubblevan` account.
- The client terminal row omits `request_sha256` on the transport-exception path. The runner's recovery verifier therefore raises `raw request missing or hash-mismatched`, despite the bytes matching the hash in the start row. This is a separate runtime accounting defect.
- The full frozen schedule and conditions were not run. No claims about fact use, communication, coordination, incentives, or collusion are supported.

## Stop decision

The preregistered batch has a zero-retry/no-replacement policy and a first-control gate. This attempt is retained as the failed first control; do not replay it or continue the remaining 39 requests under this authorization. A future version must fix the transport environment and terminal-hash accounting, then be frozen and authorized before further dispatch. The observed DNS exception does not identify whether its cause was local resolver configuration, VPN/proxy state, network policy, or another machine-level issue.

## Reproduction

From the repository root, verify the sanitized ledger and local evidence:

```powershell
python scripts/researchctl.py audit
Get-FileHash logs/deepseek-real-coordination-v2/requests/C1-delivered.bin -Algorithm SHA256
Get-Content logs/deepseek-real-coordination-v2/attempts.jsonl
Get-Content logs/deepseek-real-coordination-v2/responses/C1-delivered.meta.json
```

The file-hash command returns the request hash reported in the evidence record. Do **not** rerun the live runner: this frozen batch is terminal and has no retry authorization.
