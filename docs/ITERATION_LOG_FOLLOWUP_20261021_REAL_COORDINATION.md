# Iteration follow-up — DeepSeek real coordination pilot

## INSPECT

Review of the preceding 804-request study identified a misleading fact-transfer prompt (0/20 controls), plus 21 truncated stage outputs followed by 84 dependent ballots. The new fixed pilot initially put four fact controls first, but review found that a wrong yet schema-valid control answer still needed to stop all later calls. The runtime path also had to match its preregistration directory exactly.

## SPECIFY / FALSIFIERS

- Delivered authoritative ALPHA/BETA fact must be reported exactly; an explicitly absent message must yield UNKNOWN.
- Inject a wrong response at each of the four control positions; no subsequent model request may occur.
- A truncated/invalid stage must not populate the dependency map; dependent requests remain unattempted.
- Distinct canary strings in proposal and reply contexts must not cross into no-delivery or neutralized recipient prompts; actual delivery must follow the scheduled route.
- Raw request replay must compare exact bytes, not just equivalent parsed JSON.

## IMPLEMENT / RUN

The offline implementation adds explicit routing, four controls before any game call, a stop-on-first-control-failure gate, descendant blocking, exact raw-request reconstruction, independent settlement, and local tokenizer token counts. Targeted suite: `python -m pytest -q tests/test_deepseek_real_coordination_v1.py tests/test_deepseek_real_coordination_analysis_v1.py` — **16 passed**. Three earlier offline failures were retained in `docs/results/deepseek-real-coordination-v1/OFFLINE_ATTEMPT_001.md` through `OFFLINE_ATTEMPT_003.md`; fixes corrected test expectations and strengthened exact-byte verification without removing adversarial cases.

The registered V1 check then failed before any request because the runner's hard-coded preregistration path omitted `-40`. The failure and command are preserved in `docs/results/deepseek-real-coordination-v1/PREFLIGHT_PATH_MISMATCH.md`. No model call occurred. The two historically hash-pinned files accidentally edited during logging/ignore setup were restored exactly; the research registry now audits with no errors.

## ADVERSARIAL REVIEW

The arms share the +20 HH incentive and use four model calls each. This addresses extra-stage count but not every prompt-content or token-length difference. The neutral arm permits a delivered return reply, so its contrast is a content-substitution policy with downstream interaction, not a pure semantic effect. Since both agents know the same rewarded target, HH without delivery can be independent parallel behavior. Three fixed matrices, one same-model alias, temperature zero, and one run per cell do not support population or latent-intent claims.

## DECIDE

Do not call the model with the V1 registered path mismatch. Preserve the V1 frozen record and close it as execution-blocked with zero calls. Create V2 artifacts with aligned experiment/preregistration paths, rerun all offline checks, register, push the exact freeze, then use the existing user-authorized 40-request DeepSeek scope. The four controls remain first; any failure stops all 36 game requests.

## REPORT

No behavioral result exists yet. Highest-value next action: complete and validate V2 runtime path alignment, then promptly run the already approved bounded pilot after pushing its freeze.
