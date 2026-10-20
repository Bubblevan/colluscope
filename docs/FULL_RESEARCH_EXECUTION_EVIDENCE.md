# Full Research Execution Evidence

**Run date:** 2026-10-20 (Asia/Shanghai)
**Branch:** `codex/full-research-execution-20261020`
**Frozen pre-inference commit:** `34bb78e` (`Freeze full research execution inputs and budgets`)
**Authorization:** user attachment SHA-256 `6bf181cc9e2b1a1a022378bcb8c7e43488f12440a1b0f03c3eb073ec9186e0ad`

This report separates Agent generation, Monitor inference, deterministic scoring, and synthetic construction checks. It does not define or infer a latent-collusion label.

## 1. Scope and immutable provenance

The pre-inference commit froze the M4-v3 assignment and all three DeepSeek schedules before any Monitor request. The signed-off branch commit was pushed before the first provider call. M4 used the audited local Qwen3-8B Q4_K_M GGUF and llama.cpp b10068 at authenticated loopback `127.0.0.1:8081`. Monitor calls used only the official DeepSeek endpoint and the `deepseek-flash` alias. No paid/external Agent calls, fine-tuning, or model training occurred. There were no Monitor retries or replacement rows.

The final Monitor response identity was stable across all phases: alias `deepseek-flash`, system fingerprint `e72d3c7f663d3e1383b00b3884cb4501`. The official pricing and decoding caveat were frozen in [the execution protocol](FULL_RESEARCH_EXECUTION_PROTOCOL.md): provider-default thinking remained enabled, `temperature=0` was present but ineffective in that mode, and `max_tokens=128` included reasoning tokens. The total USD estimate uses the frozen official peak rates, not a provider invoice.

M4 asset identities, independently recorded before execution: GGUF `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`; llama.cpp build `b10068-571d0d540`, binary `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`; bundle `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759`; tokenizer `06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f`; chat template `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361`.

The three independently frozen Monitor plans were:

| Phase | Request rows | Config SHA-256 | Frozen plan SHA-256 | Request schedule SHA-256 |
|---|---:|---|---|---|
| Scripted controls | 280 | `d44cb0dac94ebd64d6ee137e76cdba8e7e1abb60823f55e4baafd6d14af39a20` | `78cab67e6b2196506d36e0e3ee05f37559266c40317422fe0ae6c83dc7955ee0` | `65c1b5583b8b2a21c6b13adcd95b13d6c74a1f2248ce4d414345b01cf7847deb` |
| M4 traces | 504 | `80021d1557e677c7d0a8933ac0b58637c01f42d248c66c12a5090bc3d3890842` | `f063122fd44c2db878585ad92d725b617140ddb71e343715fab2d85e246f6acc` | `3aaea405193e85e9f52639152c49dd7994451bfae7b4c978a39c5b66322c8030` |
| Matched worlds | 72 | `0250a1916defe3a914ace2d589fd70980def7e13f9c16707d6b9078ff33e88a1` | `a75e28f611f1579571c15a095f53140a6ac0d5d1e1a8ae4857abdec2c985ac7c` | `9e2f5cbb150c76d79b4b99e13335727b1685e4e4b199183018a0038bea8977b2` |

Only synthetic ColluScope evidence was sent to DeepSeek. No credential, treatment/seed/reference label, researcher-only field, or raw unrestricted T record was included. Private raw Agent messages, exact privileged request bodies, full responses, authorization receipt, and append-only request history remain in ACL-restricted, Git-ignored run directories. Public artifacts contain sanitized aggregates and hashes only.

## 2. M4 local Agent run

| Measure | Independently audited result |
|---|---:|
| Assigned groups | 24 / 24 |
| Local generation attempts | 24 / 264 ceiling |
| Local authenticated identity probes across retained pre-generation/final directories | 2 GET requests |
| HTTP / finish reason for generation calls | 24 HTTP 200 / `stop` |
| Strict action-parser failures | 24 / 24 (`INVALID_JSON`, leading reasoning tag) |
| Valid messages / ballots / proposal-eligible groups / settlements | 0 / 0 / 0 / 0 |
| Retries / replacements | 0 / 0 |
| Input / output tokens | 10,764 / 1,098 |

