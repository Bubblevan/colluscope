# M3 Runtime Errata 01

**Scope:** instrumentation and preflight recovery only; the frozen M3 intervention is unchanged.

The preregistered runtime source freeze was `2da217c2ea81d90a5783b5ea67c63d26a5803d86`. Its first local launch failed closed because the default execution sandbox could not produce an authoritative Windows TCP listener-owner record. That attempt made no HTTP requests and no model generations.

On a resumed run with local process-table access, the runner verified that port 8081 belonged to the launched frozen llama.cpp binary and that the authenticated `/v1/models` response contained the expected Qwen3 alias. It then failed while exporting environment metadata: `GGUFChatTokenCounter` has no `tokenizer_metadata` attribute. The config loader had already independently extracted and hash-checked the JSON-safe `backend_config.tokenizer_metadata` projection from the frozen GGUF. The implementation now writes that projection into the environment record and has a regression test that deliberately omits `tokenizer_metadata` from the counter object.

The correction does not alter task prompts, message transformations, arm order, scenario/seed IDs, payoff matrices, rewards, sampling, output schema, model, tokenizer, server, or any generation request. It changes only the source of an environment-record field. The failed startup and metadata sessions, plus the one identity-probe HTTP attempt, remain in the ignored local run directory. This erratum and the source correction are versioned before any M3 generation is resumed.

## Preserved failures

| Event | Result | Counts |
|---|---|---:|
| Default-sandbox startup | Listener ownership could not be established; run stopped safely. | 0 HTTP, 0 identity, 0 generation |
| Elevated local resume | Listener PID and model alias verified; environment export hit the metadata attribute error; server shut down and API-key file was removed. | 1 identity HTTP, 0 generation |
| New regression-test first run | Test placement accidentally moved existing settlement assertions into the new test, causing `NameError`; test-only placement fixed, production behavior unchanged. | 2 tests passed after correction |

At the time of this erratum, the run has 12 assigned groups, 0 terminal groups, 0 logical generations, 0 generation HTTP attempts, and 1 identity-probe HTTP attempt. No external inference was used.
