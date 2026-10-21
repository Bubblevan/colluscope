# Research Risk Register Follow-up — Model Scope Declined

**Date:** 2026-10-21

**Model calls:** 0

| ID | Risk / counterexample | Evidence and status | Required interpretation / next action |
|---|---|---|---|
| RV-253 | Model substitution could silently turn the declined Qwen-specific protocol into a DeepSeek experiment while retaining the same preregistration or claim. | The user explicitly declined Qwen. R3 is still only an unregistered review snapshot and names Qwen3-8B; its manifest pins the hypothesis registry and runtime. The existing DeepSeek approvals name closed experiments. No new request was sent. | Preserve R3 as history, mark its execution path withdrawn, and create a new versioned candidate for any different model. Require a fresh exact-scope decision and model-specific tokenizer, prompt, runtime, cost, privacy, and failure analysis before registration or dispatch. |
| RV-254 | The declined run could be presented as scientific evidence or the refusal treated as a positive/negative experiment outcome. | No M1 response was generated under this proposed R3 scope. The refusal is solely an authorization boundary. | Keep the M1 package hypothesis and prior observations separate from this decision. Do not update scientific effect estimates from it. |
| RV-255 | A commit-first instruction could be misread as authorization to make calls immediately after pushing. | User directed that if calls are necessary, the offline stage should be pushed and an interim status reported first. No new experiment scope, call ceiling, or cost ceiling was granted for a replacement run. | Push the offline stage and stop for a fresh exact-scope decision before any new model/API request. |
| RV-256 | Updating canonical audit logs after a campaign closes can invalidate its registry-integrity record. | A temporary append to `docs/ITERATION_LOG.md` and `docs/RESEARCH_RISK_REGISTER.md` produced an audit failure on two pinned output hashes. Both files were restored exactly from HEAD; the failure and successful re-audit are retained separately. | Treat registered output files as immutable. Record later follow-ups in versioned addenda and re-run the registry audit before committing. |
