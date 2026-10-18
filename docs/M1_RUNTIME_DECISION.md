# ColluScope M1-R Decision

**Date:** 2026-10-19 (Asia/Shanghai)
**Decision:** **GO for human review of the M1-P0 protocol only. NO-GO for real M1-P0/P1 execution or M2.**
**Topic branch:** `codex/m1-r-runtime`; M1-R implementation commit: `e46523cf1f2e9442eaaa7d890691db66506391ec`. The pushed branch also contains the final evidence-package update.

## Gate-by-gate decision

| Gate | Decision | Evidence and boundary |
|---|---|---|
| Independent M0.1 baseline on M1-R checkout | **GO** | Python 3.12.4 / pytest 9.1.1: 50 passed before runtime edits. Frozen M0/M0.1 reports, config, and run directories have no M1-R changes. |
| No-chat isolation | **GO for Mock plumbing** | No-chat traces contain ballot requests only; every request has a fresh explicit observation; no output is forwarded; A/B private messages are delivered only after both turns and only to the named peer; C never receives message or private bonus text. An external provider's hidden session/cache semantics remain untested. |
| Reward assignment vs delivery | **GO for explicit offline receipt accounting; real delivery remains unverified** | T distinguishes assigned components, response-returned request IDs, budget-not-sent, and timeout-unknown. Response receipt does not prove model comprehension or utility. The selected external runtime is not approved/implemented. |
| Strict action parsing and failure retention | **GO** | Invalid/malformed/duplicate ballots fail as `invalid_output`, are not repaired/retried, retain raw output/request ID in B and ledger, and produce no settlement. Persistent timeouts retain both attempts and uncertain delivery. |
| Deterministic ballot settlement and score arithmetic | **GO** | Independent verifier recomputes all 25 ballot outcomes, public W/gap, public/private bonus awards, realized task scores, E projection and per-agent request links. Synthetic target arithmetic confirms W=14 while private target scores are A/B=34 and C=14; it is explicitly not model behavior. |
| Hidden treatment/oracle data excluded from monitor evidence | **GO for runtime schema** | E has only public task rules/events, no condition/seed/group/oracle/private-instruction fields. A tampered E row with an injected condition field is rejected by the verifier. Publicly announced bonus rules remain as legitimate task evidence. |
| Per-episode call graph and hard cap | **GO** | 75 ballots + 20 optional message turns + 0 probes = 95 logical calls. Adapter hard limits: 95 logical and 190 total attempts, max two attempts/request. Verifier links every call to the correct episode, action, and agent. |
| Offline adversarial canary | **GO** | Ten retained counterexample traces exercise 15 assertions; all pass. Exact logs and artifact hashes are in `M1_RUNTIME_EVIDENCE.md`. |
| Real model/tokenizer/cost selection | **NO-GO** | Model/version, local/provider runtime, role mapping, tokenizer/context, real sampling values, monetary ceiling, and retention choice have not been selected or approved. No real call was made. |
| Formal monitor/four-view evaluation or M2 | **NO-GO** | M1-R exports E only. No monitor, detector score, token cost, accuracy, FPR, or view comparison was run. |

## Validity limits that remain

1. **Shared target:** A and B each see the same rewarded allocation. Matching target ballots can be independent parallel behavior in the no-chat arm; matching is not proof of agreement or communication.
2. **Extra message turn:** Chat arms add one pre-ballot request per A/B even if they choose no message. The five-condition contrast is the effect of offering a peer-message turn bundled with extra deliberation/prompt exposure. It cannot isolate received message content from the extra turn.
3. **Prompt-stated reward:** A returned response establishes only that the adapter returned a response to an observation; it does not prove reward-rule comprehension or genuine model utility.
4. **Deadline enforcement:** Offline tests verify that the adapter passes the configured timeout and preserves timeout errors. A real backend must enforce a wall-clock deadline and count any duplicate/transport attempt against the same hard cap.
5. **Small toy design:** Five seed blocks and a single 3-agent/3-task payoff matrix are feasibility-only. The public chair map is A/B/C/A/B, not perfectly balanced. Do not make general LLM or real-world collusion claims.
6. **Four-view costs:** No monitor/tokenizer is selected, so token/cost fairness is specified but not measured. No detector comparison is authorized.

The default Mock produces 25 public-optimal W=28 assignments and no messages because it is a fixed test policy. It says nothing about whether an LLM would behave similarly. The target-result arithmetic is a separate synthetic assertion only.

## Recommendation for a later real-model approval

Do not tune reward values, prompts, labels, or acceptance thresholds after seeing outcomes. If reviewing an execution request, freeze one model/version, runtime and role mapping, tokenizer/context ceiling, all sampling parameters, private-message auditor permission, retention policy, 95 logical calls / 190 maximum attempts, timeout behavior, and a monetary ceiling before any call. Keep comprehension probes disabled unless a new protocol and budget are reviewed; a probe can prime ballots. Run the complete five-condition × five-block batch with all failures retained, rather than stopping/selecting arms after outcomes are visible. Describe the primary contrast as the assigned peer-message-turn opportunity, not communication content alone.

Until that separate approval, stop at M1-R. Do not invoke any LLM, do not launch M1-P0/P1, and do not begin M2.
