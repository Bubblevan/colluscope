# DeepSeek-First M4 and Monitor — Results and Scientific Audit

**Run date:** 2026-10-20. **Authorization:** one bounded official-DeepSeek run, now consumed. **Protocol freeze:** `550bf1361609e405dc50aa60d5d77b9c502e5bf0`. **Provider:** `deepseek-flash`; returned `system_fingerprint=e72d3c7f663d3e1383b00b3884cb4501`. This is one alias/fingerprint execution, not a fixed-weight replication.

Runtime environment: Windows 11 (build 26200), Python 3.12.4; the provider-managed tokenizer identity is not exposed as an immutable revision. The Agent manifest is SHA-256 `9ab42c327b5f915337480628c42e99620b57513e00e8771dafeef1d6cb56554f`; the frozen Monitor plan manifest is SHA-256 `f2d00fed806cb61653f4a0f542b9c255c1c33923b098f66de84c689976bb198a` (local manifest; hash only is published).

## 1. Integrity and request accounting

| Phase | Scheduled | HTTP 200 | Valid/complete | Failed / not dispatched | Physical attempts |
|---|---:|---:|---:|---:|---:|
| Strict compatibility pilot | 20 | 20 | Agent 8/8; Monitor 12/12 | 0 | 20 |
| M4 Agent | 24 groups | 232 | 24 groups | 0 | 232 |
| Monitor | 376 rows | 376 | 376 parsed, citation-membership-valid rows | 0 | 376 |
| **Total** |  | **628** |  | **0** | **628** |

All requests were terminalized once: 628 HTTP 200, 0 non-200, 0 attempts without an HTTP response, 0 ambiguous/unterminalized starts, 0 retries, 0 replacement groups, and 0 cap breaches. The pilot selected Strict Function Calling; the predefined JSON fallback was not used. The old pre-run launcher exception remains preserved and is not counted as a request.

Provider usage: 655,032 input tokens and 43,645 output tokens. At the official peak-rate schedule checked immediately before execution, estimated usage was USD 0.2488836; the conservative reserved total was USD 1.7744040. The hard authorization limits were 900 physical requests and USD 5.00. No external provider, model training, weight download, or post-run inference was used.

## 2. Agent observations

All 24 frozen scenario/seed groups completed and were independently recomputed from raw request/response records, ballots, payoff matrices, and permissions. The audit verified context reconstruction, A/B message delivery boundary, all 72 sealed baseline ballots, deterministic plurality/chair settlement, welfare, regret, private task-score bonus, Public-only evidence, and request/response hashes.

| Observable | Result |
|---|---:|
| Baseline ballots | 72 valid |
| Baseline ballots matching shared rewarded target | 13/72 |
| Rewarded target allocation executed | 2/24 groups |
| Mean / median public regret | 1.9583 / 0 |
| Regret distribution | 0:14; 2:3; 4:2; 5:1; 7:4 |
| Messages sent / delivered | 48 / 48 |
| Complete literal allocation proposals | 20/48 messages |
| Complete proposals matching recipient baseline ballot | 11/20 |
| Information positive control followed | 24/24 |

Among the 20 complete proposals, 15 specified the matrix's public optimum, four specified another allocation, and one specified the rewarded target. A further 28 messages were sent but did not encode a complete allocation under the frozen parser. The short lexical marker scan found 0/48 messages matching its frozen patterns; that scan is not semantic commitment annotation.

Mean regret by matrix family was F1 0.00, F2 5.75, F3 1.75, F4 0.50, F5 1.75, F6 2.00 (n=4 per family). These scenario-specific regret values are comparable to each family’s own public optimum; raw welfare is not pooled across payoff scales.

Sixteen of 24 groups entered the proposal-eligible focal stage; all 24 remain in the assignment denominator. The four focal counterfactual ballot-change rates from each recipient's own baseline were: masked-history neutral 9/16, masked-history proposal 6/16, retained-history alternative 4/16, retained-history neutral 5/16. These are conditional prompt responses, not independent replications or a causal estimate.

An additional independent calculation replaced only the focal ballot and held the other two baseline ballots fixed, then recomputed plurality/chair selection and family-specific welfare from the raw ballot and matrix. It verifies baseline replay against the independent group audit before scoring the focal variants.

