# M3 Runtime Errata 01

**Scope:** instrumentation and preflight recovery only; the frozen M3 intervention is unchanged.

The preregistered runtime source freeze was `2da217c2ea81d90a5783b5ea67c63d26a5803d86`. Its first local launch failed closed because the default execution sandbox could not produce an authoritative Windows TCP listener-owner record. That attempt made no HTTP requests and no model generations.

On a resumed run with local process-table access, the runner verified that port 8081 belonged to the launched frozen llama.cpp binary and that the authenticated `/v1/models` response contained the expected Qwen3 alias. It then failed while exporting environment metadata: `GGUFChatTokenCounter` has no `tokenizer_metadata` attribute. The config loader had already independently extracted and hash-checked the JSON-safe `backend_config.tokenizer_metadata` projection from the frozen GGUF. The implementation now writes that projection into the environment record and has a regression test that deliberately omits `tokenizer_metadata` from the counter object.

The correction does not alter task prompts, message transformations, arm order, scenario/seed IDs, payoff matrices, rewards, sampling, output schema, model, tokenizer, server, or any generation request. It changes only the source of an environment-record field. The failed startup and metadata sessions, plus the one identity-probe HTTP attempt, remain in the ignored local run directory.

A first resume after the correction correctly refused to continue because the original design-freeze check requires exact source-commit and runner-hash equality. The run had not made any generation request, so the source check was extended with a versioned, exact allowlist for this one metadata-only correction. The exception requires: the original frozen commit as an ancestor; exact equality of every frozen input hash except the runner file; a runner hash fixed in `M3_RUNTIME_RESUME_ERRATA.json`; an exact committed changed-path list; the recorded metadata-export failure; twelve assigned groups but no started/terminal groups or generation requests; exactly one successful prior identity probe for the frozen model; and verified server shutdown/API-key cleanup. The runner appends a source-authorization record before any new model call. The independent auditor separately checks the erratum manifest, Git commit contents, changed paths, runtime hash in the environment, and generation reservations. Future resume is allowed only under the same exact code commit, input hashes, and manifest hash.

The run environment and every generation-attempt reservation now distinguish the original design-freeze `source_commit` from `runtime_code_commit` and record the actual runner SHA-256. The original `design-freeze.json` is preserved unchanged.

The append-only local failure ledger also retains the first refusal to resume. A supplemental record initially used a placeholder time instead of a verified timestamp; a subsequent correction marks its event time unknown and records only when that ledger correction was written. Neither timestamp is represented as a measured model event.

## Preserved failures

| Event | Result | Counts |
|---|---|---:|
| Default-sandbox startup | Listener ownership could not be established; run stopped safely. | 0 HTTP, 0 identity, 0 generation |
| Elevated local resume | Listener PID and model alias verified; environment export hit the metadata attribute error; server shut down and API-key file was removed. | 1 identity HTTP, 0 generation |
| First post-fix resume check | Refused because the source SHA/commit changed from the original freeze; this failed before any new server start or HTTP call. | 0 additional HTTP, 0 generation |
| New regression-test first run | Test placement accidentally moved existing settlement assertions into the new test, causing `NameError`; test-only placement fixed, production behavior unchanged. | 2 tests passed after correction |

At this pre-generation checkpoint, the run has 12 assigned groups, 0 terminal groups, 0 logical generations, 0 generation HTTP attempts, and 1 identity-probe HTTP attempt. The corrected resume gate passed the focused M3 audit tests and the full repository suite (**337 passed, 1 skipped**). No external inference was used. The branch still must commit and push the exact manifest and resume implementation before continuing.
