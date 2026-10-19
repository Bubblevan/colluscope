# M1-P0 Local Integration TRD

**Scope:** M1-R runtime adapter and offline canary integration only. This document does not authorize model calls, live preflight, research episodes, or M2 detector work.

## Research and engineering target

Prepare the smallest reproducible local inference path that could later test whether assigned incentives and peer-message opportunities change allocation behavior. The evidence target is valid behavior per model call. Infrastructure outputs, Mock actions, agreement, shared rewards, and welfare loss are not collusion labels.

## Highest validity risk

The machine contains a Qwen3-8B Q4_K_M GGUF file, while the initial preferred proposal called for Qwen3-8B AWQ served by vLLM. The matching tokenizer files and a tested WSL inference stack are absent. A passing offline HTTP contract can only show what this client sends and how it handles failures; it cannot establish that a real server accepts or enforces the communication `oneOf` schema, loads this checkpoint, or uses the expected chat template.

## Candidate protocol and implementation

- Preserve `m1-p0-frozen-v2` prompts and the five frozen pilot conditions.
- Include the exact stage schema in the rendered prompt and send it in `response_format.json_schema`.
- Use separate 512-token message and 256-token ballot output caps; reject prompts above the 3,072-token input cap or 4,096-token context rather than trimming them.
- Send a stable matched-block generation seed. For each `seed_block`, agent and action stage, derive 31 bits from SHA256 over `colluscope-m1-p0-seed-v1\0{seed_block}\0{agent_id}\0{action_kind}`. The seed is transport metadata, absent from prompt text and E, and independently recomputed by the run verifier.
- Keep the existing strict parser. Malformed, schema-invalid, truncated, or refused outputs are terminal and retained. Only timeouts and transient transport errors receive one retry; both attempts count against the hard ceiling.
- Keep all real calls default-denied. The local vLLM adapter permits only a loopback endpoint, disables proxies and redirects, sends no authorization header, and shares the request/attempt budget.

## Frozen call graph

Five conditions × five seed blocks produce 25 episodes. Three no-chat arms each use three ballot requests per episode: 15 × 3 = 45. Two message-opportunity arms each use two A/B message turns plus three ballots: 10 × 5 = 50. Total: 75 ballots + 20 message turns = **95 logical requests**, with at most two physical attempts each = **190 attempts**. Comprehension probes are disabled. Timeouts and malformed outputs do not remove episodes from the record.

A separate engineering preflight is disabled and capped at six logical requests / twelve attempts. The current preflight implementation makes two GET requests (`/version`, `/v1/models`) and has no automatic retry. Preflight results would establish endpoint metadata only, not a research outcome or immutable checkpoint revision.

## Falsifiers and offline checks

The offline canaries use the actual `urllib` client against a loopback HTTP service. They check successful request bodies and hashes, communication `oneOf` transport, explicit unsupported-schema error retention, malformed output without repair, timeout retries, connection refusal, duplicate IDs, and global retry-budget enforcement. A separate tamper test changes a recorded matched seed and recomputes the file hash; independent verification must reject it. Historical V1/V2 verification compares manifest bytes before and after.

These checks establish client-side request construction, recording, accounting, and rejection behavior. They do not establish actual server-side schema enforcement, model loading, tokenizer agreement, model comprehension, or behavior.

## Runtime and model boundary

The inventory in [M1_P0_LOCAL_ENVIRONMENT.md](M1_P0_LOCAL_ENVIRONMENT.md) records the actual file under `E:\Health-Copilot-Models\models`, GPU, Windows/WSL runtimes, and installed server. The local draft config is intentionally denied by the loader. No checkpoint or package was downloaded, upgraded, or served.

The official vLLM API documents `response_format.type=json_schema`; the installed Windows llama.cpp server is a different backend contract and has not been integration-tested here. The official vLLM GGUF guide describes GGUF support as experimental and recommends the base-model tokenizer; the exact Qwen3-8B tokenizer revision and hash are not present locally. See [vLLM structured outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/), [vLLM GGUF guide](https://docs.vllm.ai/en/v0.18.1/features/quantization/gguf/), [Qwen Q4_K_M model card](https://huggingface.co/Qwen/Qwen3-8B-GGUF), and [llama.cpp server contract](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

## Stop condition

Stop at offline integration. A separate user review must resolve the local GGUF/tokenizer/server choice and authorize a concrete preflight budget before any live request. No model call, model server, research episode, or detector evaluation is part of this milestone.
