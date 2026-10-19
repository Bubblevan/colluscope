# M2-V3 DeepSeek Execution Record

## Scope and status

This document records the single user-authorized DeepSeek run against the frozen M1 corpus. It is not a standing API authorization. The permitted model is `deepseek-flash`; the optional Pro comparator is excluded. The only permitted external destination is `https://api.deepseek.com/chat/completions`. The hard provider spend ceiling is USD $5, there are no external fallbacks, and dispatch must stop before 2026-10-20 09:00 Asia/Hong_Kong.

The source freeze, protocol, prompts, configuration, schedule, scorer, and offline checks are committed and pushed before the first paid request. Their exact commit and hashes are recorded in the private run manifest. M1/M2 historical files are read-only. Official provider docs currently route `deepseek-flash` to DeepSeek-V4.1-Flash-1017; because the alias is mutable, every response's `model` and required `system_fingerprint` are checked, recorded, and must remain stable for the run. If only the alias is returned, the underlying weights cannot be independently pinned.

## Frozen input and request budget

The runner reads the existing 25 historical F0 episodes and 75 prospective M1-100 episodes, preserving the F0–F3 group split. The schedule contains 1,500 eligible evaluation rows: 250 F1 rows (10 per episode) and 1,250 F2/F3 rows (25 per episode). F0 is development-only and receives no call. The fixed F1 diagnostic consists of 15 rows, with five in each task family and one row per each of five groups; those rows remain inside the F1 denominator.

Byte-identical requests are collapsed only within the same partition, permission, model, and protocol. The frozen schedule yields exactly 916 unique request bodies: 199 F1, 371 F2, and 346 F3. The diagnostic comprises 15 of the F1 requests. At two attempts per unique request, this exact list has a maximum of 1,832 physical HTTP attempts; the executable also enforces the separate 2,250 global cap and two-attempt per-request cap. The request body's SHA-256 is checked immediately before dispatch.

Before dispatch, the runner reserves each request at the peak cache-miss input and output prices, using UTF-8 body bytes plus 256 tokens for provider framing and the full 128-token output cap. The source-freeze schedule's conservative two-attempt bound is **$2.7214722**; the final pushed-source manifest independently recomputes it. A request is refused if cumulative committed cost plus its reserve would exceed $5. Returned prompt, cache-hit, cache-miss, and completion usage are reconciled at the applicable documented rate; provider billing remains authoritative. The API's tokenizer revision is not exposed, so no local tokenizer version is claimed.

## External data boundary

Only the sanitized task-specific JSON payload is transmitted. It contains public task specifications and public ballots/outcomes for eligible views, plus exact synthetic A/B messages that were both sent and delivered for Privileged Audit views. Public-only requests preserve the source Public E message-free view. T, private reward assignment, reference labels, condition/group/episode IDs, local paths, raw researcher rows, and evaluator-only event inventories stay local. Before every request the runner verifies the expected evidence projection and rejects forbidden metadata. It does not include C messages or undelivered messages.

The API key is loaded from the approved local `.env` source only after endpoint/model validation. The key is used solely in the HTTP authorization header and is never printed or logged. Proxy handling and redirects are disabled; TLS certificate validation remains on. Every physical attempt has a durable start/terminal ledger record. Raw provider response bytes and assistant text are retained under the ignored, current-user ACL-restricted run root.

## Gate sequence and failure policy

1. Recompute the 100-case source corpus, schedule, references, prompt bytes, request IDs, privacy checks, source hashes, split membership, and cost ceiling with zero model calls.
2. Run the 15-request Flash diagnostic exactly once. The gate is at least 90% valid task-specific JSON objects with a normal `stop` finish, plus zero source, permission, endpoint, model-identity, or thinking-mode violation. Factual errors, over-abstention, and citation errors remain scored predictions and do not invalidate JSON syntax.
3. Only after a diagnostic pass, complete the frozen F1 calibration requests. The operational threshold is at least 90% format-valid over all 250 F1 evaluation rows. F1 outputs are never used to edit the frozen prompt or scorer.
4. Only after the F1 gate passes, run all eligible F2/F3 requests. These are previously exposed exploratory holdouts, not confirmatory data.

No model answer is retried or replaced. At most one retry is permitted for a documented transient HTTP status under the frozen rule (HTTP 429 only when `Retry-After` is present) or a transport failure proven to occur before connection. Timeouts, connection resets after POST, malformed answers, wrong facts, and bad citations are terminal; an interrupted `started` attempt is marked unknown and never resent. If a gate fails or the cutoff arrives, unstarted requests are assigned terminal `not_dispatched` statuses with the reason. A process crash before finalization may be resumed only within the same approved window and from the append-only ledgers; after cutoff no new request is started.

The diagnostic and calibration gates concern interface operability only. Passing them does not imply monitor accuracy. The protocol never assigns a latent-collusion label.

## Reproduction

From the repository root:

```powershell
python scripts/run_m2_v3_deepseek.py prepare --run-dir runs/m2-v3/deepseek-overnight-r1
python scripts/run_m2_v3_deepseek.py verify --run-dir runs/m2-v3/deepseek-overnight-r1
python scripts/verify_m2_v3_deepseek.py --run-dir runs/m2-v3/deepseek-overnight-r1
python -m pytest -q
```

After the clean source freeze has been pushed, the user-authorized execution command is:

```powershell
python scripts/run_m2_v3_deepseek.py run --run-dir runs/m2-v3/deepseek-overnight-r1
```

Scoring and the final integrity/hash inventory are offline:

```powershell
python scripts/score_m2_v3_deepseek.py --run-dir runs/m2-v3/deepseek-overnight-r1
python scripts/verify_m2_v3_deepseek.py --run-dir runs/m2-v3/deepseek-overnight-r1
```

Raw messages, payloads, outputs, scoring rows, and request-level metadata remain local and Git-ignored. The public report contains aggregate tables, sanitized case IDs, hashes, and no raw private-message text.

## Official provider references

- [DeepSeek Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/)
- [DeepSeek Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)
- [DeepSeek Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)
- [October 17 model update](https://api-docs.deepseek.com/news/news261017/)

The private run manifest records the requested and returned model IDs, system fingerprint when supplied, runtime/platform, Python version, prompt/config/source hashes, per-request payload/response hashes, finish reasons, exact usage counters, retry counts, and price-period assumption. The provider-managed tokenizer version is not independently observable through the response and is explicitly reported as unavailable.
