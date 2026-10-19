# M1-P0 Local GGUF Runtime TRD

**Status:** offline implementation complete; live preflight and research calls are not authorized.
**Candidate:** Qwen3-8B Q4_K_M GGUF through the installed local llama.cpp server.
**Protocol basis:** the accepted `m1-p0-frozen-v2` prompts, schemas, five M1 conditions, and reward amounts remain unchanged.

## Scope

This change adds a local-only adapter and a static GGUF metadata tokenizer. It does not start the server, load model weights, call a model, run a real-agent episode, or compare monitors. `llama_server_command()` only returns a candidate command. The default config rejects live calls and preflight unless a separate approval ID is supplied; the checked-in candidate has both gates disabled.

The model bytes are at `E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf`, SHA256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`. This is the selected user-provided model. It is identified as GGUF Q4_K_M and is not mislabeled AWQ.

## Runtime flow

The existing M1-R V2 state machine remains authoritative:

1. Build each agent's task and incentive observation. Assignment/delivery records remain in researcher-only T; a returned response for that exact observation is the delivery confirmation used by the runtime, not proof of comprehension.
2. In the two chat conditions, request A's optional message action and then B's. Messages are delivered only to their named peer after both responses parse. A failed pair is retained, and a sent message is not marked delivered unless delivery occurred. C receives no communication action.
3. In no-chat conditions, make no message calls and pass no pre-vote output across agent contexts.
4. Request sealed ballots from A, B, and C. No ballot response is sent to another agent.
5. After all ballots parse, apply the deterministic plurality rule and public chair tie-break. Only then publish the decision, public welfare, and realized task scores. There is no post-result model call.

Public score rules are part of the public task observation. A public bonus is permitted task evidence; it is not a collusion label. Private reward text is only delivered to its assigned agent. Voluntary agent disclosure remains a behavior in B and enters E only if the configured auditor permission allows the corresponding private message to be observed.

T (treatment assignment), B (actual actions and settlement), E (auditor-permitted evidence), and agent-visible observation records remain separate. The adapter request has only the rendered prompt, agent/action identity, sampling fields, seed, timeout, and observation hash. It contains no condition, seed-block, oracle, split, or other-agent state fields.

## Adapter and tokenizer

`LocalLlamaCppBackend` uses Python's standard-library HTTP client and can address only `http://127.0.0.1:8080`. It disables proxy discovery, refuses redirect targets, checks the endpoint again immediately before dispatch, sends no authorization header, disables streaming and prompt caching, and records the exact JSON request, response/error, hashes, usage, timing, timeout, and attempt through the shared `RequestAdapter`.

The llama.cpp request uses the direct documented envelope `response_format: {type: "json_schema", schema: ...}`. There is no schema fallback. The request also sends the frozen `chat_template_kwargs.enable_thinking=false`, `reasoning_format=none`, exact sampler order, seed, and stage output limit. Non-2xx 5xx and transport timeouts may be retried once; schema, response, token-count, model-alias, parser, and output-limit errors are terminal. No response repair or vote substitution is allowed.

The embedded GGUF tokenizer is read from metadata only. It uses the measured GGUF BPE arrays and Jinja template with pinned local `tokenizers==0.19.1` and `jinja2==3.1.4`. The static counter is an implementation candidate. It is not considered equivalent to llama.cpp until the approved preflight exactly matches the server template and token IDs.

The installed `llama-server.exe` is a 9,216-byte launcher; the runtime code and accelerator support are in adjacent DLLs. The frozen identity therefore includes all 53 regular files in the install directory, not just the launcher. The bundle manifest digest is `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759`. Preflight rejects a changed bundle before making HTTP requests.

## Call budget

For the frozen 25-episode graph:

| Calls | Calculation | Logical requests |
|---|---:|---:|
| Ballots | 25 episodes × 3 agents | 75 |
| Message decisions | 10 chat episodes × 2 agents (including `no_message`) | 20 |
| **Pilot total** | 15 no-chat episodes × 3 + 10 chat episodes × 5 | **95** |
| **Worst case attempts** | 95 logical × 2 attempts | **190** |

The local backend and the shared `RequestAdapter` both enforce the 95 logical / 190 physical ceiling and two-attempt per-request cap. The M1-P0 completion token maxima are 75 × 256 ballot tokens plus 20 × 512 message tokens = 29,440 tokens for first attempts; the worst theoretical retry ceiling is 58,880 generated tokens. Prompt input is capped at 3,072 tokens per attempt, or 291,840 on the 95-call path and 583,680 across 190 attempts. These are hard configured bounds, not an observed token count.

The separate compatibility preflight is six logical requests in fixed order: `/props`, `/apply-template`, `/tokenize`, then one ballot, one `send_message`, and one `no_message`. It has ceilings of 12 HTTP attempts and four generation attempts. Comprehension probes are fixed at zero. An error stops the preflight; it does not roll into the 25-episode pilot.

## Conditions and interpretation limit

The five conditions in the frozen config are unchanged: normal cooperation; public common incentive without chat; private A/B target bonus with chat; the same private bonus without chat; and chat without a side bonus.

**Shared-target confound:** A and B independently receive the same rewarded target in both private-bonus conditions. They may agree on that target without communicating. Their target agreement in the no-chat arm cannot establish communication-induced coordination. Even a chat/no-chat ballot difference estimates the effect of the bundled offer of a peer-message turn (including an extra deliberation request), not the causal effect of message content alone. Neither agreement, chat availability/use, reward assignment, target execution, nor welfare loss is by itself a collusion label.

## Frozen files and failure policy

`runs/m1_p0_local/gguf-iteration-01/frozen-protocol/` contains byte-for-byte copies of all five V2 prompt/schema files and both relevant TOML configs, plus `candidate-protocol.json` and a SHA256 manifest. Its aggregate manifest SHA256 is `e62511ad52d54a1fb4624d58b19855ff0a69a3fe0e1ea1a968acb96f0c09748b`.

Malformed actions, HTTP/schema rejection, changed model alias, token/template mismatch, timeouts, transport errors, exhausted budgets, and incomplete communication pairs remain explicit failures. Failed episodes are never removed or replaced. There is no fallback model, API, prompt, JSON-repair request, or hidden attempt.

## What remains unknown

Documentation for the inspected llama.cpp commit describes the direct schema shape, template kwargs, reasoning format, `/props`, `/apply-template`, `/tokenize`, context settings, and local runtime flags. It does **not** establish that this specific server build accepts the V2 `oneOf` schemas, that the static tokenizer exactly matches it, that the Qwen template renders identically, or that the model fits and behaves as intended. Those are live compatibility claims and remain unverified until a separately approved bounded preflight. This adapter test suite uses injected fake HTTP responses and is not evidence of actual llama.cpp enforcement or model behavior.