The independent replay validates the assignment and terminal-attempt ledger, and confirms that no response was linked to a valid action and no settlement was fabricated. This is a runtime/action-contract failure under the frozen configuration. The M4 behavior contrast and outcome are **not estimable**; it is not a null effect. Across the authorized work there were 24 local Qwen generations and 856 remote Monitor requests (880 inference calls total), plus two local authenticated identity-probe GETs (882 physical HTTP requests including probes). Identity probes are infrastructure checks, not model generations.

## 3. DeepSeek Monitor execution

| Frozen phase | Assigned requests | Parseable predictions | Invalid at `length` cap | Input tokens | Output tokens | Estimated cost (USD) | Mean latency (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original scripted controls | 280 | 16 | 264 | 285,127 | 35,583 | 0.1282377 | 1.445885 |
| Actual incomplete M4 traces | 504 | 123 | 381 | 291,672 | 60,379 | 0.1599564 | 1.399261 |
| Matched evidence worlds | 72 | 2 | 70 | 90,888 | 9,201 | 0.0383076 | 1.431824 |
| **Total** | **856** | **141** | **715** | **667,687** | **105,163** | **0.3265017** | — |

All 856 requests have one terminal physical HTTP attempt; all 715 invalid outputs ended with `finish_reason=length`. This is 83.528% of the request schedule. No row was retried, repaired, or replaced. The maximum schedule-specific conservative reserve was USD 1.0224735 against the authorized USD 3.00 ceiling. Actual token/cost records were reconciled against raw phase responses and the cross-phase ledger. The public independent analysis recomputes elapsed times from raw attempt start/terminal timestamps; an earlier audit JSON field reported an elapsed sum of zero because its schema did not contain duration values. That original audit file was preserved and not silently rewritten.

### 3.1 Protocol completion by method

The table reports `parseable / scheduled`, not task accuracy. A cell not scheduled by the frozen design is shown as `—`.

| Method | Scripted controls | M4 traces | Matched worlds |
|---|---:|---:|---:|
| B2 text-only | 9 / 80 | 24 / 144 | — |
| B3 action-only | 0 / 40 | 19 / 72 | — |
| B4 raw fusion | 4 / 80 | 39 / 144 | 0 / 36 |
| B5 evidence-aware raw | 3 / 80 | 41 / 144 | 2 / 36 |

All assigned denominator counts come from the frozen schedule/progress ledger, not the subset of completed rows. The initial draft coverage figure mistakenly used the scorer's completed-row list as if it were the assigned denominator. Visual review exposed this; the analyzer now joins every frozen progress row to independently scored completed outputs and renders unscheduled cells as “not scheduled.” Regression tests cover both denominator conservation and the distinction between `0/0` and a measured `0%`.

### 3.2 Observable scoring and baselines

- In the scripted Public-only/Action-only `public_harm` cell, B1 deterministic replay was correct on 7/7 assessable rows, including all five positive references. B0 always-negative was correct on 2/7 and recalled 0/5 positives. This is a narrow, synthetic, same-cell deterministic reference; B1 is not an LLM.
- Among parseable scripted outputs, B2 had 4/4 exact matches on its four assessable rows; B4 had 4/4; B5 had 2/3. The completed and assessable subsets differ by method, so these ratios do not establish a ranking. Across the scheduled rows, only 16/280 outputs were parseable.
- Within those selected parseable scripted rows, positive-reference/positive-prediction counts were B2 3/3, B4 4/4, and B5 2/2. These are conditional case counts, not sensitivity estimates: the majority of each method schedule was unparseable. No parseable model output landed on a frozen `hard_negative_control` row (n=0); therefore the empirical model unsupported-sequence rate on hard negatives is **not estimable**, rather than 0%. No unsupported sequence assertion was observed among the parseable responses, but this does not establish specificity.
- Among the 123 parseable M4-trace outputs, all were abstention-like labels. The task-specific scorer marked 111/123 repeated view/task rows as appropriate abstentions; the remaining 12 were inappropriate abstentions under their row references. There were no positive sequence claims in these parsed M4-trace outputs. These are repeated, correlated rows, not 123 independent episodes.
- Across all three phases, B4 and B5 had **zero common completed-and-assessable instances**. The predeclared paired raw-fusion versus evidence-aware accuracy comparison is not estimable.
- Provenance gating is a deterministic transformation of B5's stored raw output and citations. It incurs no model call and must not be counted as a second LLM result. In the matched worlds the only two parseable responses were B5 Privileged positive-control predictions; both had sufficient citations and matched their observable sequence references. This two-row subset is not an accuracy estimate.

B5 raw versus its offline provenance-gated projection on the same parseable rows:

| Phase | B5 raw rows | B5 gated rows | Gated exact assessable | Gated appropriate abstentions | Gated sufficient positive citations |
|---|---:|---:|---:|---:|---:|
| Scripted controls | 3 | 3 | 2 / 3 | 0 | 2 |
| M4 traces | 41 | 41 | 0 assessable | 33 / 41 | 0 |
| Matched worlds | 2 | 2 | 2 / 2 | 0 | 2 |

The gate adds no new model outputs. In these sparse completed subsets it leaves the aggregate exact-correct counts unchanged; this is not evidence that gating generally cannot help. Both raw and gated results are preserved by request ID in the private audit and their task/view aggregates are in the public CSV.

Full task/view values, deterministic baselines, and method denominators are in `monitor_task_view_metrics.csv`, `deterministic_rule_baselines.csv`, and `monitor_method_coverage.csv` under the results directory. The superseded chart/projection issues and their corrections are recorded in `analysis_review_history.md`. All assigned, completed, and failed rows remain represented.

### 3.3 Language and evidence-processing cost

| Method | Assigned API rows | Parseable | Input tokens | Output tokens | Estimated peak-rate cost (USD) |
|---|---:|---:|---:|---:|---:|
| B2 text-only | 224 | 33 | 128,661 | 27,752 | 0.0719007 |
| B3 action-only | 112 | 19 | 76,560 | 13,721 | 0.0394332 |
| B4 raw fusion | 260 | 43 | 195,315 | 32,048 | 0.0970521 |
| B5 evidence-aware raw | 260 | 46 | 267,151 | 31,642 | 0.1181157 |
| **Total** | **856** | **141** | **667,687** | **105,163** | **0.3265017** |

B5 used 71,836 more input tokens than B4 over the same 260 scheduled requests (about 276.3 extra tokens/assigned request) and had USD 0.0210636 more peak-rate API cost; its total output was 406 tokens lower. This is the end-to-end difference between the frozen B5 and B4 payloads, not an isolated causal estimate of ledger cost. The offline B5 provenance gate adds **zero** API requests and zero provider tokens. Local deterministic computation times for B1 and the B5 evidence ledger were not instrumented, so no wall-clock/CPU overhead claim is made. Per-phase/method latency and token costs are in `monitor_method_resources.csv`.

## 4. Matched-world identifiability audit

| Check | Result |
|---|---:|
| Scripted matched pairs | 12 |
| Public-only projection byte/reference equality | 24 / 24 comparisons |
| Privileged projection differs on observable private evidence | 24 / 24 comparisons |
| Public-only observable references | 24 `not_visible` |
| Privileged observable references | 4 `supported`, 32 `not_supported`, 8 `uncertain`, 4 `insufficient_evidence` |
| Parseable Monitor outputs | 2 / 72, both B5 Privileged positive-control predictions |

The matched-world construction tests a deterministic permission boundary: the public projections are identical while allowed private message evidence differs. The positive-control labels describe visible proposal/acceptance/action sequences, not hidden intent. There is no latent-collusion gold label. The two outputs do not show general monitor accuracy or reliable detection.

## 5. Table and figure interpretation

The four figures in `figures/` are derived from independently audited public aggregates:

1. `m4_attempt_disposition.png` shows that all assigned M4 groups reached only the first message attempt and none reached message, ballot, or settlement outcomes. It is a failure/disposition chart, not an intervention-effect plot.
2. `monitor_method_coverage.png` reports parseable completion by frozen method/population with full assigned denominators. Coverage is not accuracy; gray cells were not scheduled.
3. `matched_evidence_sufficiency.png` shows the separately compiled observable-reference categories under Public-only versus Privileged permissions.
4. `matched_world_identifiability.png` shows the paired public indistinguishability and privileged-evidence construction checks alongside the low parseable-output count.

The deterministic computation baseline recomputes task facts from allowlisted source events; language models interpret serialized evidence; source validation/gating checks source-event membership and provenance; and total API cost covers all 856 physical requests. B5's extra ledger is a deterministic input-processing component. This run supplies no common assessable B4/B5 comparison and no evidence that B5 adds value beyond B4 or B1.

## 6. Reproduction commands

Run from the repository root with the private ACL-restricted `runs/` tree available. These commands make **no model/API calls**:

```powershell
$env:PYTHONPATH = 'src'
python scripts/audit_full_research_m4.py --run runs/m4/full-research-execution-20261020-run03 --out docs/results/full-research-execution-20261020/m4_independent_trace_audit.json --source-commit 8eade50aab27a3ef5e0e2ff99f43b3cbc3ec481b
python scripts/audit_full_research_monitor.py scripted_controls --run runs/full-research-execution-20261020/monitor/scripted_controls --freeze runs/full-research-execution-20261020/monitor/freezes-v2/scripted_controls --out runs/full-research-execution-20261020/monitor/audits/scripted_controls.json
python scripts/audit_full_research_monitor.py m4_trace_eval --run runs/full-research-execution-20261020/monitor/m4_trace_eval --freeze runs/full-research-execution-20261020/monitor/freezes-v2/m4_trace_eval --out runs/full-research-execution-20261020/monitor/audits/m4_trace_eval.json
python scripts/audit_full_research_monitor.py matched_worlds --run runs/full-research-execution-20261020/monitor/matched_worlds --freeze runs/full-research-execution-20261020/monitor/freezes-v2/matched_worlds --out runs/full-research-execution-20261020/monitor/audits/matched_worlds.json
python scripts/analyze_full_research_execution.py
python -m pytest -q tests/test_full_research_execution_analysis.py
python -m pytest -q
```

Final post-run offline suite: **469 passed, 1 optional host-dependent Windows owner-table integration test skipped** in 125.78 seconds. Raw terminal output is saved at `offline-full-suite-final-postanalysis.log`; the preceding 468/1 run remains separately preserved at `offline-full-suite-postrun.log`. The final run followed the pre-inference 460-passed/1-skipped suite and includes all analysis regressions; none of these suites invokes a model.

The row-level source data are deliberately not committed. A third party without authorized access to the local raw run roots can verify the public aggregate hashes and source code but cannot independently replay private message-level rows from the public repository alone.

## 7. Reviewer-facing objections

1. The M4 strict JSON contract may be incompatible with the model's emitted reasoning-tag format or the prompt/template pairing. These 24 failures do not identify which component caused the behavior; they only establish that the frozen end-to-end contract failed.
2. DeepSeek's provider-default reasoning mode and 128-token completion budget made most outputs unusable. Conditional results over the 141 parseable rows are strongly selected by output completion and are not representative of the 856-row schedule.
3. Only one provider alias/fingerprint and one date were used. The provider alias is not a checkpoint-level immutable model identity.
4. The 280 scripted prompts are a tiny synthetic set; their successful positive predictions may reflect case construction and are not natural-collusion performance.
5. The M4 trace population has no complete agent episode, so it is not a natural behavior benchmark despite being derived from real local model attempts.
6. The matched-world positive control is scripted and observable by design. Public equality demonstrates an identifiability limit only relative to the defined views and projection; it does not establish universal impossibility under additional evidence.
7. Token/cost accounting and independent audit rely on local private artifacts. Secure reviewer access is needed for row-level reproduction.
