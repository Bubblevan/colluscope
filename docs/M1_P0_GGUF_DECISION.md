# M1-P0 GGUF Runtime Decision

**Decision:** **GO for offline implementation review and the bounded local preflight only after resolving the port conflict. Preflight is user-authorized but BLOCKED before launch. NO-GO for the full M1-P0/P1 research pilot and M2.**

## GO: offline integration package

Evidence supports review of a local llama.cpp adapter candidate:

- The user-provided GGUF checkpoint path, size, and SHA256 were verified. The model choice is fixed as Qwen3-8B Q4_K_M GGUF.
- Static tokenizer/template extraction and candidate rendering work locally without loading model weights.
- The adapter uses the pinned llama.cpp request shape, strict response checks, loopback-only transport, no proxy, no redirect, no model fallback, recorded request/response/error data, bounded retry, and independently enforced 95-logical/190-attempt caps.
- Fake HTTP adversarial tests cover schema rejection without fallback, timeouts, 5xx retry, invalid output, alias/usage/token drift, reasoning leakage, endpoint restrictions, runtime DLL drift, and hard call ceilings.
- The offline M0/M1-R artifacts independently verify. M1-R's scripted Mock behavior is explicitly not behavioral evidence.

Exact commands and retained output are in [`M1_P0_GGUF_COMPATIBILITY_EVIDENCE.md`](M1_P0_GGUF_COMPATIBILITY_EVIDENCE.md).

## NO-GO: live compatibility and research calls

The user's 2026-10-19 request authorizes only the frozen six-logical-request compatibility preflight (at most 12 HTTP attempts and four generation attempts), with local retention and no paid API. The checked-in config remains default-denied pending a separate run-scoped approval record. This preflight has not started: frozen port 8080 is already bound by PID 12152 (`ApplicationWebServer.exe`), associated with service `NIApplicationWebServer`, on `0.0.0.0`; its executable path and command line are unavailable. No request was sent and that service was not stopped. There is still no empirical compatibility evidence that this exact server/model combination accepts the V2 `oneOf` schemas, renders the embedded template identically, produces matching token IDs, honors the no-reasoning settings, or fits the observed GPU. The official API docs and fake server are not substitutes for that evidence.

The preflight is specified as six logical requests, at most 12 HTTP attempts and four generation attempts. It must stop on the first mismatch. Approval of this preflight does not authorize the 25-episode pilot. Pilot authorization would separately need the exact model/runtime/tokenizer/sampling/context and a call/retention/auditor budget. No pilot or M2 work follows automatically.

The current blocked attempt is recorded in `runs/m1_p0_local/gguf-preflight-iteration-02/`. Resolve the listener conflict without disrupting the NIApplicationWebServer service, then freeze the exact endpoint for this preflight before retrying.

## Research validity limitations preserved

- A and B share the same rewarded target, so their independent agreement in the no-chat private-bonus arm is compatible with parallel independent choice.
- A/B chat conditions include an extra pre-ballot request even when the action is `no_message`; the contrast estimates a bundled communication-turn opportunity, not the effect of message content in isolation.
- A task-score rule or public bonus is visible evidence about the task. It does not reveal private treatment assignment and does not itself establish collusion.
- The runtime cannot infer intent, mental agreement, comprehension, or model utility from an action. Intervention labels and actual-action labels must remain separate.

## Stop condition

Stop at M1-R plus offline llama.cpp compatibility implementation. Await human review of the frozen candidate protocol and this decision. Do not start M1-P0 live preflight, a real-agent pilot, or M2 without a separate explicit approval.
