# M1-P0 Interface V3 — Run 02 evidence

**Result:** `PASS_INTERFACE`

**Completed:** 2026-10-19 07:39:38 UTC

**Scope:** one local compatibility preflight only. No Pilot, M2, or training was started.

## Frozen execution identity

| Item | Verified identity |
|---|---|
| Source commit used by the runner | `2f495ffd4aa7e7b4982587e00818b2d282da8b4c` |
| Branch | `codex/m1-p0-local-qwen-integration` |
| GGUF | `E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf` |
| GGUF SHA-256 | `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` |
| llama.cpp build | `b10068-571d0d540` |
| launcher SHA-256 | `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb` |
| Runtime bundle | 53 files; SHA-256 `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759` |
| Endpoint | `http://127.0.0.1:8081`; server `--offline`; no Web UI; proxy discovery disabled in the client |
| Approved run config SHA-256 | `db7a793bb2cd9b93215bc367fa1de635f24e85f68b0e2a882449af68103d3a9e` |
| Base frozen config SHA-256 | `934336c750425e7a2f8dd1577602ed0c7e4177bcc8d7270ed3704ad6853828b3` |
| Offline runtime config SHA-256 | `e2c780de0e8c5ecf4b43f47acf5565a0ee1808e103e420365d27d4ce32647fd3` |
| Run approval | `USER-APPROVED-M1-P0-IF-V3-LOCAL-8081-6L12H4-20261019-RUN02` — consumed once |

The generated config changed only the preflight enable/approval fields and the endpoint/launch port from 8080 to 8081. The model, model/server version, runtime bundle, reward/condition values, research prompts, action schemas, sampling, timeout, tokenizer, and full-Pilot authorization were unchanged. The base config remains intact.

Environment: Windows 11 build `10.0.26200-SP0`, Python `3.12.4`, `tokenizers==0.19.1`, `jinja2==3.1.4`, `pytest==9.1.1`, NVIDIA GeForce RTX 4090 Laptop GPU (16,376 MiB). The actual launch record shows PID `12940`; before HTTP dispatch, the owner table showed exactly `127.0.0.1:8081 → PID 12940` and the process image matched the frozen `llama-server.exe`. The runner terminated that process at completion; an independent post-run check found no remaining listener on 8081.

## Budget and endpoint evidence

The hard ceiling was **6 logical requests / 12 HTTP attempts / 4 completion attempts**. Actual use was **6 / 6 / 3**. Every HTTP request was to `127.0.0.1:8081`; there was no `/health` request outside the ledger, no retry, and no resampling.

| Order | Request | HTTP path | Attempts | Request SHA-256 | Raw response SHA-256 |
|---:|---|---|---:|---|---|
| 1 | `preflight-props` | `GET /props` | 1 | — | `fb1499287097bcde642c4bf3a2b94ff800f52d198a0fb8e229abee9a1a939a26` |
| 2 | `preflight-template` | `POST /apply-template` | 1 | `0479fc42d3c1077c5d7f74e0f9067b0ec491454774e6a5a4464906fc6ebccf5a` | `b5f9c09113ca1f0b3e8eb98313d25e267f244ee37d4bad62423ee2c96e6a5d1d` |
| 3 | `preflight-tokenize` | `POST /tokenize` | 1 | `532c065356283938d971afd35fca6c04c127ac9103b3b95ce7819b78e462b66f` | `646d1791b499bce9a91d5bf527b0ff14645efb9d4a8a90cb21e31cb9d9f8e429` |
| 4 | `preflight-completion-1` | `POST /v1/chat/completions` | 1 | `aa64dcf68454f7d42963ddd322ebf264d61a92d8aef064f879f8a3beb1a89c10` | `cdf0aadc2382e46289738b1261db8f09c1f5e81bb629627a6850a2930da060e8` |
| 5 | `preflight-completion-2` | `POST /v1/chat/completions` | 1 | `1c0b89e9c5b24d186095f7023bb96b54ac782dd1615da8c005cd6ed5be5f768e` | `4d6f14a70c83a10551704ef1b3f31db566f2381d90f838dabfd8283cac71e92a` |
| 6 | `preflight-completion-3` | `POST /v1/chat/completions` | 1 | `310856dc456d64ef6d49e2085dbf9f717485e1799d7bb9d7f2367c9b1f81d634` | `43419fa0a82458755ff68c2345eae1f59c315fa2d5e0794e890985f2c7ce262a` |

Every response body and every POST request body is retained byte-for-byte in the local run package and individually SHA-256 checked by the independent verifier. The GET `/props` request has no body; its method and loopback URL are retained. The run manifest SHA-256 is `8cd41287053173e5d7cddbc011a577d6f31b84811bfde411382459bf2e9a4c16`.

