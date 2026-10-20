# M4 DeepSeek Monitor V1 — Evidence Record

**State:** request compiler and raw-response scorer are implemented; no Monitor request has been sent by this task yet.  
**Frozen protocol:** `docs/M4_DEEPSEEK_MONITOR_V1_PROTOCOL.md`  
**Plan source:** the local ACL-restricted freeze generated from the independently audited 24-group Agent run; it contains 376 rows and is byte-replayed before dispatch.

## Offline evidence

- The compiler uses the frozen B4 raw-fusion/B5 evidence-aware tasks and produces 288 natural-trace rows, 16 scripted-control rows, and 72 matched-world rows.
- Offline plan tests verified all 288 trace rows remain attached to the 24 frozen groups, both permissions and all three tasks are present, the 16 scripted-control rows are fixed, and all 24 pair/method Public-only matched-world inputs are byte-identical with separately permitted Privileged inputs.
- The pre-dispatch public/private projection test found no private message text in Public-only Monitor inputs. Source labels, construction truth, references, and case-routing metadata are kept outside model messages.
- A dedicated regression asserts the compatibility-pilot Monitor uses the same frozen message renderer as the formal plan.
- The full pre-inference repository suite recorded 546 passed, 1 opt-in host-dependent test skipped. A final full suite must be rerun at the pushed freeze commit before the first model request.

## Post-run scoring slots

After authorization-controlled dispatch, populate this record only from the frozen plan, raw Monitor request/response bytes, the append-only attempt ledger, and independent replay output. Include all 376 assigned row statuses, parse validity, citation membership, task-specific exact-match/abstention counts, B4/B5 paired coverage, returned model/fingerprint, input/output tokens, duration, provider usage cost and global reserve. A missing/failed row remains assigned and is never replaced.

Private or Privileged Audit message text must remain in local ACL-restricted storage. Published tables may include event IDs, counts and hashes only after checking they do not reproduce private content.
