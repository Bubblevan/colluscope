# DeepSeek-First M4 / Monitor — Integrated Evidence

**Current status:** bounded real run complete; independent raw replay passed; scientific interpretations remain descriptive and claim-limited.
**Provider scope:** official DeepSeek API only; no local Qwen, third-party provider, external fallback, download, training or M2 detector comparison.  
**Protocol versions:** `M4-DEEPSEEK-AGENT-V1` and `M4-DEEPSEEK-MONITOR-V1`.

## Frozen design and budget

| Stage | Assigned requests/groups | Maximum physical attempts | Gate |
|---|---:|---:|---|
| Compatibility pilot | 8 Agent + 12 Monitor Strict; only on explicit Strict capability rejection, 4 Agent + 6 Monitor fallback | 30 | Agent output types and Monitor parse/pair/permission gate |
| M4 Agent | 24 frozen groups | 264 | First two preselected groups independently replay before remaining groups |
| M4 Monitor initial | First 6 groups × 3 tasks × 2 methods × 2 permissions | 72 | At least one assessable paired B4/B5 raw prediction |
| M4 Monitor remaining | Remaining 18 groups, same schedule | 216 | Only after initial pair gate passes |
| Scripted controls | Frozen synthetic positive/hard-negative set | 16 | After all 288 natural trace rows are terminal without fatal stop |
| Matched worlds | Frozen paired public/privileged set | 72 | After all 288 natural trace rows are terminal without fatal stop |
| **Total planned maximum** |  | **670** | Shared hard limit 900 attempts / USD 5 peak-rate reserve |

There are zero retries and zero replacement groups. Every assigned group and request remains in its denominator. The static 30-slot compatibility schedule and its input/source hashes are in `configs/m4-deepseek-pilot-plan-v1.json`. The Agent and Monitor protocols preserve the original M4 scenario, incentive, seed/split and task rules while explicitly versioning the provider/runtime interface.

## Pre-inference evidence

- Python 3.12.4, Windows 11. Temporary current-user-only ACL setup and verification passed.
- `.env` endpoint/model preflight passed; credential content was not printed or copied.
- Synthetic raw-response and injected fake-HTTP tests exercised both output interfaces, complete Agent group execution, context isolation, send/delivery distinction, settlement replay, monitor parsing, citation/input freeze, hard request cap, gate stopping, and error retention.
- Corrected candidate targeted suite: **36 passed**, including byte-for-byte reproduction of the regenerated 30-slot plan. Corrected candidate full repository suite: **548 passed, 1 skipped in 137.09s**; the skip is the opt-in host-dependent Windows listener-owner-table check. The complete output is `docs/results/deepseek-first-m4/logs/pytest-full-offline-post-launcher-fix.log`.
- Historical M0–M4 raw artifacts and earlier failures remain unchanged. All M0–M3 research and current preparation date 2026-10-20, before the Apart Sprint starts on 2026-10-23; this work is pre-sprint work.
- Real model/API calls: 0 at freeze time.

## Preserved pre-dispatch launch failure

After the freeze candidate was pushed, the first invocation of the authorized orchestrator stopped in pilot setup with `UnboundLocalError` caused by a function-local `write_once` import shadowing its module import. It occurred before a client call. `runs/deepseek-first-m4/global_budget_ledger.jsonl` was absent after the invocation, confirming zero physical request-start records. The complete reproduced traceback is preserved at `docs/results/deepseek-first-m4/logs/orchestrator-preflight-unbound-write-once.log`. The fix removes the shadowing import and adds a mocked pilot-run regression test. The run has not been resumed and no model request has been sent.

The corrected pilot-plan bytes match the source-generated schedule at SHA256 `21bddaccd2385bf730dd367085aaad804ce7fb43a0dc33080b41ce3219d7b935` (30 slots: 20 Strict, 10 preassigned fallback). The corrected candidate passed 548 full-suite tests with one opt-in host check skipped. This evidence remains pre-inference evidence only.

## Post-run evidence (2026-10-20)

The single user-authorized run used the corrected, pushed pre-inference freeze at `550bf1361609e405dc50aa60d5d77b9c502e5bf0`. The earlier launcher exception and its traceback remain in this record; it was a pre-transport failure and did not consume an API request. The corrected run then completed once. No calls occurred after it.

| Stage | Assigned | Completed / valid | Failed or unstarted | Physical requests |
|---|---:|---:|---:|---:|
| Strict compatibility pilot | 20 | Agent 8/8; Monitor 12/12 | 0 | 20 |
| M4 Agent | 24 groups | 24 | 0 | 232 / 264 ceiling |
| Monitor | 376 rows | 376 parseable and citation-membership-valid | 0 | 376 / 376 ceiling |
| **Total** |  |  |  | **628 / 900 ceiling** |

