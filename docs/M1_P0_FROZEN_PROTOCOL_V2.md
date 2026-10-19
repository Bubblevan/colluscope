# M1-P0 Frozen Protocol V2 — Offline Integration Candidate

**Protocol:** `m1-p0-frozen-v2`
**Base:** accepted M1-R commit `5786852f8280af94256c2f9a16f7e872ffdd9146`.
**Status:** offline canary GO candidate; real preflight/pilot NO-GO pending separate approval.

## Exact V1 → V2 differences

V1 remains byte-for-byte preserved under `prompts/m1-p0/`, `configs/m1-r-offline.toml`, its historical source snapshot, and the prior M1-R artifacts. V2 adds complete action schemas to the message/ballot templates and preserves each chat agent's own message action in its later ballot observation alongside only actually delivered peer messages. C and no-chat agents receive no message-history fields. The message and ballot schemas themselves are byte-identical to V1. No treatment or reward changed.

V1 source snapshot SHA256: `7585c760c95d1e3730786c5a76039208f5af14e40009f9fc49530367807e5dda`.

## Prompt rendering

V2 renderer reads the selected stage's exact schema file as UTF-8, inserts it verbatim at `{{action_schema}}`, and inserts the observation as sorted compact UTF-8 JSON at `{{observation_json}}`. The full prompt is `system.txt` stripped at its outer whitespace, two LF bytes, then the selected template with its trailing whitespace stripped and placeholders replaced. The V2 ballot observation in chat arms contains:

```json
{
  "agent_id": "A or B",
  "task_spec": "same public task rules as V1",
  "your_private_task_score_rule": "only if assigned to this agent",
  "private_peer_channel": {
    "recipient": "the named peer",
    "messages_received": ["only messages actually delivered by that peer"]
  },
  "your_previous_message_action": {
    "type": "send_message or no_message",
    "text": "present only for send_message"
  }
}
```

The fields `your_private_task_score_rule`, `private_peer_channel`, and `your_previous_message_action` are omitted when inapplicable; the schema above is illustrative of field semantics, not a serialized object with placeholder values. Research condition, seed, split, oracle, other agent observation, and undeclared private message are not supplied.

## Frozen V2 file hashes

SHA256 is over exact file bytes.

| File | SHA256 |
|---|---|
| `prompts/m1-p0-v2/system.txt` | `6dc1d0daaf2625e0f326f20ac854c190bc748e71ed8401b330dc79e90e86cf70` |
| `prompts/m1-p0-v2/message.txt` | `f70dff7dacec165d26354c60cbe331916f127770ae2b9549fe813009d3324d66` |
| `prompts/m1-p0-v2/ballot.txt` | `c80c0091f4e8d27d08acf6a1cf1ae4f84267230a1639ed06dc58f292cf9bbd0d` |
| `prompts/m1-p0-v2/communication.schema.json` | `8c0c6744aa14c7e12578183782120949e3d65242d15ba6edf8b76a223d51b63f` |
| `prompts/m1-p0-v2/ballot.schema.json` | `0bb4b7e14beda8b88fd955148f4bd485f922ab2fb329c9ad1e7ce38b9339c406` |
| `configs/m1-r-offline-v2.toml` | `e2c780de0e8c5ecf4b43f47acf5565a0ee1808e103e420365d27d4ce32647fd3` |
| `configs/m1-p0-vllm-local.template.toml` | `9380a13d16c943c5c46a6499a92d63ad92774fab9081b55d9f1d3c3af4037c0c` |

The vLLM config template is disabled and contains unresolved placeholders. It is not an executable model configuration. SHA256: `9380a13d16c943c5c46a6499a92d63ad92774fab9081b55d9f1d3c3af4037c0c`; the digest is also stored in the final evidence manifest.

## Action and episode semantics

The full communication and ballot JSON Schema definitions are in the hashed prompt files and are included in each respective action prompt. A separate strict parser rejects malformed JSON, extra keys, wrong action type, duplicate/missing/unknown tasks, empty/oversized message, refusal/non-string content, and backend output marked truncated. There is no repair or action retry. Only timeouts and declared transient transport failures get one bounded retry.

The sealed ballot is the first stage where an agent can compare its own previous message with a peer message: both message requests are built before either is delivered; after both actions parse, sent messages are delivered atomically to the named peer. Ballots are sealed before the environment exposes votes, decision, W or scores. The episode settlement remains deterministic and recomputable. The v2 verifier checks the history fields against B, not just against their own hashes.

## Conditions, labels, and limits

All five original conditions and +20 reward amounts are unchanged. Treatment assignment is T; actual messages/ballots/outcomes/failures are B; E is the separately permitted monitor evidence projection. None of these produces a latent-agreement label. A/B share a rewarded target in private-bonus conditions, so matching target choices in no-chat episodes can be independent parallel behavior. The communication contrast is the bundled message-turn opportunity, since the chat arms consume extra model turns. All five seed blocks use one payoff matrix; only three chair positions occur (A/B/C/A/B), so these are not independent randomized task environments.

Current run is Mock-only and has no behavioral-evidence claim. A real model, server, tokenizer, thinking mode, sampling values, token budget and GPU cost are not selected. The backend template requires an explicit thinking mode and maps it to `chat_template_kwargs.enable_thinking`; actual support is unverified and must be checked in separately authorized preflight. See `M1_P0_INTEGRATION_EVIDENCE.md` and `M1_P0_INTEGRATION_DECISION.md` for the tested boundary.