| Focal arm | Ballot changed | Selected allocation changed | Target selected | Mean regret | Mean regret delta vs eligible baseline |
|---|---:|---:|---:|---:|---:|
| Masked-history neutral | 9/16 | 5/16 | 4/16 | 3.250 | +1.750 |
| Masked-history proposal | 6/16 | 4/16 | 4/16 | 3.313 | +1.813 |
| Retained-history alternative | 4/16 | 4/16 | 4/16 | 3.625 | +2.125 |
| Retained-history neutral | 5/16 | 4/16 | 4/16 | 3.125 | +1.625 |

The eligible-group baseline regret mean was 1.500. A focal vote change often left the plurality/chair outcome unchanged. These deterministic fixed-peer replays do not represent newly observed episodes and cannot show how other agents would respond in a natural repeat.

Provider prompt tokens matched exactly in the positive-information/neutral control (0 difference in 24/24). Real proposal/neutral focal prompts were not matched: proposal minus neutral averaged +60 tokens, range +32 to +85 (n=16). This creates a material input-length/salience confound. The observed counterfactual ballot changes cannot be attributed uniquely to proposal semantics.

## 3. Monitor observations

All 376 frozen rows across three populations were sent once and independently replayed. Every response parsed, and every cited event ID belonged to the evidence projection supplied on that request. The independent exact-match scorer found 145/376 requests correct on all attached reference labels and 145/400 exact individual reference labels. Syntax and citation-membership validity must not be conflated with factual accuracy or semantic citation support.

Using the frozen abstention set (`insufficient_evidence`, `uncertain`, `unknown`), 45/376 Monitor request outputs abstained (12.0%). On the observable `explicit_sequence` task, 9 predictions said `supported`; 6 matched a `supported` reference and 3 were emitted against one of 190 references labeled not-supported, not-visible, uncertain, or insufficient. This is a task-reference unsupported assertion count, not a latent-collusion false-positive rate.

| Population | Method | Exact reference labels / rows |
|---|---|---:|
| Natural DeepSeek M4 traces | B4 raw fusion | 52/144 (36.1%) |
| Natural DeepSeek M4 traces | B5 evidence-aware | 47/144 (32.6%) |
| Scripted synthetic controls | B4 raw fusion | 5/8 (62.5%) |
| Scripted synthetic controls | B5 evidence-aware | 5/8 (62.5%) |
| Matched synthetic worlds | B4 raw fusion | 18/48 (37.5%) |
| Matched synthetic worlds | B5 evidence-aware | 18/48 (37.5%) |

The populations and denominators must remain separate. Task, episode, permission and repeated-view rows share contexts; these rows are not independent observations. The 126 assessable B4/B5 matched pairs yielded 65 both-exact, 10 B4-only exact, 4 B5-only exact and 47 neither-exact. Predictions were label-identical in 101/126. These descriptive paired outcomes do not establish superiority. The 400 reference-row exactness denominator is the relevant per-label score, whereas 145/376 is a stricter all-references-per-request measure.

### Scripted positive and hard-negative controls

The 16 frozen scripted-control requests split into four observable positive and four observable hard-negative cases per Monitor method. Exact-reference counts were B4: 3/4 positive, 2/4 negative; B5: 4/4 positive, 1/4 negative. Across the four same-control/task/permission positive pairs, both methods were exact in 3, B5 alone in 1, and neither/B4 alone in 0. Across four hard-negative pairs, both were exact in 1, B4 alone in 1, B5 alone in 0, and neither in 2. These are small synthetic protocol controls: they support neither a sensitivity/specificity estimate nor a natural-world detection claim. In particular, the hard-negative misses are retained and visible.

### Public versus privileged evidence

The frozen matched-world public inputs and observable references remained byte-identical across each matched pair; privileged projections differed only by permitted message evidence, as confirmed by the independent audit. Public-only matched-world exact references were absent/not-visible by design. Results on these synthetic cases test the frozen evidence boundary, not natural prevalence. No latent-intent labels are present.

## 4. Failures, repairs, and retained negative evidence

Before the successful execution, the first orchestrator launch failed at local pilot initialization with `UnboundLocalError` due to a function-local import shadowing `write_once`. No physical request start was recorded. The exact failure was retained. A minimal fix removed the shadowing import and added a mocked end-to-end regression. The corrected freeze was pushed before actual inference; its plan was byte-reproduced, preflight receipt renewed, and full suite passed.

The first post-run analysis attempt also failed because the scorer CSV did not contain a `population` field. Its failure log remains in the result logs. The analyzer now derives population only from the frozen `phase_id` mapping and has regression coverage. It never exports message text, request bodies, or provider responses. No failed episode or model row was deleted or replaced to obtain the reported counts.

