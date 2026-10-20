# M1 Package Replication v3 — Runtime TRD

**Status:** implemented for offline review; live dispatch disabled by default.
**Runtime:** `src/colluscope/m1_package_replication_v3_runtime.py`; CLI `scripts/run_m1_package_replication_v3.py`.

## Runtime contract

The runner consumes the frozen 24-group schedule and existing M1-P0 V2 task/prompt runtime. It assigns all 120 episode-condition slots before execution and uses the deterministic runtime settlement to create T (researcher-only assignment/incentive), B (actual agent actions and settlement), and Public-only E evidence. Incentive assignment/delivery and message sending/delivery remain separately represented by the base runtime. No private message content is exported into E.

The candidate config is `configs/m1-package-replication-v3.toml`. It fixes the local Qwen3-8B Q4_K_M file, llama.cpp b10068 build, GGUF tokenizer/template identity, sampler, context, timeouts and 127.0.0.1:8081. Static config sets model calls and preflight to false, contains no approval ID, and records `NOT_AUTHORIZED`. Its parser enforces the exact v3 request budget and rejects external URLs, a changed port, changed reward/prompt profile, retries, or a live flag in the static candidate file.

## Request accounting and failure semantics

The call graph is 360 ballots + 96 message decisions = 456 logical generations. Each logical request allows one HTTP attempt, so the generation ceiling is 456 with no retry or replacement. Three authenticated identity checks are actually needed per server startup (`/props`, `/apply-template`, `/tokenize`); their authorization ceiling is 24 across the run to account for restarts. The hard total physical HTTP ceiling is 480. Each physical request is reserved in an fsync-backed append-only hash-chain ledger before transport. The request ledger never stores an Authorization header value; it records only auth type and key hash.

Every generation request payload and response body, finish reason, reported usage and timing are preserved in the ignored local run directory. Identity-check request bodies are journaled before dispatch; successful raw response bytes are stored as base64 with a byte hash before parsing, so even malformed HTTP 200 JSON remains auditable. Invalid or truncated model output terminalizes its assigned episode and is retained. Transport/server/runtime failure terminalizes and preserves the in-flight episode, halts the run, and blocks resume pending review. A crash after a durable pre-call reservation never replays that request: an episode left open at resume is recorded as `FAILED_INTERRUPTED_NO_REPLAY`. Terminal episodes and request IDs are never regenerated. No output is repaired or treated as a successful action after parsing failure.

## Live gates and storage

`--check-only` is the default executable path. `--live` requires a formally registered experiment, immutable approval batch bound to the exact preregistration, an active matching budget snapshot, unexpired approval, successful registry audit, matching frozen source hashes, and an exact experiment-specific approval ID. An M4/DeepSeek grant is not accepted for M1/Qwen.

The runner validates the output path and rejects symlink/junction traversal before creating any run directory. It starts the frozen local llama.cpp process only after checking that port 8081 has no listener. It uses a per-run API key in an ACL-restricted directory, checks the launched process image and listener owner, disables network proxies, rejects redirects and non-loopback targets, and verifies model/server/tokenizer/template identity. It never contacts or terminates an unknown listener and has no provider fallback. Run artifacts must be below Git-ignored `runs/m1_100/m1-package-replication-v3/`; raw prompts, responses, observations, private traces and server logs remain local under the restricted ACL.

## Recovery and reproducibility

Append-only JSONL journals use a sequence number, previous-record hash, record hash, flush and `fsync`. On startup, the runner checks the full chains, frozen assignment plan, logical/physical request reservations, unique episode starts and the hard caps. Inconsistent/tampered ledgers are rejected. A missing initial assignment plan cannot be inferred from partial rows. The environment manifest stores source/config/schedule hashes, model/runtime identity, tokenizer metadata, approval reference, operating environment and request ceiling. All original failures and incomplete groups remain in the denominator.

## Validation boundary

Offline validation consists of schedule generation and independent matrix checks, prompt-profile checks, `researchctl audit`, focused runtime/transport tests, and a complete repository test run with the restored historical data. Fake-server tests exercise the production HTTP adapter with scripted canned bytes only; they do not run a model or constitute a live llama.cpp compatibility check. Live model/server identity and token/template parity are still unverified until a separately approved local run.

## Exact gated command

Only after registration and a fresh exact user authorization, the command shape is:

```powershell
python scripts/run_m1_package_replication_v3.py --live --approval-id <fresh-M1-approval-id> --out runs/m1_100/m1-package-replication-v3/run-<unique-id>
```

This documentation is not authorization. No model request was sent to prepare it.
