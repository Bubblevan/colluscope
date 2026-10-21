# V5 preregistration clarification — 2026-10-21

The registered V5 preregistration was derived from the reviewed V4 draft. A few narrative strings retained old version labels. The frozen runtime/configuration are authoritative for exact identities:

- `research/schedules/deepseek-real-coordination-v5.json` contains only `v5-` request IDs and the pinned V5 schedule digest.
- `configs/deepseek-real-coordination-v5.json` points to `.cache/deepseek-recipe/tokenizer-v41.json`, SHA-256 `81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99`.
- V5 runner and analyzer import `render_v41`; no `v51` tokenizer or renderer exists or is used.
- The preregistration's phrases “V4 uses the schema-compatible sentinel,” “Tokenizer v51,” and “V4 request IDs” are inherited-copy wording. The intended V5 facts are: it uses the same `UNDECIDED` sentinel and v4.1 tokenizer/renderer, but a fresh `v5-` namespace and log directory. V4 itself remains a separate terminal record.

This clarification does not change the task, prompts, schedule, conditions, outcome gate, model settings, or budget. The registered preregistration remains byte-for-byte unchanged; this sidecar is included in the pushed execution package for human review.
