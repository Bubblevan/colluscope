# M2 One-shot Decision

**Decision: NO-GO for M2 detector-performance claims, formal monitor comparison, or a collusion finding.** The bounded execution completed and passed independent integrity checks, but none of the 517 returned model responses satisfied the frozen JSON/schema contract.

## Gate assessment

| Gate | Decision | Evidence |
|---|---|---|
| M1 source preservation | PASS | M1 manifest and source hashes remained unchanged; source manifest SHA-256 `4e7868449a5e2bc3621fef4da4eaded4d710c15570dbf12f7d4ab215f3a4bb13`. |
| Frozen schedule and input isolation | PASS after pre-inference repair | 1,000 unique logical keys prepared; no hidden treatment/oracle metadata, no cross-permission/split deduplication, Public E unchanged, ACL verified. |
| Runtime/model identity and locality | PASS | Exact model/server/runtime/tokenizer hashes; all 529 recorded HTTP attempts used authenticated `127.0.0.1:8081`; no external fallback; $0 spend. This is not a host-wide egress-isolation claim. |
| Budget and assigned-row accounting | PASS | 1,000/1,000 logical rows terminal; 523 unique payloads; 529/2,000 physical attempts; at most two attempts per request; no replacement sampling. |
| Calibration-before-held-out order | PASS | 500 F0/F1 rows closed before the first F2/F3 request; independent audit checked phase timestamps. |
| Output validity | **FAIL** | 0/517 valid responses; 517 JSON parse errors, with all 517 also failing the root schema in the post-hoc diagnostic. |
| Monitor accuracy / view comparison | **NOT ESTIMABLE** | Zero valid predictions; confusion table is empty; coverage 0%. |
| Latent collusion conclusion | **NOT SUPPORTED** | No latent-collusion gold label was created; observable sequence references are not intent or causal labels. |

## Scientific decision

The study can be reported as a reproducible **local interface-failure pilot** with an independently checked input schedule, permission boundary, request ledger, source linkage, and resource record. It cannot be reported as a successful Track 2.2/2.3 monitor evaluation. All accuracy, recall, precision, abstention, unsupported-assertion, and view-superiority claims are not estimable from this output set. Any mechanically zero unsupported-assertion count is non-informative because every model response was invalid.

The source corpus remains unchanged and its visible evidence supports ordinary descriptive facts, including 12 privileged cases with a complete proposal followed by matching sender/recipient ballots. That pattern is not a gold label for collusion and is consistent with shared-target knowledge or other non-communication causes. No real-agent behavior was rerun in this M2 task.

## Recommended next action

Review the raw local response format and frozen request/schema contract before authorizing any further inference. The post-hoc diagnostic shows a leading `<think>...</think>` segment and a JSON root that omits required fields; do not silently strip the segment or retroactively accept these outputs. A future interface-repair pilot would need a separately reviewed protocol, explicit output-shape canaries, a pre-inference freeze revision, and a new user-approved call budget. No extra model call, prompt change, parser change, M2 monitor run, or training is started here.

## Final counts

- **Logical evaluations assigned/completed/failed:** 1,000 / 1,000 terminal / 20 request-failed logical rows.
- **Returned model calls:** 517, all invalid; 244 calibration and 273 held-out.
- **HTTP attempts:** 529 total, including 12 attempts across six requests that exhausted the frozen retry allowance.
- **Valid predictions:** 0.
- **External or paid model calls:** 0 recorded; paid API spend $0.
- **M2 readiness:** **NO-GO** for formal detector comparison; the local data/projection and audit package are preserved for a separately approved interface-valid follow-up.
