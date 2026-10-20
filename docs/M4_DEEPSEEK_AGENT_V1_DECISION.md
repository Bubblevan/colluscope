# M4 DeepSeek Agent V1 — Final Decision

**Status:** `COMPLETE_INDEPENDENT_REPLAY_PASS`. This is one prospective run of the frozen DeepSeek interface, not a replacement or rewrite of the historical Qwen/llama.cpp run.

## Verified execution

- 24 assigned groups; 24 completed and independently replayed; 0 failed or unstarted.
- 232 physical Agent generation requests; 0 retries; 0 replacement groups.
- Strict Function Calling was selected by the 20-request compatibility pilot. The formal run used the same single interface.
- All 48 messages were sent and delivered. All 72 baseline ballots passed action validation and settlement replay.
- Independent audit status: `PASS_INDEPENDENT_AGENT_REPLAY`; audit summary SHA-256 `9fd50cb250cc3867b26ad45b14c035a3f1fb3652fe36defa061b69b5a44031e0`.

## Scientific interpretation

The common rewarded target received 13/72 baseline ballots and was executed in 2/24 groups. This is compatible with multiple explanations: independent response to a shared incentive, task/matrix variation, and communication. The design does not isolate a causal effect of communication on natural ballots.

Twenty messages contained complete allocation proposals. Eleven exactly matched the recipient's baseline ballot. This temporal concurrence does not itself establish acceptance, agreement, intent, or communication causation. In the focal counterfactual prompts, Proposal and Neutral differed by 32–85 provider-reported input tokens; observed ballot-change contrasts are confounded by prompt length/salience and are not a clean semantic-content estimate.

**GO:** integrity and descriptive analysis for this 24-group run.
**NO-GO:** causal communication, latent-collusion, or generalization claims.
**STOP:** no additional Agent inference is authorized by the consumed one-run approval.

See `docs/M4_DEEPSEEK_AGENT_V1_EVIDENCE.md` and `docs/results/deepseek-first-m4/audit/` for replay and sanitized rows.
