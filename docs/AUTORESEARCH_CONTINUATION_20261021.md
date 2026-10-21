# Autoresearch Continuation — M4 B5 Repeatability

- **Date:** 2026-10-21
- **Scope:** offline evidence review and zero-call preparation; no new monitor or agent inference
- **Scientific outcome for the closed B5 campaign:** `INCONCLUSIVE`
- **Current candidate:** `m4-b5-view-repeatability-v2` — prepared, not registered, not authorized

## Evidence inspected

The closed `m4-b5-context-sensitivity-campaign-v1` report and source-pinned audit remain authoritative. Its 232 requests all completed with valid tool responses. On the fixed 24 M4 cases, public-harm references are unchanged across views; prediction changes are 12/24 for Public-only→Privileged-neutral, 20/24 for Neutral→Original, and 19/24 for Public-only→Original. The exact-input historical/current replay also found 19/48 label disagreements despite byte-identical requests and matching reported fingerprints.

The 40-row A2 fixture does **not** have one invariant output profile across runs/forms:

| Request form | Present | Absent | Abstain | Exact against public-harm rule |
|---|---:|---:|---:|---:|
| Earlier 120-call Public-canonical diagnostic | 40 | 0 | 0 | 20/40 |
| 232-call V2-direct | 40 | 0 | 0 | 20/40 |
| 232-call production B5 | 35 | 0 | 5 | 20/40 |
| Correct six welfare totals | 21 | 19 | 0 | 39/40 |
| Reversed prose and enum order together | 2 | 15 | 23 | 10/40 |

The first three forms show a recurring one-sided/abstaining response pattern on this fixed fixture, but “40/40 present” applies only to the first two forms. The later production B5 output was 35 present and 5 abstentions. The deterministic public-harm rule is exact on all 40 rows. Nothing here establishes an LLM advantage on computing public welfare.

## Hypothesis selection

| Candidate | Information value for the current claim | Cost and main limitation | Decision |
|---|---|---|---|
| 144-call repeated M4 views | Directly tests whether cross-view majority changes exceed same-view variation for the same 24 contexts | $0.35 cap; three repeats provide only a small finite reliability screen and still compare bundled evidence packages | **Select** |
| 728-call omnibus B5 mechanism campaign | Could separately probe order, arithmetic display, wording, scale, and M4 repeatability | Combines multiple questions; the A2 positive-only pattern is not invariant across request forms; exact provider-tokenizer matching is not available locally | Defer the 480-call synthetic factorial, 40-call definition arm, 40 repeats, and 24 scale arm |
| M1 natural-message/action audit or prospective communication replication | Could provide a more direct language-monitor or behavior contribution | Human references and an additional authorized experiment are prerequisites; shared incentives and message-turn effects remain confounds | Keep as later candidates |

The 144-call design is the smallest current test of the interpretive blocker. It does not claim a semantic message effect. Every one of 24 contexts receives three byte-identical Public-only requests and three byte-identical Privileged-original requests in a frozen interleaved order. The primary unit is the context, not the 144 requests or the 3 pairwise comparisons within a context.

### Falsifiable outcomes

Use the gates already frozen in the candidate protocol; do not tune them after seeing results.

- **Stable finite package contrast:** at least 18/24 contexts have a unique mode in both views, and cross-view mode changes are at least 6 and exceed the number of contexts with any within-view disagreement.
- **Historical contrast not reproduced:** at least 18/24 have a unique mode in both views, at most 1/24 changes modes across views, and at most 6/24 have any within-view disagreement.
- **Otherwise:** `INCONCLUSIVE`. Any request-body mismatch within a repeated profile, identity/fingerprint drift, or privacy failure invalidates the intended comparison; keep all assigned rows and stop.

Even the first outcome supports only a repeatable difference between the bundled Public-only and Privileged-original packages. It cannot distinguish message meaning from permissions, event structure, completeness cues, wording, salience, token length, or hidden provider state.

## Independent preflight and provenance

The no-call preparation command rebuilt 144 request bodies locally. A separate read-only audit (using the frozen source module only to resolve historical source paths, not to compile request bodies) then verified:

- all 144 assignments map one-to-one to the frozen schedule;
- 48 context/view profiles each contain three byte-identical request bodies;
- all 144 body hashes and serialized lengths match their manifest entries;
- the five source identities in the prepared manifest still match their local files;
- 72 requests per view, the identical 24-context set in both views, temperature 0, disabled thinking, and a 512-token output ceiling;
- no schedule/research identifiers or reference labels appear as request fields;
- the raw run directory is Git-ignored; ACL verification reported success for 304 objects;
- the maximum conservative input bound is 12,104 units, calculated as `2 × UTF-8 request bytes + 256` framing allowance. This is **not** an exact provider-tokenizer count. The worst-case off-peak reservation computed from those per-request bounds and 512 output tokens is $0.2658564, below the proposed $0.35 cap.

