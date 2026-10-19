# M1-P0 V2 Candidate Protocol Freeze

**Prompt version:** `m1-p0-frozen-v2`

**Behavior protocol:** inherited unchanged from accepted M1-R V2.

**Status:** offline protocol and request contract frozen for review; model-specific tokenizer/server freeze is incomplete, so live execution is NO-GO.

## Prompt and action artifacts

All SHA256 values cover exact UTF-8 file bytes.

| File | SHA256 |
|---|---|
| `prompts/m1-p0-v2/system.txt` | `6dc1d0daaf2625e0f326f20ac854c190bc748e71ed8401b330dc79e90e86cf70` |
| `prompts/m1-p0-v2/message.txt` | `f70dff7dacec165d26354c60cbe331916f127770ae2b9549fe813009d3324d66` |
| `prompts/m1-p0-v2/ballot.txt` | `c80c0091f4e8d27d08acf6a1cf1ae4f84267230a1639ed06dc58f292cf9bbd0d` |
| `prompts/m1-p0-v2/communication.schema.json` | `8c0c6744aa14c7e12578183782120949e3d65242d15ba6edf8b76a223d51b63f` |
| `prompts/m1-p0-v2/ballot.schema.json` | `0bb4b7e14beda8b88fd955148f4bd485f922ab2fb329c9ad1e7ce38b9339c406` |
| `configs/m1-r-offline-v2.toml` | `e2c780de0e8c5ecf4b43f47acf5565a0ee1808e103e420365d27d4ce32647fd3` |
| `configs/m1-p0-vllm-local.template.toml` | `9380a13d16c943c5c46a6499a92d63ad92774fab9081b55d9f1d3c3af4037c0c` |

The communication action schema has `oneOf` branches for `send_message` and `no_message`. The ballot schema requires an exact assignment over A/B/C and T1/T2/T3. Both exact schema files are in the stage prompt and in the API structured-output request. The local HTTP canary verifies their exact bytes/objects reach the server boundary; it does not establish real-server enforcement.

## Episode and visibility order

1. Deliver the public task rules and recipient-specific private score rule in separate observations.
2. In a chat arm, A and B independently submit one sealed communication action; neither response is delivered until both action requests complete. Then deliver each sent message only to its named peer. C has no peer channel.
3. Each participant submits one sealed ballot using its own observation. A/B chat ballots contain that agent's own previous action and only delivered peer messages. No-chat ballots have no message stage, peer-message field, previous message, or other pre-vote output.
4. Only after all three ballots seal, settle by the frozen plurality/tie-break rule and compute public welfare and realized task score separately.
5. Export T (assignment/research metadata), B (actual actions/outcomes), and permission-filtered E into separate paths. E does not contain treatment IDs, seed blocks, private reward instructions, oracle data, or the API sampling seed.

An HTTP response only verifies that a response was returned for the observation. It does not establish comprehension or incentive uptake. Assignment, response receipt, observed action, realized score and latent intent remain distinct.

## Request parameters frozen for a future review

| Parameter | Candidate value | Validation status |
|---|---:|---|
| Prompt version | `m1-p0-frozen-v2` | Offline hash-checked |
| Context | 4,096 tokens | Proposed only; tokenizer/server not loaded |
| Input budget | 3,072 tokens | Fail-closed client check; fake counter used offline |
| Message output maximum | 512 tokens | Sent by adapter and unit-tested |
| Ballot output maximum | 256 tokens | Sent by adapter and unit-tested |
| Temperature / top-p / top-k | 0.7 / 0.8 / 20 | Candidate only; no empirical search |
| Thinking | Disabled; `chat_template_kwargs.enable_thinking=false` | Payload tested against offline service; actual server support unverified |
| Seed | 31-bit SHA256-derived matched block × agent × stage value | Recorded, independently recomputed, absent from prompt and E |
| Timeout / retries | 60 seconds; at most two attempts, timeout/transient only | Offline fake/local HTTP paths tested; server deadlines unverified |
| Model artifact | Local Qwen3-8B Q4_K_M GGUF, exact path/hash in environment inventory | File verified; not loaded |
| Server / tokenizer | vLLM 0.32.0 is an uninstalled candidate; tokenizer revision and hashes unresolved | Not frozen for real execution |

Any future run must freeze the exact server build, model/tokenizer revisions and hashes, chat template hash, token counter implementation, memory settings, and actual local load command before it is authorized. The disabled draft config contains unresolved fields and is rejected by the runtime.

## Conditions and budget

All five conditions, reward amounts, 25 episodes, and five seed blocks are unchanged from `configs/m1-r-offline-v2.toml`. The call graph is 75 ballots + 20 communication turns = 95 logical requests, at most 190 attempts. There are zero comprehension probes. The separate engineering preflight limit is six logical requests / twelve attempts, disabled by default; the current implementation uses two GET calls if separately authorized.

No condition, reward, label, or acceptance criterion was changed to improve observed outcomes. Mock runs claim no agent behavior evidence.
