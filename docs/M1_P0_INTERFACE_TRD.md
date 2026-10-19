# ColluScope — M1-P0 Next Gate TRD

**Review date:** 2026-10-19 (Asia/Shanghai)  
**Remote branch:** `codex/m1-p0-local-qwen-integration`  
**Reviewed HEAD:** `657eab90356ce9137c2988aacb4b5b10d0402c28`  
**Scope:** Separate structured-interface validity from model action-choice compliance; preserve frozen evidence; prepare an explicitly approved new live gate.  
**Current decision:** Historical parser V2 trial is `NO-GO` for the 25-episode Pilot; **0 research episodes collected**. No live requests are authorized by this TRD.

## 1. Verified baseline and exact blocker

- Local Qwen3-8B Q4_K_M GGUF loads under pinned llama.cpp, using the approved loopback port 8081. Model/server identity and one tested prompt's chat-template/tokenizer parity have been checked in saved records.
- Initial strict JSON-only preflight failed because a real completion began with an empty `<think>\n\n</think>\n\n` wrapper. A *new*, narrowly frozen parser accepts exactly that prefix; archival strict-parser artifacts remain unchanged.
- Parser V2 trial recorded two real completions: valid ballot JSON and valid `{"type":"no_message"}`, both with the exact observed empty wrapper.
- The second probe also carried `preflight_probe_instruction` requesting `send_message`, but the model returned `no_message`; the code at `src/colluscope/openai_compat_llamacpp.py` requires `actual == expected_type` and consequently stopped. This is an **action-choice/compliance mismatch**, not a JSON-schema violation.
- The original run was not retried to obtain a preferred response. Latest logs state 159 passed, 1 skipped and **0/25 assigned episodes**. The present review independently inspected repository files/logs, not a fresh run on the user's GPU.

## 2. Research question for this milestone

Can the runtime accept and faithfully record *every valid communication action* while preserving the ability to report an explicit action-compliance mismatch separately? Can it then support a new, preregistered, bounded live experiment without selecting favorable samples?

### Scope exclusions

No detector comparison, no reward/prompt manipulation in the research treatment, no alteration to M0/M0.1/M1-R archives, no hidden retry, no extra model download, and no new model call absent user approval.

## 3. Requirements

### R1. Split two orthogonal gates

**Schema/transport gate (hard):** valid JSON after the exact approved empty prefix, valid action variant, exact field and type constraints, no extraneous text. In a *message-stage* request, both `send_message` and `no_message` are acceptable outputs. Invalid JSON, nonempty or altered thinking wrappers, schema violations, truncated completions, unsupported schema errors, and server/model mismatches remain hard failures.

**Instruction-compliance diagnostic (descriptive):** if a probe deliberately requests a particular action, record `requested_action`, `actual_action`, `followed_instruction`, and the complete raw response. Do not convert a schema-valid alternative into a model-incompatibility claim. Do not count this diagnostic as an in-game behavior sample or quietly retune prompts after viewing it. Define in advance whether this check is advisory or blocking for a separately specified capability question. 

A missing live `send_message` demonstration means **positive message generation remains unverified**, not that the `oneOf` schema is unsupported. Do not assert end-to-end *positive-message generation* is validated merely from a valid `no_message`.

### R2. Positive-branch plumbing without cherry-picking

- Exercise `send_message` through deterministic Mock / fake transport and verify parsing, A→B delivery, self-history, isolation from C, T/B/E export, and verifier semantics. This is **software-path validation**, not evidence the model elects to send messages.
- Inspect the pinned llama.cpp supported JSON Schema subset and retained live response; compare actual server contract to the frozen `oneOf` schema. Do not claim full grammar enforcement just because HTTP 200 or two valid responses were observed.
- Optional real-model compliance probes require a **new user-approved budget and new protocol ID**, with fixed prompt, sampling, sequence, expected response and failure handling. Any observed compliant and noncompliant responses are retained. Never loop until `send_message` appears.

### R3. Fix phase language and versioning

- Create a new preregistered protocol version (e.g. `m1-p0-interface-v3`) rather than altering the parser-V2 freeze.
- Keep `strict_parser_v1` and `json_prefix_v2` historical verdicts and exact raw bytes immutable.
- Describe `no_message` as a protocol-valid action; describe disobeying an explicit engineering instruction as an instruction-following observation, not necessarily a protocol violation.
- Document whether the research prompt is unchanged. If engineering-probe wording changes, keep those probes separate from experiment prompts.

