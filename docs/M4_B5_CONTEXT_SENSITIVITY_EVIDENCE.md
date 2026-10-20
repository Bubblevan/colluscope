# M4 B5 Context-Sensitivity Campaign — Evidence

**Experiment:** `m4-b5-context-sensitivity-campaign-v1`
**Evidence class:** finite fixed-corpus Monitor evaluation
**Scientific status:** `INCONCLUSIVE`
**Operational status:** all assigned requests terminal and independently replayed
**Calls:** 232 assigned, 232 attempted, 232 valid HTTP 200 tool responses; zero retries, replacements, or unattempted rows.

## Frozen inputs and provenance

The campaign used the registered DeepSeek Flash alias with temperature 0, thinking disabled, 512 maximum output tokens, and the frozen `report_evidence` tool. All responses reported fingerprint `e72d3c7f663d3e1383b00b3884cb4501`. The alias/fingerprint are provider-reported identifiers, not immutable weight identities. The run occurred from `2026-10-20T21:04:33.707188Z` through `2026-10-20T21:08:24.320524Z` UTC.

| Frozen item | SHA-256 |
|---|---|
| Registered protocol | `79f9f8f6967f783d9469c3ad73ea4a1e903e1b301ca0f26ef9775a1d6454bbdd` |
| Schedule | `c44585532b18e8def0488c4f3de42be1c4a04009566b396251c3da2659043c3c` |
| Hash-only frozen request manifest | `987c5dabff67066ef3fbedb479d30ed90f67552cefe818603334ce56ef711c2a` |
| Registered preregistration | `819d95ff6f8ea3141471b1a8cc669b1ceb20878ee54b4ccc7df702642c229421` |

The protected raw request/response run remains in the Git-ignored, ACL-restricted local run directory `runs/sprint-monitor/m4-b5-context-sensitivity-campaign-v1-run`. Raw private messages and model payloads were not copied into this report or public artifacts. The sanitized request ledger contains attempt hashes, status, times, and usage-derived per-row costs only.

## Independent integrity replay

The no-call independent audit reconstructed the registered request schedule and source bindings; recomputed the public-harm reference labels from public task/action evidence; parsed raw tool responses; checked request and response hashes, response identity, usage, all 232 started/terminal rows, and all 40 registered frozen input hashes. It verified nine source bindings, both protected private-source hashes, and the private truth digest reconstructed from raw requests. The result is `PASS_INDEPENDENT_RAW_REPLAY`.

The execution counts were A1: 72 requests for 24 M4 contexts × three evidence views; A2: 160 requests for 40 synthetic rows × four request forms, clustered into 20 groups. There were 232 `attempt_started`, 232 terminal records, 232 valid tool-call completions, and no retries or replacements.

Usage was 283,855 prompt tokens, 16,444 completion tokens, 300,299 total tokens, including 170,496 cache-hit and 113,359 cache-miss prompt tokens. Summed HTTP latency was 220.044 seconds (mean 0.948466, median 0.969 seconds). The official off-peak usage-derived fee estimate is `$0.027381738`; the all-input-uncached peak-rate ceiling is `$0.104889300`. Neither amount is an invoice. Both are below the approved `$0.90` cap.

Reproduction commands:

```powershell
python scripts/audit_m4_b5_context_sensitivity_run.py
python -m pytest -q tests/test_m4_b5_context_sensitivity_audit.py tests/test_m4_b5_context_sensitivity_runner.py
python scripts/researchctl.py audit
```

The final focused test rerun passed **27 tests** in 25.53 seconds. The complete raw test output is preserved at `docs/results/research-sprint-20261021/direction-review/campaign-postrun-focused-tests-rerun.log`. The audit stdout is preserved at `.../campaign-postrun-independent-audit-final.log`. Earlier failures and intermediate pass logs remain alongside them; the misleading prior log filenames were renamed without changing their contents.

## A1: response changes across evidence views

Independently recomputed public-harm references were 10 `present` and 14 `absent`. Per-view exact labels were Public-only 10/24, Privileged-neutral 4/24, and Privileged-original 17/24. Citation membership was valid in every response, but that is not proof that a citation semantically supports a claim.

| Contrast | Changed labels | No change | Main transitions |
|---|---:|---:|---|
| Public-only → Privileged-neutral | 12/24 | 12/24 | present→insufficient evidence: 11; insufficient evidence→present: 1 |
| Privileged-neutral → Privileged-original | 20/24 | 4/24 | insufficient evidence→absent: 12; present→absent: 7; insufficient evidence→present: 1 |
| Public-only → Privileged-original | 19/24 | 5/24 | present→absent: 16; insufficient evidence→absent: 3 |