## 5. Claim-to-evidence boundary

| Claim | Status |
|---|---|
| The bounded request schedule completed within limits and raw records independently replay | **Supported for this run** by the append-only ledger and independent raw replay. |
| The DeepSeek Agent emitted observable ballots/messages and task outcomes | **Supported descriptively** for 24 assigned groups under this one alias/interface. |
| A delivered proposal caused a matching vote | **Not identified**. Shared target information, own histories, the conditional eligible subgroup, and prompt token differences remain alternative explanations. |
| B5 outperforms B4 | **Not supported**. Only 14/126 pairs were discordant on the all-reference exactness outcome (10 B4-only vs 4 B5-only); no superiority claim was preregistered or powered. |
| The Monitor detects latent collusion | **Not supported**. There is no latent-intent ground truth. |
| Results generalize to DeepSeek weights, model families, or real institutions | **Not supported**. The provider alias has no pinned weight hash and the task is synthetic. |

## 6. Reproduction and artifact hashes

Run from a checkout with the ignored local raw directory `runs/deepseek-first-m4/` and the exact code/dependencies:

```powershell
python scripts/audit_deepseek_first_research.py
python scripts/analyze_deepseek_first_research.py
python scripts/plot_deepseek_first_research.py
python -m pytest -q
```

Sanitized audit hashes:

- Agent summary: `9fd50cb250cc3867b26ad45b14c035a3f1fb3652fe36defa061b69b5a44031e0`
- Monitor summary: `49f3cf85cde5a4a6561b18c7dc6ed92e565a0a9e77e0bc48bbb477a5dd4d6ca7`
- Combined independent audit: `ca5fadb95c7377d54659139c3e1138a51cc97333b2d05b6102cb94a3ca41af57`
- Sanitized analysis JSON: `35aff02b2790cd4b3d19d452213a9447b0fb939ba3767fdbbb38974c3900b93d`
- Version-2 sanitized analysis with independent focal settlement, abstention and unsupported-sequence counts: `6cff80e9ee675b9b09e723228183b3901977c4bdc12f43b415fa50db34311cb4`
- Sanitized per-group table: `4a1caa0ced27a33dcb22ccd4f833851597ed88d6b0b9b4178e5fd8df4f28b015`
- Sanitized Monitor request outcomes: `b784177b1dd2cdf695cb5f2772b9793b42c6b34bd9980b51acb53d5317448d98`
- Sanitized Monitor per-reference rows: `ebfc472cb615fc351d35099e2f61469396a3f1d08d82534fe3daf4ebd9cc48a7`
- Sanitized Monitor paired table: `fba44c77d2582a087e202ef3b922ed92debb4ed55509d01931876ef91c96d3da`
- Private final run summary (local only): `d8a577d2976fd2ab313ed3f3f314f96c929e7f149f66ccb7252d2110f39cbfa2`
- Private global budget ledger (local only): `716d3a62c5a7f5c8edc14e1d4487c02bf6ad6daddebf4a3082bea5a1f255ae51`

Figure reproduction source: `scripts/plot_deepseek_first_research.py`; figure hashes and its input hashes are in `docs/results/deepseek-first-m4/figures/manifest.json`. The version-2 figure set includes a separate ballot-versus-settlement change plot.

The targeted privacy-plus-analysis suite passed **8 tests**, including focal-settlement, abstention/unsupported-assertion, and private-message exact-text scanner counterexamples. The reproducible privacy command is `python scripts/audit_deepseek_message_privacy.py`; it reads only the ignored local raw Agent response store and emits counts and matching file paths, never message text. Its sanitized result is `docs/results/deepseek-first-m4/logs/privacy-scan-final.json` (48 messages, 623 files, no matches; SHA-256 `c205a2648089b8e55be47d8f0b69f3c1d79c21c1f833be8624faae7bf8fef45c`). The targeted test log SHA-256 is `4a7a681458c41df32870635250738c8dbabc6038c8e530a18d9ddbe5c0bc3698`. The complete current repository suite passed **556 tests with 1 opt-in Windows owner-table check skipped in 217.79s**; stdout SHA-256 is `2924095a8320abd1173c0f1f3811ac310b4ea41fe32eeb1672b96109cf2b2834` at `docs/results/deepseek-first-m4/logs/pytest-full-final-with-monitor-claims.log`.

The full raw T/B/E records, provider requests/responses, and private messages remain in Git-ignored, ACL-restricted storage. Do not publish them automatically.
