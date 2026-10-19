# M1-P0 GGUF Candidate Frozen Protocol V3

**State:** frozen for offline review; **not authorized for live execution**.
**Protocol:** reuses `m1-p0-frozen-v2` prompt text and action schemas unchanged.

The complete frozen copy is at [`runs/m1_p0_local/gguf-iteration-01/frozen-protocol/`](../runs/m1_p0_local/gguf-iteration-01/frozen-protocol/). The manifest verifies eight files (five prompt/schema files and two TOML configs plus candidate metadata); its aggregate SHA256 is `e62511ad52d54a1fb4624d58b19855ff0a69a3fe0e1ea1a968acb96f0c09748b`.

## Exact prompt/schema files

| File | SHA256 |
|---|---|
| `prompts/system.txt` | `6dc1d0daaf2625e0f326f20ac854c190bc748e71ed8401b330dc79e90e86cf70` |
| `prompts/message.txt` | `f70dff7dacec165d26354c60cbe331916f127770ae2b9549fe813009d3324d66` |
| `prompts/ballot.txt` | `c80c0091f4e8d27d08acf6a1cf1ae4f84267230a1639ed06dc58f292cf9bbd0d` |
| `prompts/communication.schema.json` | `8c0c6744aa14c7e12578183782120949e3d65242d15ba6edf8b76a223d51b63f` |
| `prompts/ballot.schema.json` | `0bb4b7e14beda8b88fd955148f4bd485f922ab2fb329c9ad1e7ce38b9339c406` |

The copied M1-R condition config SHA256 is `e2c780de0e8c5ecf4b43f47acf5565a0ee1808e103e420365d27d4ce32647fd3`. The default-denied local backend config SHA256 is `934336c750425e7a2f8dd1577602ed0c7e4177bcc8d7270ed3704ad6853828b3`.

## Model and runtime identity

- Checkpoint: `E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf`; SHA256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`; upstream `Qwen/Qwen3-8B-GGUF`, immutable revision `6a569868d07d3bd59e8b97fb001bf8c0b254bb20`.
- Server candidate: llama.cpp 10068, commit `571d0d540`; launcher SHA256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`; 53-file runtime bundle SHA256 `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759`.
- Static tokenizer: GGUF embedded `qwen3 / gpt2 / qwen2`; tokenizer identity `06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f`; chat template SHA256 `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361`; libraries `tokenizers==0.19.1`, `jinja2==3.1.4`.
- Candidate launch settings: loopback `127.0.0.1:8080`, context 4096, one slot, Vulkan1, all GPU layers, fit off, offline, no WebUI, no warmup, reasoning off, reasoning format none. The exact generated command is in `candidate-protocol.json`; it was not executed.
- Sampling: temperature 0, top-p 1, top-k 0, min-p 0, sampler order `top_k;top_p;min_p;temperature`, per-request deterministic seed from frozen seed block/agent/action scheme. Input cap 3072; message output cap 512; ballot output cap 256.

## Episode order and interpretation

The frozen five conditions and reward amounts are exactly those in `m1-r-offline-v2.toml`. In chat arms A and B each receive one optional message action; delivery occurs only to the named recipient after both actions parse. Then A, B, and C submit sealed ballots. In no-chat arms there are no message requests or other pre-vote outputs. The environment announces the decision and welfare only after settlement.

The M1-P0 call graph is 75 ballot calls plus 20 A/B message decisions = 95 logical requests. Two attempts per request yields a 190-HTTP-attempt ceiling. The independent preflight ceiling is six logical requests / 12 HTTP attempts / four generations; comprehension probes are zero. The shared-target confound and message-turn confound are not resolved by this protocol.

## Failure policy and authorization

Only transport timeouts/connection errors and HTTP 5xx are retryable, once. Schema rejection, malformed output, wrong model alias, tokenizer/template mismatch, unsupported action, context overflow, and budget exhaustion are terminal. Raw requests, responses, errors, and partial episodes are retained. No model fallback, JSON repair, replacement episode, label edit, or deletion is permitted.

The config has `model_calls_enabled=false`, `preflight_enabled=false`, empty approval IDs, and a `$0.00` external API spend ceiling. The 6-request preflight and any 25-episode live pilot both remain unauthorized. A completed fake-server test does not change this state.
