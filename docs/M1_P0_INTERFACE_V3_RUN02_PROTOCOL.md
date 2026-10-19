# M1-P0 Interface V3 Local Preflight — Run 02

**Status:** frozen for one user-authorized local compatibility preflight. This authorizes no research episode, 25-Episode Pilot, M2 evaluation, or training.

## Scope and identities

- Run-scoped approval: `USER-APPROVED-M1-P0-IF-V3-LOCAL-8081-6L12H4-20261019-RUN02`.
- Model: `Qwen3-8B-Q4_K_M.gguf` at `E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf`; expected SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`.
- Runtime: frozen llama.cpp build `b10068-571d0d540`; launcher expected SHA-256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`; 53-file runtime bundle expected SHA-256 `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759`.
- Endpoint: `http://127.0.0.1:8081`; server must launch with `--offline`, bind only `127.0.0.1`, and pass the exact PID/image/listener-owner gate before any HTTP request. Client proxy discovery is disabled. No third-party endpoint or provider credential is configured.
- There is no extra unbudgeted `/health` HTTP probe. Process liveness, executable identity, and exact loopback listener ownership are checked locally; the first budgeted `/props` request establishes the HTTP service/model identity.
- The frozen tokenizer is embedded in the GGUF and locally measured by the repository's GGUF tokenizer implementation. The expected tokenizer, vocabulary, merges, and Jinja template digests are recorded in the approved run config and preflight evidence; the server's `/tokenize` result must exactly match the local IDs for the exact rendered prompt.

The only run-scoped config changes from `configs/m1-p0-llama-local-draft.toml` are: enable this preflight; set the unique approval ID; move the local URL and server port from 8080 to 8081; and set the matching live-preflight authorization field. The reward/condition definitions, model, binary/runtime bundle, prompt/schema files, sampling, tokenizer, timeout, and full-Pilot approval remain unchanged. The exact generated config and diff are retained locally under `runs/m1_p0_local/`.

## Frozen request sequence and hard limits

The preflight sequence is the V3 sequence from `docs/M1_P0_PRE_REGISTERED_PROTOCOL_V3.md`:

1. `GET /props` to verify alias, model path, build, context, and frozen server settings.
2. `POST /apply-template` for the exact frozen rendered prompt.
3. `POST /tokenize` for that same prompt; token IDs must equal the pinned local tokenizer output.
4. One ballot completion under the frozen ballot schema.
5. One message completion whose prompt asks for `send_message`.
6. One message completion whose prompt asks for `no_message`.

Budgets are hard maxima of **6 logical preflight requests, 12 HTTP attempts, and 4 model-completion attempts**. There are no comprehension probes. The frozen per-request transport retry policy allows at most one retry for retryable transport/timeout failures. Invalid JSON, schema/action errors, truncation, identity mismatch, template/tokenizer mismatch, or context failure stop the preflight. No failed completion is repaired, replaced, or resampled, and an episode is never started by this runner.

For a message-stage completion, either schema-valid `send_message` or `no_message` is interface-valid. The exact observed action is recorded. Whether it matches the prompt's requested action is a separate diagnostic (`followed_instruction`); it does not change interface validity. In particular, a valid `no_message` is not a JSON/schema error, and a request is never repeated to obtain `send_message`.

## Reproduction command

After code is committed, run exactly once from the repository root with the run-scoped config and a fresh output directory:

```powershell
python scripts/run_m1_p0_local_preflight.py `
  --config runs/m1_p0_local/approval-scopes/m1-p0-interface-v3-run02.toml `
  --out runs/m1_p0_local/m1-p0-interface-v3-local-preflight-run-02 `
  --approval-id USER-APPROVED-M1-P0-IF-V3-LOCAL-8081-6L12H4-20261019-RUN02
```

The single-use approval ledger is stored locally at `runs/m1_p0_local/approval-ledger/`. Exact request/response bytes, server logs, GPU/phase samples, errors, and manifests stay under the local run directory and are not committed or pushed. This file defines the authorized attempt; the run evidence records the actual commit, environment, prompt/config/tokenizer/runtime digests, counts, and terminal status.
