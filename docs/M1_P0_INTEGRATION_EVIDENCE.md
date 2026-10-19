# M1-P0 Local Integration Evidence

**Scope:** offline runtime, Mock reproduction, and local loopback HTTP tests only. No model completion, server launch, preflight request, paid API, detector, or M1 research behavior was run.

## Source and environment

- Topic branch: `codex/m1-p0-local-qwen-integration`.
- Base checkout: prior accepted offline gate commit `29c27b8338314bf3e152c5255dc95e6d23f3e66b`, descending from accepted M1-R base `5786852f8280af94256c2f9a16f7e872ffdd9146`.
- Current source snapshot in both new generated artifacts: `e1ac7b424b7c44cd922eb7a6b3432ea894bf238ab171b02c68019a29eeeca6e6`.
- Run manifests record Git HEAD `29c27b8338314bf3e152c5255dc95e6d23f3e66b` with `working_tree_clean=false`; the verifier authenticates the full per-file source snapshot rather than relying on the commit label alone.
- Local Qwen3-8B artifact: `E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf`; size 5,027,783,488 bytes; SHA256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`.
- Environment facts and full hardware/model inventory: [M1_P0_LOCAL_ENVIRONMENT.md](M1_P0_LOCAL_ENVIRONMENT.md), with raw command output in `runs/m1_p0_local/iteration-01/`.

## Actual offline results

| Check | Result | Preserved evidence |
|---|---:|---|
| Full repository regression | **102 passed** | `runs/m1_p0_local/iteration-01/pytest-full-offline-final.log` |
| Final rerun after evidence/decision updates | **102 passed in 11.83s** | `runs/m1_p0_local/iteration-01/pytest-full-offline-delivery.log` |
| Focused runtime/backend/HTTP regression | **52 passed** | `runs/m1_p0_local/iteration-01/pytest-focused-runtime-http-final.log` |
| V2 25-episode deterministic Mock run | **PASS**, 25/25, five per condition, 95 logical requests, 95 attempts / 190 cap, independent settlement and E recomputation, behavioral evidence flag false | `runs/m1_p0_local/offline-v2-mock/`; generation and independent verifier logs in `runs/m1_p0_local/iteration-01/` |
| V2 adversarial Mock canaries | **PASS**, 11 traces / 18 assertions; no-chat isolation, A/B-only routing, C exclusion, malformed ballot, timeouts, budget, welfare/score separation, schema and self-history checks | `runs/m1_p0_local/v2-canaries/`; generation and independent verifier logs in `runs/m1_p0_local/iteration-01/` |
| Actual adapter to offline loopback HTTP service | **7 passed**; 7 scenario records and 8 observed HTTP requests; exact schema, request/response hash, error body, timeout, duplicate ID and budget evidence recorded | `runs/m1_p0_local/iteration-01/http-contract-requests.jsonl`, its summary and `pytest-http-contract-evidence.log` |
| Historical V1 and prior accepted V2 gate artifacts | **PASS**, manifest bytes unchanged | Included in full tests; old integration reports/protocol are preserved byte-for-byte as `M1_P0_GATE_*` files |

The loopback service is an offline test server returning deterministic canned responses. The response payload is not from a model. A simulated `oneOf` rejection is retained and surfaced as a non-retryable error. No actual vLLM or llama.cpp server was contacted.

## Retained failures and revisions

- First loopback attempt: 6 HTTP-dependent cases failed before reaching the service with Windows WinError 10013; a repeated run and the full focused suite passed. `pytest-local-http-first-attempt-incident.txt` records the first outcome; the initial invocation output was not redirected, so it contains a clearly labeled excerpt/summary rather than a fabricated full trace. The retry is preserved in `pytest-local-http-loopback-retry-pass.log`.
- First focused run after seed addition: **4 failed, 47 passed** because the old canary/verifier exact-field allowlists rejected the new researcher-only generation seed. Failed canary case/summary files are preserved under `canary-generation-first-fail-v1/` and `canary-generation-first-fail-v2/`; raw test output is `pytest-focused-runtime-http.log`.
- Intermediate focused rerun: **1 failed, 50 passed** because the independent run verifier still required the pre-seed request envelope. The full raw traceback is `pytest-focused-runtime-http-second.log`.
- Corrective change: current-source runs now require the seed, recompute it from T's seed block plus agent/stage, reject E exposure, and still accept archived V1/V2 schemas. A tamper test changes a seed and recomputes the request-file hash; verification rejects it.
- The initial structured-schema test mismatch and disabled-config validation failures remain in `pytest-local-schema-first-fail.log` from the implementation iteration. No failing scenario or negative sample was removed.
- Raw test logs preserve terminal output verbatim, including trailing spaces in traceback context. The source/document whitespace check excludes `runs/` evidence files so it does not rewrite or normalize failure records.

## Key artifact digests

| Artifact | SHA256 |
|---|---|
| Current runtime source snapshot | `e1ac7b424b7c44cd922eb7a6b3432ea894bf238ab171b02c68019a29eeeca6e6` |
| Disabled local model draft config | `afe4cdd91fb71606b2d66ae533ff9222b00603d94cd79c704a4cc92e1b5acc92` |
| New offline V2 run manifest | `baeae58c394b3cd25b0ba0a925e9cb26a8116bf0a5a9e859c1b265814d5ccc6c` |
| New V2 canary manifest | `e61208860c485ad25516ed67d6245f70542c2b1788633a607ad088d572f3bfd9` |
| Offline HTTP request/response JSONL | `ea7ea10c66575d6876ae19e5584b8603f8ae500e98c9ccc6737de37eaa91202a` |
| Previous integration evidence preserved copy | `93b648aa026bd5f72e7ff719659b4c9864757979933a3f6597b3e228dd17b148` |
| Previous integration decision preserved copy | `db1ededb03929c022f926bc2616a3d451c2a5ee37a660b1be67e6a9dd5a56d86` |
| Previous V2 protocol preserved copy | `de6f1f2e0b9bc72bcc45b93813e440b9ce44bc4760e7a71eff5494fdbc83c8bb` |
| Previous integration TRD preserved copy | `3262ecec3e4bb1a45479a66e9a27b5f2182303c337b6497b2c0dbb50e86641ff` |
| Previous V2 source snapshot archive | `bbdb0a3720662331a38de000f458eb0e0406d8d1c4284122bb3442aeac8d08a8` |

The per-run manifest contains exact hashes for T, B, E, requests, observations, prompts, schemas, configuration and randomized order. The archived pre-change V2 source list is authenticated separately so the older accepted run remains verifiable after these additions.

## Reproduction

Run from the topic worktree root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python -m pytest -q
python -m colluscope m1r --config configs/m1-r-offline-v2.toml --out runs/m1_p0_local/reproduction-mock
python -m colluscope verify-m1r --run runs/m1_p0_local/reproduction-mock
python -m colluscope m1r-canary --config configs/m1-r-offline-v2.toml --out runs/m1_p0_local/reproduction-canaries
python -c "from pathlib import Path; from colluscope.m1_runtime import verify_canary_suite; print(verify_canary_suite(Path('runs/m1_p0_local/reproduction-canaries'))['status'])"
$env:COLLUSCOPE_OFFLINE_HTTP_EVIDENCE = 'runs/m1_p0_local/reproduction-http.jsonl'
python -m pytest -q tests/test_openai_compat_http_contract.py
Remove-Item Env:COLLUSCOPE_OFFLINE_HTTP_EVIDENCE
```

The commands above use deterministic Mock episodes and a test-only `127.0.0.1` HTTP service. They do not start an LLM server or call a model.
