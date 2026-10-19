# M1-P0 Local Integration Decision

## Decision

**GO for offline runtime and adapter review. NO-GO for live engineering preflight, M1-P0 research episodes, and M2 detector comparison.**

No model call was made. The full 25-episode Mock run is infrastructure evidence only and explicitly sets `behavioral_evidence_claimed=false`.

## Gate-by-gate result

| Gate | Decision | Evidence |
|---|---|---|
| Local artifact path and integrity | **GO for inventory** | Qwen3-8B Q4_K_M GGUF at `E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf`, 5,027,783,488 bytes, SHA256 recorded and matched to local download metadata. |
| Hardware and runtime inventory | **GO for inventory / NO-GO for compatibility claim** | RTX 4090 Laptop GPU (16 GB class) and installed versions are recorded. WSL can see the GPU, but has no vLLM, CUDA compiler or PyTorch. The installed llama.cpp build was not started. |
| API action-schema delivery | **GO for client contract** | The actual adapter posts the exact communication and ballot schemas using `response_format.json_schema`; local HTTP canary confirms request bytes, hashes and explicit unsupported-`oneOf` handling. Real server acceptance/enforcement is UNKNOWN. |
| Self-message continuity / agent isolation | **GO for offline plumbing** | V2 Mock canaries verify the A/B prior-action and delivered-peer-message fields, C/no-chat exclusion, no pre-vote ballot exposure and separate T/B/E paths. |
| Call, retry and token budgets | **GO for offline enforcement** | 95 logical / 190 maximum behavior attempts are enforced; 2 attempts per request; 6 logical / 12 attempt preflight budget defaults disabled and is hard-capped; 0 comprehension probes. Stage output caps are separate, and context overflow fails before HTTP dispatch. |
| Historical evidence | **GO** | Full suite verifies prior V1 and accepted V2 packages without changing manifest bytes. Prior integration docs/protocol are preserved with byte-identical hashes under `M1_P0_GATE_*`. |
| Real model compatibility | **NO-GO** | Current file is GGUF, not the initial AWQ proposal. The matching Qwen3-8B base tokenizer/revision/hash is absent, vLLM is not installed in WSL, and the exact model-specific chat-template/tokenizer count has not been tested. |
| Research outcome interpretation | **NO-GO for behavioral claims** | No LLM agent ran. Shared-target agreement in no-chat arms remains compatible with independent parallel choice. Channel availability, private-message use, shared incentive, target execution and welfare loss are not individually treated as collusion labels. |

## Why live preflight is blocked

The local HTTP server is a test double; it proves the request construction and client failure policy, not that vLLM 0.32.0 or the installed llama.cpp build loads this model, implements the requested `oneOf` schema, honors Qwen3 non-thinking mode, or reports matching tokenizer usage. The official vLLM guide describes GGUF support as experimental and recommends the base tokenizer. That tokenizer is not currently cached under the user's model root. The installed llama.cpp server has a different structured-output request shape and has not been exercised.

These are observable integration gaps, not failed model behavior. There is no valid basis to report a live compatibility PASS or an agent behavior result.

## Next review decision

Before any live request, choose one exact local runtime path:

1. Approve the existing Q4_K_M GGUF and nominate a compatible local server/tokenizer pair; or
2. Separately authorize a different local checkpoint/runtime after its exact files are present under the approved model root.

Then freeze exact model and tokenizer revisions/hashes, server build, chat template, tokenizer counter, launch/memory settings, and the preflight request allowance. The configured preflight ceiling is at most 6 logical / 12 attempts and remains disabled. A preflight is only a compatibility check; it does not authorize the 25-episode behavior pilot.

Do not proceed automatically to M1-P0/P1 or M2. Stop here for user review.