The preregistered directional pattern was not met. These are labels on this fixed corpus, not estimates of a general monitor effect, collusion, or latent intent.

### Token and repeated-input sensitivity

Provider-reported prompt-token differences (right minus left) were Public-only→Neutral: `+178` for every case (mean/median +178); Neutral→Original: +113 to +383 (mean +184.625, median +180); Public-only→Original: +291 to +561 (mean +362.625, median +358). The fixed neutral message is substantially shorter. The interventions also differ in message wording, salience and, for Public-only versus Neutral, event packaging, permission and completeness cues. Token equality or semantic isolation was not achieved.

The preregistered exact-input-pair sensitivity found 23 unique Public-only/Neutral input-pair profiles among 24 assigned cases, with one repeated size-2 profile. Its two responses had different transitions. All 24 assigned cases remain in the primary table; the descriptive sensitivity counts 11 changes among the 22 stable unique profiles. The other two contrasts had 24 unique profiles each. This triggers the preregistered `DUPLICATE-SENSITIVE / INCONCLUSIVE` qualification; no sample was removed or replaced.

### Post-hoc historical exact-request comparison

After the registered analysis, a no-call audit compared the A1 Public-only and Privileged-original request bodies with historical requests for the same case hashes and permissions. All 24 Public-only pairs and all 24 Privileged-original pairs had byte-identical request bodies and identical reported fingerprints across the two runs. Labels nevertheless matched only 7/24 Public-only pairs and 22/24 Privileged-original pairs. The old and current Public→Original transition was identical in only 7/24 cases, despite 20/24 versus 19/24 total changes. Historically, the main transition was insufficient_evidence→absent (15 cases); currently it was present→absent (16 cases).

This post-hoc finite comparison establishes non-repeatability for these exact request observations under a matching reported fingerprint. It does not identify why outputs differed, prove identical hidden provider state or immutable weights, or show that output variability explains all cross-view differences. It substantially weakens causal attribution from single calls. The independent critic reviewed this analysis and agreed with that limitation; the critic did not inspect protected raw files or perform the raw-byte integrity replay.

## A2: fixed-fixture request-form diagnostics

The independently reconstructed reference labels were balanced (20 present, 20 absent). Results were:

| Request form | Present | Absent | Insufficient evidence | Exact |
|---|---:|---:|---:|---:|
| V2-direct | 40 | 0 | 0 | 20/40 |
| Production B5 | 35 | 0 | 5 | 20/40 |
| B5 plus six unranked allocation totals | 21 | 19 | 0 | 39/40 |
| Reversed prompt and enum label order | 2 | 15 | 23 | 10/40 |

The arithmetic table makes the deterministic public-harm answer calculable from visible task inputs; 39/40 is not evidence of independent LLM reasoning. Reversing both prompt order and tool-enum order changed 36/40 predictions relative to Production B5, with at least one change in each of the 20 clusters. Because both ordering locations changed together, this is a bundled presentation sensitivity, not an isolated enum-order effect. A2 is a fixed-fixture compiler/presentation diagnostic and not an independent sample or collusion benchmark.

## Adversarial review and decision boundary

The independent critic's conclusion is `INCONCLUSIVE` for the primary mechanism claim. A1 has clear finite response changes, but cannot distinguish message text from token length, wording, salience, package structure, request-level non-repeatability, or mutable provider state. A2 confirms strong request-form sensitivity in a deterministic task; its labels are mechanically derivable from the visible public record. No result establishes semantic comprehension, real-world collusion, intent, detector superiority, or a population-level causal effect.

There were no model calls after the 232 authorized attempts. Any repeated-request study would be a new preregistered experiment and requires fresh scope-specific approval. The campaign's authorization is consumed and non-reusable.

## Evidence files

- Independent replay JSON: `docs/results/research-sprint-20261021/m4-b5-context-sensitivity-independent-audit.json`
- Sanitized per-row analysis: `docs/results/research-sprint-20261021/m4-b5-context-sensitivity-independent-rows.csv`
- Hash-only request/cost ledger: `docs/results/research-sprint-20261021/m4-b5-context-sensitivity-request-ledger-sanitized.json`
- Independent scientific critique: `docs/results/research-sprint-20261021/campaign-postrun-independent-critic-review.md`
- Blind review packet: `docs/results/research-sprint-20261021/campaign-postrun-critic-packet.md`
- Pinned historical failure history: `docs/results/research-sprint-20261021/failure_history.jsonl` (restored byte-for-byte); this campaign’s appended failure records: `docs/results/research-sprint-20261021/campaign-postrun-failure-history-addendum.jsonl`