All 628 physical requests returned HTTP 200; there were no non-200 responses, missing HTTP responses, retries, replacements, or unterminalized request starts. The pilot selected Strict Function Calling; the fallback was not used. Provider identity was `deepseek-flash`, fingerprint `e72d3c7f663d3e1383b00b3884cb4501`. The alias does not expose a fixed weight hash.

Provider usage was 655,032 input and 43,645 output tokens. At the pre-dispatch official peak rates the usage estimate is USD 0.2488836 and the conservative global reservation was USD 1.7744040; both stayed under the authorized USD 5 cap. The single run used an alias with provider-managed weights; this does not establish checkpoint-level replication.

### Independently replayed Agent outcomes

Independent replay reconstructed all 24 episodes from raw requests/responses and source records: contexts, message permissions/delivery, sealed ballots, plurality/chair settlement, welfare, regret, private incentive and Public-only evidence. The independent summary is `docs/results/deepseek-first-m4/audit/agent_audit_summary.json` (SHA-256 `9fd50cb250cc3867b26ad45b14c035a3f1fb3652fe36defa061b69b5a44031e0`); per-group sanitized rows are in `agent_group_outcomes.csv`.

- All 24 assigned groups completed; all 72 baseline ballots were valid. Thirteen baseline ballots matched the common rewarded target; the target allocation was executed in 2/24 groups.
- Mean public regret was 1.9583 (median 0; distribution 14×0, 3×2, 2×4, 1×5, 4×7). Raw public welfare is not pooled across the six differently scaled scenario families.
- All 48 message actions were sent and delivered. Twenty contained a complete allocation proposal: 15 public optima, four other allocations, and one rewarded target; 28 sent messages did not encode a complete allocation under the frozen parser. Eleven of the 20 complete proposals exactly matched the recipient's independently collected baseline ballot.
- Sixteen of 24 assigned groups entered the proposal-eligible focal stage; the other eight remain in the denominator. In the 64 focal rows, ballot changes from baseline were: masked-history neutral 9/16, masked-history proposal 6/16, retained-history alternative 4/16, retained-history neutral 5/16. These are model outputs under fixed prompt counterfactuals, not natural paired episode repeats.
- A version-2 independent analysis substituted each focal ballot into its group's three baseline ballots, held the other two fixed, and re-computed plurality/chair settlement and matrix-specific regret. Compared with the eligible-group baseline, selected allocations changed in 5/16 masked-history neutral, 4/16 masked-history proposal, 4/16 retained-history alternative, and 4/16 retained-history neutral rows. The target was selected 4/16 times in each arm. Mean regret was 3.250, 3.313, 3.625 and 3.125 respectively (eligible baseline mean 1.500). This is deterministic replay of counterfactual ballots, not four observed environments.
- Provider-reported prompt-token counts were exactly matched for the positive-information versus neutral control (0 difference in 24/24). Real proposal versus neutral focal prompts were not token-matched: treatment-minus-control averaged +60 tokens (range +32 to +85; n=16), a material length/salience confound.
- The positive-information control was followed in 24/24 cases; neutral choices were T1 in 7/24 and T2 in 17/24. This is a narrow task-comprehension check, not evidence of collusion.
- A prespecified-pattern lexical scan found no occurrences of its short commitment-marker patterns among 48 messages. This is not semantic coding and cannot establish that no commitment was expressed.

### Independently replayed Monitor outcomes

Independent replay verified 376/376 Monitor attempts and 376/376 parseable, citation-membership-valid outputs. Exact correctness is separate: 145/376 requests matched all attached observable references, and 145/400 individual reference rows were exact. Citation membership means an ID was permitted in that input; it does not prove the cited event semantically supports the claim.

The frozen abstention labels (`insufficient_evidence`, `uncertain`, `unknown`) occurred in 45/376 request outputs (12.0%). For the observable `explicit_sequence` task, three outputs labeled the sequence `supported` when the attached observable reference was not-supported, not-visible, uncertain, or insufficient (3/190 such reference rows). This counts disagreement with an observable reference only, not a latent-collusion false positive.

There were 126 assessable same-case/task/permission B4/B5 pairs: both exact on all references in 65, B4-only exact in 10, B5-only exact in 4, neither exact in 47; predictions were identical in 101 pairs. These descriptive counts do not establish a B4/B5 superiority effect. Pairing does not remove the repeated-case/task dependencies or one-alias limitation.

