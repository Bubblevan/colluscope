# M1-P0 Formal 25-Episode Pilot — Frozen Run Protocol

**Protocol status:** frozen before the newly authorized run. This document records the run plan; it does not claim that a preflight or episode has passed.

## Authorized scope

The user directly instructed the project to start the formal 25-episode Pilot on 2026-10-19. The run is local-only, uses the already selected model/runtime and existing M1-P0 V2 research protocol, and stops after 25 assigned episodes or an explicit runtime failure. M2, model training, detector comparison, and additional Pilot batches are outside this authorization.

The run-scoped identifiers are `USER-REQUEST-FORMAL-25-EPISODE-PILOT-PREFLIGHT-2026-10-19` and `USER-REQUEST-FORMAL-25-EPISODE-PILOT-2026-10-19`. They are single-use and are recorded in the local approval ledger before server launch.

## Frozen research inputs

- Model: `Qwen3-8B-Q4_K_M.gguf`, SHA256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`.
- Runtime: the already selected llama.cpp 10068 build, commit `571d0d540`; launcher SHA256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`; complete local bundle SHA256 `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759`.
- Endpoint: `http://127.0.0.1:8081/v1`, bound to loopback, offline mode enabled, no Web UI, no provider fallback, and $0 external API spend ceiling.
- Research configuration: the existing five M1-P0 conditions, five frozen seed blocks, reward amounts, prompts, schemas, action output contract, sampling parameters, tokenizer, and settlement rule. The run copies their exact bytes into its evidence package before execution.
- Sampling: temperature 0, top-p 1, top-k 0, min-p 0; context 4096; reasoning disabled; sampler order `top_k;top_p;min_p;temperature`.

No model, research prompt, reward, condition, seed, sampling, parser, or outcome acceptance rule is changed for this run. The only runtime change from the historical interface run is endpoint hardening and a budget-accounted security preflight.

## Runtime boundary and preflight

The server receives an ephemeral per-run API key through `--api-key-file`; the key file is created empty, its inherited NTFS permissions are removed, and the current user's SID receives full control before the key is written. The key is passed to the adapter only in memory, its hash is recorded, and the file is removed after the server stops. The server command restricts CORS to `localhost` and disables CORS credentials. The process uses llama.cpp `--offline`; the client disables proxy discovery and refuses non-loopback URLs and redirects.

Before any preflight completion or research episode, the six-logical-request Interface V3 preflight must:

1. Request `/props` without authentication and observe HTTP 401. This is attempt 1 of the `preflight-props` logical request.
2. Request `/props` with the per-run key and an untrusted `Origin` value, and verify that the response does not allow `*` or reflect that origin. This is attempt 2 of the same logical request.
3. Verify the model properties, chat template and tokenizer, then run the fixed ballot, `send_message`, and `no_message` interface probes.

The routine fresh-run preflight has six logical IDs, seven HTTP attempts, and three generation attempts. Its hard ceilings remain six logical requests, twelve HTTP attempts, four generations, and two attempts per logical request. All attempts and raw bodies are recorded. A failed authentication or CORS canary stops before a generation probe; any later preflight failure stops before episode 1. No separate `/health` HTTP request is sent outside this ledger.

## Episode budget and failure policy

The frozen call graph is 25 × 3 sealed ballots = 75 logical requests, plus 10 chat episodes × 2 A/B message decisions = 20, for a maximum of 95 logical requests. Each may use at most two attempts, for a maximum of 190 Pilot HTTP attempts. There are no comprehension probes. The runtime enforces those ceilings.

Every assigned episode is retained, including malformed actions, timeouts, failed deliveries, incomplete chat pairs, and settlement failures. Episodes are never replaced. A valid `no_message` is an observed action and is not resampled to obtain a positive message. Public score/welfare, realized task scores, private rewards, messages, and ballots retain their frozen meanings and permissions.

## Interpretation boundary

The Pilot is exploratory behavioral evidence about this fixed model, task, and implementation. An assigned condition is an experimental intervention, not an action label. Ballots, message sending/delivery, harmful allocations, welfare changes, and latent intent remain separate fields. Shared-target agreement without communication cannot establish communication-induced coordination. This Pilot does not test a detector and cannot by itself establish real-world collusion or external validity.

## Reproduction entry point

After the source freeze commit, the run uses:

```powershell
python scripts/run_m1_p0_local_pilot.py `
  --config runs/m1_p0_local/formal-25ep-pilot-20261019/configs/full-pilot.toml `
  --runtime-config configs/m1-r-offline-v2.toml `
  --out runs/m1_p0_local/formal-25ep-pilot-20261019/run
```

The run-specific config and raw model responses remain local. The repository code and sanitized evidence/decision documents may be committed; raw prompts, private rewards, model responses, and server logs are not pushed.