### R4. Reproducibility and client safety

- Verify checkpoint SHA256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`, server executable/bundle identity, tokenizer/chat-template identities, 127.0.0.1:8081 owner, no proxies/redirects, fixed output limits, and non-thinking setting. Record the returned empty wrapper instead of pretending it does not exist.
- Existing episode pipeline retains shared budgets 95 logical / 190 attempts maximum, no retries of malformed actions, and all failure rows. Do not conflate metadata HTTP checks with generation calls.
- Validate historical run packages, including `PASS_PACKAGE_INTEGRITY__NO_GO_ACTION_MISMATCH`, **without changing their decisions**.
- A new explicit approval is required before server launch or further model completion; authorizing this TRD alone does not grant it.

### R5. Behavioral pilot gate, only after approval

The previously planned five conditions × five seed blocks may proceed *only under an approved immutable protocol and model/runtime budget*. Run the entire assigned batch; if an episode fails, retain the incomplete record. Do not stop, restart, or vary bonuses because observed actions are unhelpful. A preflight probe is never a research episode. Report all five arm-level denominators, validity/parse failures, sent/delivered messages, ballots, target outcomes, W and realized scores. Report action-choice and welfare-loss variables separately from hidden treatment and latent intent.

## 4. Tests / falsification criteria

1. **Valid non-preferred action:** engineering prompt requests `send_message`; model/test double returns valid `no_message`; schema gate PASS, compliance diagnostic `false`, raw response retained.
2. **Valid preferred action:** valid `send_message` passes schema and plumbing tests; peer delivery verifiably A/B-only.
3. **Bad action:** malformed JSON, malformed wrapper, trailing bytes or truncated content fails hard, without retry/repair.
4. **Invalid server contract:** simulated unsupported `oneOf`, schema ignoring, wrong model ID, wrong tokenizer/template or context overflow fails explicitly.
5. **Historical evidence:** all previous manifests and source snapshots unchanged; previous failed run still reports NO-GO.
6. **No hidden data:** no condition ID, seed block, hidden incentive, oracle field, or research manifest enters model or monitor inputs except intentionally public task rules.
7. **Independent audit:** sample output and full launch/ledger/source hashes verify under a new clean checkout; a tamper test fails even after the file hash is recomputed when a semantic invariant is broken.

## 5. M1-P0 behavior analysis plan (no monitor yet)

- For each arm: assigned N=5, attempted/completed/invalid counts, private messages sent/delivered, target ballots, chosen allocation, welfare gap and task-score distribution.
- Contrast `coalition_incentive_private_chat` vs `coalition_incentive_no_private_chat` only as **offer of an extra peer-message turn** under shared A/B target bonus, not isolated message-content causality.
- Public bonus induces parallel choice without peer channel; it is not a collusion negative label by itself. Welfare loss also does not alone prove collusion.
- Repeated seed blocks share one payoff matrix and a small chair schedule. Do not report nominal 25 episodes as 25 independent task environments.
- If there are no or too few executed harmful/coordination-relevant trajectories, do not fabricate positive labels or tune reward strength after seeing outcomes; apply the research pivot specified in the persistent Goal.

## 6. Decision gates and deliverables

**Engineering GO:** new offline tests, revised schema/compliance separation, preserved old failures, clean verified build, exact prompt/source/hash manifest.  
**Live preflight GO:** only after a new explicit approval of server/runtime, local data retention, 6 logical / 12 HTTP / at most 4 model-completion engineering preflight requests. This must be a **new** ledger, not a reuse of consumed approval IDs.  
**Behavior Pilot GO:** only after the new live preflight and separately approved 95/190 research budget; no M2 automatic transition.

Required files:

- `docs/M1_P0_INTERFACE_TRD.md`
- `docs/M1_P0_INTERFACE_EVIDENCE.md`
- `docs/M1_P0_INTERFACE_DECISION.md`
- `docs/M1_P0_PRE_REGISTERED_PROTOCOL_V3.md`
- `docs/RESEARCH_RISK_REGISTER.md` update and `docs/ITERATION_LOG.md` entry
- Offline counterexample tests, historical verifiers, and raw manifests
- Pushed topic commit SHA, branch, and exact replay instructions

**Stop:** report the new gate result and any unresolved action-choice ambiguity; do not treat completion of implementation as permission to run the research batch.
