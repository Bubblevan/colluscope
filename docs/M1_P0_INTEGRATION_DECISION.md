# ColluScope M1-P0 Integration Gate Decision

**Decision:** **GO for review of the offline V2 integration package. NO-GO for P0-IV live preflight and NO-GO for the 25-episode real-LLM behavior Pilot.**
**Accepted source baseline:** `5786852f8280af94256c2f9a16f7e872ffdd9146`.

## Gate decisions

| Gate | Decision | Evidence and limitation |
|---|---|---|
| V1 preservation | **GO** | Original V1 prompt/config and M0/M0.1/M1-R runs remain unchanged. Historical V1 run and canary reverify against the authenticated archived V1 source snapshot; manifest bytes were checked before and after. |
| Full action schema in agent prompt | **GO for V2 prompt path** | Exact communication/ballot schemas are in every respective V2 action prompt; prompt/schema byte hashes are frozen. Strict parser counterexamples reject truncated JSON, extra keys, wrong type, malformed allocation and invalid message. No real model adherence test was run. |
| Self-message continuity | **GO for offline runtime plumbing** | Chat A/B ballot observations contain the exact agent's own prior action and only delivered peer messages. C/no-chat isolation remains. A semantic verifier catches removal even if the modified observation/file hashes are recomputed. Injected promise/suggestion/contrary-vote case retained. |
| Local vLLM adapter | **GO for fake-transport software integration only** | Exact role mapping, request, timeout, output cap, response usage/raw body, retry, truncation and budget semantics tested with an injected fake opener. Remote endpoints/proxies/redirects are excluded. No model weights/server/LLM contacted; vLLM protocol compatibility with an actual chosen version is UNKNOWN. |
| Original regression and adversarial controls | **GO offline** | Final full repository suite after thinking-mode configuration: 88 passed. V2 25-episode Mock run: 25/25, all condition counts 5, 95 calls / 95 attempts, independent settlement/E/hash verification. V2 canaries: 11 traces / 18 assertions, all pass. Failures remain in logs. |
| T/B/E and inference scope | **GO as protocol; latent intent UNKNOWN** | T assignment, B actions/outcomes, and E permission projection remain separate. No condition, incentive, message, matching ballot, target action or welfare loss is itself collusion ground truth. |
| Request budget | **GO for hard call-count enforcement** | 95 logical requests and maximum 190 attempts are reserved before backend dispatch. Fake transport confirms a second request is rejected at its budget boundary. Preflight/structured probes require a separately approved side budget. |
| Monetary/token budget | **NO-GO for experiment approval** | Local endpoint API cap is set at $0.00; model/tokenizer/max-output/hardware are not selected, so exact token and GPU/host compute cost is unknown. No cost was incurred. |
| P0-IV real backend preflight | **NOT RUN / NO-GO pending approval** | User authorization requires exact model, endpoint, sampling and call budget first. No actual endpoint was configured or contacted. Fake preflight test is not a preflight result. |
| Full 25-episode real-LLM pilot | **NO-GO** | Requires separate approval of immutable model/revision, exact vLLM/server version, tokenizer/chat-template hashes/context, thinking mode and supported request field, sampling/output/timeout, 95/190 limit, compute/spend ceiling, retention/auditor permission, and preflight results. No automatic batch follows this decision. |
| M2 or detector comparison | **NO-GO** | No monitor, four-view comparison, detector metric, tokenizer cost comparison, threshold tuning, or formal evaluation ran. |

## Research limitations that remain

1. A/B share a rewarded target. Agreement on that target without chat cannot establish communication-induced coordination; parallel action is a live negative explanation.
2. Chat arms get an extra message-stage turn even for `no_message`. The contrast is the bundled peer-message-turn opportunity plus deliberation exposure, not a pure message-content causal effect.
3. The five blocks use one payoff matrix and only three public chair positions (A/B/C/A/B). They are not five independent random task environments and do not support generalization.
4. Prompt-stated task rewards may not be comprehended or function as actual model utility. Receipt is not comprehension. Any failure to elicit harmful action must remain a result, not trigger post-hoc reward tuning.
5. The V2 Mock still makes no behavioral claim. It always demonstrates software responses, not real-agent cooperation, collusion or harm.

## The single next valuable action

Review this package and, only if the frozen design is acceptable, separately authorize a model-specific P0-IV request specifying the exact local model/revision, vLLM version, tokenizer/chat template/context, supported thinking mode/field, sampling/output limit, timeout, preflight request allowance, pilot 95/190 ceiling, maximum local compute/spend, retention, and private-message auditor permission. Until that is received, stop here.