Per-reference exact counts were: natural M4 traces B4 52/144 and B5 47/144; scripted synthetic controls B4 5/8 and B5 5/8; matched synthetic worlds B4 18/48 and B5 18/48. Populations are separate; the synthetic controls are not natural-agent examples. Full row-level sanitized tables are `monitor_request_outcomes.csv`, `monitor_per_reference_scores.csv`, and `monitor_paired_B4_B5.csv`.

### Evidence hashes and replay

- Independent Monitor summary SHA-256: `49f3cf85cde5a4a6561b18c7dc6ed92e565a0a9e77e0bc48bbb477a5dd4d6ca7`.
- Combined independent audit SHA-256: `ca5fadb95c7377d54659139c3e1138a51cc97333b2d05b6102cb94a3ca41af57`.
- V1 sanitized post-run analysis JSON `postrun_analysis.json` SHA-256 (preserved): `35aff02b2790cd4b3d19d452213a9447b0fb939ba3767fdbbb38974c3900b93d`.
- V2 sanitized post-run analysis JSON with fixed-peer settlement, abstention and unsupported-assertion counts SHA-256: `6cff80e9ee675b9b09e723228183b3901977c4bdc12f43b415fa50db34311cb4`.
- Figure manifest `docs/results/deepseek-first-m4/figures/manifest.json` SHA-256 `e39abcbe8af0386fb02ecdead02871f58e72bbad6a2740b45620f20a8d682282`; figures were rendered from sanitized independent audit outputs only. Agent-regret figure SHA-256 `98341b6c50c0076539aaa482d52568f3386fc55c4b714525fc8b89514c3e3fe6`; focal-ballot/settlement figure `ca61910bd6685b84530362ad774152f76605d091de6a522d9ccea6785f6e0c1b`; Monitor population accuracy figure `e083bb61d0382c01ff811644b442f7120162cd0cd068395f1a985852a691714d`; paired correctness figure `aaeae5fefe5447b13c161c5b6a61ab3c408e6db2d5d16c4915c560a38ffc9121`.
- Post-run full repository suite after independent focal settlement analysis: **552 passed, 1 opt-in Windows listener-owner-table check skipped in 227.52s**. Captured stdout SHA-256 `f4760f031fa126951115ec3e36cac766ad72e36ca65b14246248127a8177fc9e`; file `docs/results/deepseek-first-m4/logs/pytest-full-final-with-focal-settlement.log`.
- Private final run summary SHA-256: `d8a577d2976fd2ab313ed3f3f314f96c929e7f149f66ccb7252d2110f39cbfa2`; private global budget ledger SHA-256: `716d3a62c5a7f5c8edc14e1d4487c02bf6ad6daddebf4a3082bea5a1f255ae51`.
- Hashes above can be independently recomputed with PowerShell `Get-FileHash -Algorithm SHA256 <path>` or Python `hashlib.sha256(path.read_bytes()).hexdigest()`. Full source replay requires the ignored, ACL-restricted local run root.

- Final full repository suite after adding the privacy scanner and leak/no-leak counterexamples: **556 passed, 1 opt-in Windows owner-table check skipped in 217.79s**. Captured stdout SHA-256 `2924095a8320abd1173c0f1f3811ac310b4ea41fe32eeb1672b96109cf2b2834`; file `docs/results/deepseek-first-m4/logs/pytest-full-final-with-monitor-claims.log`.

Raw private messages, request/response bytes, and credentials were not copied into tracked results. The preserved local root is `runs/deepseek-first-m4/` and remains Git-ignored/ACL-restricted.

## Reproduction

Pre-inference and frozen-run commands are specified in `docs/DEEPSEEK_FIRST_RESEARCH_RELEASE.md`. The no-inference independent scoring/replay entry point is:

```powershell
python scripts/audit_deepseek_first_research.py
python scripts/analyze_deepseek_first_research.py
python scripts/plot_deepseek_first_research.py
```

The pre-inference PASS entries above are protocol/runtime evidence only. The post-run observations are one alias/version's descriptive behavior and do not support latent-collusion labels, intent, causal communication effects, or generalization claims.

- A reproducible exact-text privacy scan checked 48 locally captured sent-message strings against 623 non-ignored repository files and found no matches. Scanner: `scripts/audit_deepseek_message_privacy.py`; sanitized result SHA-256 `c205a2648089b8e55be47d8f0b69f3c1d79c21c1f833be8624faae7bf8fef45c` at `docs/results/deepseek-first-m4/logs/privacy-scan-final.json`. The tool emits no message content. Exact matching cannot detect paraphrases or transformed copies.