The audit emitted hashes and counts only. Raw request bodies and private message text remain under the local restricted `runs/sprint-monitor/m4-b5-view-repeatability-v2-run` directory. The 72 Privileged-original requests contain two private message events each, so a live run would send 144 historical private-message event appearances to the provider. Local ACLs protect stored bytes; they do not prevent provider transmission.

The preparation ran at **2026-10-21 01:23 UTC**, inside the currently published weekday peak interval. It made zero API calls; the off-peak cost is a reservation calculation, not authorization or a live pricing/dispatch check. The old 232-request authorization is consumed by its closed experiment. A new scope-specific approval is required.

One invocation of the schedule builder with unsupported `--check` was preserved as a command failure. The actual CLI supports `--out`; running the valid build command reproduced the existing schedule hash. Two audit-output attempts also failed: a wrapper appended an exit-status line to JSON, and the first source-path resolver referenced a nonexistent module constant. Both failure logs are preserved; the corrected audit emits valid JSON and has a separate exit-status file. These are local tooling errors, not model or experiment outcomes.

### Reproduction commands

```powershell
python scripts/freeze_m4_b5_view_repeatability_v2.py
python scripts/run_m4_b5_view_repeatability_v2.py --prepare
python scripts/audit_m4_b5_view_repeatability_preparation.py
python scripts/researchctl.py audit
```

The final preparation audit is `docs/results/research-sprint-20261021/m4-b5-autoresearch-continuation-20261021/repeatability-preparation-audit-v3.json`. Its assigned schedule, request manifest, source hashes, and all local body hashes are pinned there. The `--prepare` raw console receipt containing the local account SID remains in the ignored restricted run directory. Sanitized summary and command failures are in the result folder; the raw private prompts are not copied there.

The earlier offline fake-server runner suite recorded 6/6 passing checks in `docs/results/research-sprint-20261021/m4-b5-view-repeatability-v2-offline-canary/pytest-final.log` (verify the repository path before using this as a current reproduction reference). It is engineering evidence only, not live model evidence. This iteration did not run tests.

## Adversarial literature review

The proposed repeatability question is not novel as a general LLM-output reliability study. Nicholson reports repeated identical-prompt runs at temperatures 0.0 and 0.7 for two publicly accessible models and finds output variation can persist at temperature zero ([arXiv:2601.19934](https://arxiv.org/abs/2601.19934)). Patodiya reports exact-repeat and serving-cache differences for local `llama.cpp` and quantized Qwen2.5-7B, including Q4_K_M, while cache-disabled repeated executions were exact in the tested setup ([arXiv:2609.04748, v2](https://arxiv.org/abs/2609.04748)). That is a particularly strong alternative mechanism for local serving, but it does not establish the cause of differences observed through DeepSeek's hosted API.

DeepSeek's official API documentation describes lower temperature as making output more focused and deterministic; it does not promise identical outputs. The current official model/pricing page lists `deepseek-flash` as DeepSeek-V4.1-Flash-1017, with $0.15/M off-peak uncached input and $0.60/M output, and weekday peak windows 01:00–04:00 and 06:00–10:00 UTC ([API parameters](https://api-docs.deepseek.com/api/create-chat-completion), [pricing](https://api-docs.deepseek.com/quick_start/pricing/)). Prices and model aliases can change; they must be checked again immediately before any separately approved run.

**Contribution boundary:** if executed, this can add only a finite, task-specific audit of whether B5's evidence-package contrast is larger than short-window same-input variation for these 24 contexts. It cannot identify random sampling versus provider serving state; prove stable model weights; generalize to other models; establish message comprehension; or establish collusion/intent. Paper-level novelty remains unproven.

## Self-critique and decision

This is an adversarial self-review, not a new independent critic assessment. The existing separate-context critic found the broader B5 mechanism inconclusive and warned that a deterministic public-harm rule leaves no demonstrated LLM-specific advantage. The selected 144-call question is deliberately narrower. Three repeats and one short provider window may be too weak to characterize hidden serving state; a stable package contrast still cannot be attributed to private-message semantics. The study is worthwhile only as a scoped reliability check that determines whether the historical single-call contrast is interpretable at all.

**Decision:** `INCONCLUSIVE` for the mechanism claim; `PREPARED_OFFLINE / NOT_REGISTERED / NOT_AUTHORIZED` for the next candidate. No model/API call was made in this iteration. Do not launch the 728-call omnibus or the 144-call candidate from this record.

**Single next action:** seek a new user approval naming `m4-b5-view-repeatability-v2`, at most 144 physical attempts and $0.35, official DeepSeek Flash only, zero retries/replacements, off-peak only, an explicit expiry, and external transfer of 144 private-message event appearances. The proposed expiry is 2026-10-25 23:59 UTC. After approval, register the exact frozen protocol and rerun the pre-dispatch identity, price, window, token-bound, ACL, manifest, and budget gates. Registration alone is not permission to dispatch.