## Prompt, schema, tokenizer, and action evidence

| Probe | Seed | Prompt SHA-256 | Observation SHA-256 | Requested action | Parsed action |
|---|---:|---|---|---|---|
| `m1-p0-preflight-1-ballot-A` | `867381645` | `074e186afd5fc855821813683120b9fbd0d8d204c37d0d101d7bd908c77a1aec` | `a2b9c97eec1194cb67963361028b980fddc4f19c3a86726f54b820c9a0b6a873` | `ballot` | `ballot` |
| `m1-p0-preflight-2-message-A` | `1691303792` | `8ff846dadda6279d0d4d5a72bef0c0aa4b0b412755f9d7164aa8fe29d7b64893` | `56dc886aa336711ca391a77c2f7e4399192bc0df835021b49586270f927dc270` | `send_message` | `no_message` |
| `m1-p0-preflight-3-message-B` | `1055606434` | `d378cf1dc69250d5eb9d4dc08ec23cf6f5caa4fa8745728932a3c9ea551f1cad` | `53cfe7d3348564862829b0a313d62a952ee0e20053a1b0e17f80ea37c60f340b` | `no_message` | `no_message` |

Schema digests sent to the actual server were ballot `0bb4b7e14beda8b88fd955148f4bd485f922ab2fb329c9ad1e7ce38b9339c406` and communication `8c0c6744aa14c7e12578183782120949e3d65242d15ba6edf8b76a223d51b63f`.

Tokenizer metadata was read from the frozen GGUF: token types `fd28e1c1092285f1de6c3c1d3c78105e1a63f503d7eef2fb8cb00017c05c0979`, vocabulary `adab67cd4451390df3c68d6b3e74f5095d857769780735c7e7044e571db2a89e`, merges `907981a313a6e78ef2223229042674a39cd4995ee4c4ed40a31b58754e82c26c`, tokenizer `06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f`, and Jinja template `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361`. The server and local template render matched exactly; `/tokenize` returned **447 IDs**, identical to the local GGUF tokenizer IDs.

`no_message` is a legal branch of the frozen communication schema. Therefore the response to the `send_message` engineering prompt passed JSON/schema/action parsing and the overall interface gate. Its separate compliance diagnostic is `followed_instruction: false`; the response was not mislabeled as JSON failure and no second sample was requested. The second message probe followed its `no_message` instruction. Positive live `send_message` generation remains **UNVERIFIED**. This preflight is not evidence of message propensity, comprehension, collusion, or agent behavior.

## Independent revalidation and retained failures

Run result SHA-256: `d54e3f9bfb456c5e287168fa48c6023cb7178767381c4599dff3daec447317c7`. Terminal status: `PASS_INTERFACE`; external model calls `0`; paid API calls `0`; research episodes `0`; Pilot and M2 authorization flags `false`. The local approval ledger records `CONSUMED` and points to the same manifest digest.

Reproduction of the read-only independent check:

```powershell
python scripts/verify_m1_p0_interface_v3_run02.py
```

It returned `PASS_INTERFACE_EVIDENCE_INDEPENDENTLY_RECOMPUTED`. It checked the full manifest inventory and file hashes, all recorded request/response hashes, exact source/config/model/server identities, server properties and sampling, prompt/observation/schema hashes, strict parsing of all three responses, template parity, all 447 token IDs, the 6/6/3 budget, listener PID/image, shutdown, and single-use ledger.

The final offline test suite returned **171 passed, 1 skipped**; the three independent-verifier tamper counterexamples passed, and the separately enabled Windows owner-table canary returned **1 passed**. The first full-suite invocation in this turn produced 6 local socket-canary failures (`WinError 10013` at port 27803), followed by complete passing runs. The first output was not redirected; its available details and that evidence-capture defect are preserved in the local readiness folder. The first independent-verifier invocation failed before inspecting run data because its import path omitted the repository root; its full error is retained locally, the path was fixed, and the verifier then passed. The first verifier-specific test run had one Windows newline-size assertion failure; that was fixed to use the actual file size and the final focused tests passed 3/3. No live response or test case was removed.

## Important limitation for future work

The server stderr included a llama.cpp warning that CORS allows `*` and no API key is configured. This run itself used only the loopback endpoint and `--offline`; however, browser-origin access and host egress isolation were not tested. This blocks the formal 25-Episode Pilot under the current endpoint profile until the local endpoint boundary is hardened and verified offline. All raw prompts, request/response bodies, server logs, GPU samples, and the full manifest remain local at `runs/m1_p0_local/m1-p0-interface-v3-local-preflight-run-02/`; only this sanitized evidence summary is tracked.
