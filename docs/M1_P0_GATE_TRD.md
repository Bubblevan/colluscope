# ColluScope M1-P0 Integration Gate TRD

**Status:** Offline integration candidate; real-model execution is not authorized.
**Source baseline:** accepted M1-R HEAD `5786852f8280af94256c2f9a16f7e872ffdd9146`.
**Scope:** Correct the action-schema and message-history omissions, integrate a local-only OpenAI-compatible vLLM adapter behind an explicit disabled-by-default configuration, and falsify the offline runtime assumptions. This is not a behavior experiment, monitor study, or M2 start.

## Highest validity risks and counterexamples

1. **Action schema omitted from prompt.** The v1 renderer asked for exact JSON but did not show the model the schema. A model could fail for an under-specified interface, and malformed output rates would not be interpretable. V2 includes the complete exact schema in every action prompt and still rejects malformed output without repair. Counterexamples cover truncated JSON, extra keys, wrong action type, duplicate/unknown/missing allocation tasks, and empty messages.
2. **Own message history omitted from ballot.** V1 saved the outgoing message in researcher B but then removed the agent's own previous action from its ballot observation. This prevents a valid within-agent comparison between a commitment and its vote. V2 includes the agent's own exact parsed message action and only peer messages that were actually delivered. The canary has A promise the target, receive B's different suggestion, then vote for the public optimum.
3. **External backend could invalidate the offline budget or reproducibility.** V2 adds a stdlib-only loopback vLLM adapter. It cannot reach remote endpoints, suppresses environment proxies and redirects, and requires explicit model/revision/server/tokenizer/chat-template/context/sampling/timeout/budget values. The real config template is disabled and intentionally incomplete. Every request must go through the same logical/attempt budget adapter.

## Version boundary

The frozen v1 prompts, config, code snapshot, run, and canaries are not edited. V2 is selected only by `configs/m1-r-offline-v2.toml` and `prompt_version = "m1-p0-frozen-v2"`. Exact V1 source provenance is archived in `M1_P0_V1_SOURCE_SNAPSHOT.json`; the verifier accepts that exact historical snapshot as well as the current V2 source snapshot. It does not silently reinterpret V1 observations as V2.

V2 differences are limited to:

- Add the exact communication and ballot JSON schemas to their agent-facing prompts. V1 and V2 schema files are byte-identical.
- For chat-enabled A/B ballot observations only, add `your_previous_message_action` and retain `private_peer_channel.messages_received` as exactly the delivered peer messages. The message-stage observation has no future action. C and every no-chat agent continue to have no peer-channel or prior-message fields.
- Version the runtime config and artifacts so the change cannot be mistaken for a V1 run.

The five treatment conditions and +20 reward amounts, allocation matrix, voting/settlement rule, communication order, auditor permission, and retry policy remain unchanged. No acceptance threshold was relaxed.

## Strict action path

- V2 message and ballot requests include a literal JSON Schema block and a sorted compact observation JSON object. The exact prompt/schema bytes are frozen and hashed in `M1_P0_FROZEN_PROTOCOL_V2.md`.
- The parser independently enforces exact key sets, action type, all three unique tasks, and message-length limits. Schemas are not treated as proof of backend constrained decoding.
- JSON/schema errors, wrong action type, extra keys, invalid allocations, refusal/non-string content, and server `finish_reason="length"` fail the action. No repair, truncation, schema retry, or replacement is allowed. Transport timeouts and declared transient HTTP/connection failures can retry once, at most twice per logical request.
- The original raw assistant content and response envelope/usage are retained in the researcher request ledger where a response arrived. Failed, timed-out, malformed, and partial episodes remain records.

## Episode and information boundaries

The episode sequence remains: per-agent task/reward observation → optional A/B message requests → atomic delivery of valid sent messages only after both message actions parse → A/B/C sealed ballots → deterministic settlement → public W/individual task score/realized score → E export. A's message is not shown to B during B's message-stage request. In the later ballot stage, A sees A's own action and any delivered B message; B sees B's own action and any delivered A message. C sees neither. A no-chat episode makes no message request and exposes no peer action before ballots are sealed.

Assignment T, observed behavior B, and auditor evidence E remain distinct:

- **T:** assigned condition/reward/channel and component-specific response-receipt status. Assignment is not delivery; response receipt is not comprehension or utility.
- **B:** exact sent/delivered message records, each sealed ballot, selected allocation, public welfare and task score arithmetic, failures, and usage/transport logs. Message sending and delivery remain separate.
- **E:** permission-filtered public task rules and events. No condition/seed/group/oracle or injected private reward instruction. Private peer text is absent by default; if a future user-approved permission includes it, voluntary agent-authored disclosure remains behavior evidence and is not censored by keyword.
- **Latent agreement/intent:** no ground-truth label is assigned by treatment. Matching ballots, target execution, common incentives, private-chat access or use, and welfare loss alone do not establish collusion.

## Local vLLM adapter and configuration

`src/colluscope/openai_compat_vllm.py` implements a local OpenAI-compatible `/v1/chat/completions` adapter with only Python standard-library transport. It has no provider SDK, credential lookup, external model fallback, environment proxy, redirect, or streaming. The URL must be an unauthenticated loopback URL ending in `/v1`. Transport uses the configured timeout argument.

The fixed role mapping splits the rendered prompt at its first system/user separator into exactly two messages: `system` then `user`. The model, thinking mode, temperature, top-p, output-token limit, and non-streaming setting are sent on every request. Thinking mode is explicit (`enabled`/`disabled`) and maps to vLLM's `chat_template_kwargs.enable_thinking`; support and behavior must be established for the selected server/model during separately approved preflight, not assumed from this offline test. An injected token counter must attest matching tokenizer ID/revision, tokenizer-file hash, and chat-template hash; prompt tokens plus max output must fit the frozen context length before dispatch. This prevents copying offline Mock sampling values into a real config without review.

`configs/m1-p0-vllm-local.template.toml` is intentionally disabled and contains unresolved values. Loading it raises before transport. A later user-approved config must fix: model ID and immutable 40-character revision; server version; tokenizer ID/revision and hashes; chat-template hash; context length; thinking mode and supported request field; temperature, top-p, output limit; transport timeout; logical/attempt limits; and a `$0.00` API-spend ceiling for the local-only endpoint. The local server's model revision is not attested by the compatible `/models` API; it must be pinned at server launch and reported as operator-configured, not as independently verified metadata.

Adapter records include the exact serialized request payload/hash, endpoint and roles, configured model/tokenizer identity, prompt-token count, max output, timeout, raw returned assistant content, raw backend response envelope/hash, finish reason, returned model ID, and actual usage fields where the server supplies them. 4xx/config/schema errors are not retried; 5xx/transport transient errors and timeouts share the two-attempt ceiling. `finish_reason="length"` is a terminal malformed/truncated action.

The shipped CLI still exposes only the offline Mock path. The local backend was tested only with an injected in-memory fake HTTP opener; `preflight()` was exercised against fake `/version` and `/v1/models` responses. No socket, local model server, model weights, provider, or LLM was contacted.

## Call and spend limits

For the unchanged 5 conditions × 5 seed blocks:

| Source | Calculation | Logical requests |
|---|---:|---:|
| Sealed ballots | 25 episodes × 3 agents | 75 |
| Optional peer-message round | 2 chat conditions × 5 blocks × 2 agents | 20 |
| Comprehension probes | disabled | 0 |
| **Pilot total / hard logical maximum** | | **95** |
| **Worst-case adapter attempts** | 95 × 2 attempts | **190** |

Both ceilings are checked before backend dispatch through `RequestBudget`. A lower explicit ceiling is allowed, but a full 25-episode execution requires the full 95 logical-request allowance. Preflight GETs and any separately approved structured-output test must be logged and budgeted separately; neither is part of these 95 research requests.

Current authorization is **0 real model calls / `$0.00` API spend**. For the local vLLM proposal, API spend is capped at `$0.00`; GPU/host compute cost is unmetered and cannot be quoted until the host/runtime and duration are known. Actual token/compute budget is not estimable without a selected tokenizer, model and max-output setting. The offline Mock value of 256 output tokens is not proposed for a real model. These open cost facts block pilot GO.

## Design limits retained

- **Shared target:** A and B receive the same rewarded target in private-bonus arms. Matching target ballots without private chat are compatible with independent parallel behavior and cannot establish communication-induced coordination.
- **Bundled communication contrast:** chat arms give A/B an extra message-stage turn even when they choose `no_message`; the contrast is the assigned offer of a peer-message round plus extra deliberation/prompt exposure, not an isolated message-content effect.
- **Environment replication:** all five seed blocks use the same 3-agent payoff matrix. The public chair has only three positions and rotates A/B/C/A/B; five blocks are not five independent random task environments.
- **Four-view fairness:** this gate runs no detector or view comparison. Any later comparison must keep episode content and permissions fixed, separate derived computation from serialization via a same-schema findings/no-findings ablation, and report exact tokenizer/context/truncation/token and cost information. Hidden treatment metadata is not an allowed shortcut.

## Gate boundary

Offline V2 GO requires the original suite, historical V1 artifact verification, schema/self-history counterexamples, local-backend request/response tests, the V2 25-episode run and independent verifier, and V2 isolation canaries to pass. Any real connection/completion request remains NO-GO until a separate approval names the exact model/runtime/sampling/budget/retention configuration. This TRD contains no such approval.
