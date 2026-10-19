# M2-V2 Repair-02 Evidence

**Decision:** `NO_GO_INTERFACE`; preserve the third and final compatibility repair for a targeted attempt. Formal 1,000-row inference remains gated and has not started.

## Freeze and no-call audit

- Repair-02 source freeze: `5db76c38b0932d875212929ce1bb076c8d962b9c`.
- Candidate registry SHA-256: `53d396f0285e5bf9dbe89ec22a1bf29b5f554d4f83b85e2e3f8c5ede07a52076`.
- Registry freeze SHA-256: `f49571cd3f8a7ea075bb7401c4b47193bd47e3038b84d487893c00725ab2f5ac`.
- Prepared-input manifest SHA-256: `21cd5390cf464449153bbb30db4ce05ab9e88c5c53d0f3150feae50312671bc1`.
- Independent no-call auditor: `PASS_M2_V2_PREFLIGHT_INPUT_AUDIT`; 30 unique requests, 10 per candidate, zero prior calls, 9 ACL-verified directories, no hidden treatment keys, 12 privileged message-bearing inputs, and all 1,450 V1 artifacts intact.
- Maximum local prompt: 2,620 tokens for full and 2,497 for compact; all 30 inputs fit the 3,072-token input limit and the 4,096-token context with 512 output tokens.

## Local model run

The same local Qwen3-8B Q4_K_M checkpoint (`d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`), llama.cpp server (`3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`), runtime bundle (`9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759`), tokenizer (`06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f`), chat template (`57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361`), sampling, authenticated `127.0.0.1:8081` endpoint, and strict contract were used. No external or paid inference occurred. Server process was terminated and its temporary API key removed.

| Candidate | Strict valid | Invalid | Result |
|---|---:|---:|---|
| C1 full / JSON Schema | 6/10 | 4/10 | Fail |
| C2 full / JSON object | 6/10 | 4/10 | Fail |
| C3 compact / JSON Schema | 5/10 | 5/10 | Fail |

Across the 30 outputs, JSON parse, root shape, core enums, and `finish_reason=stop` were all valid. The first-rejection distribution was view/permission 8, evidence reference 1, other contract 4, and valid 17. The best individual fixed-cell rates were `action_only + public_only` 3/3, both structured-evidence permissions 3/3, `structured_without_findings + privileged_audit` 3/3, and `text_only + public_only` 3/3. This is still only interface validity on one F1 episode.

## Counterexamples left by repair-02

- In `action_only + privileged_audit`, all three candidates could add the inapplicable reason `actions_not_in_view`; actions are visible in this view.
- In `text_only + privileged_audit`, C1/C2 set `action_concordance=not_visible`, but the contract requires `not_assessable` because messages are visible while ballots are omitted.
- In `raw_fusion + public_only`, C1/C2 treated a hidden message claim as absent/uncertain instead of `not_visible`; in `structured_without_findings + public_only`, the same pair regressed to `uncertain` for all claim values.
- C3's compact citations included whitespace in the claim prefix, producing malformed references on the raw-fusion privileged and text-only privileged cases. It also lacked two distinct P citations for public disagreement in one public-only case.
- The two full candidates again produced byte-identical assistant text in all ten matched tuples. Because the candidate payloads and deterministic seeds differ in their response-format fields, this remains an observation only; the cause is unidentified.

All overlapping violation diagnostics are exported without raw assistant or private message text in [`docs/results/m2_v2_repair_02/m2_v2_bad_case_diagnostics.csv`](results/m2_v2_repair_02/m2_v2_bad_case_diagnostics.csv). Each candidate received ten requests; total was 30 logical calls, 30 HTTP attempts, zero retries.

## Resources and hashes

- Server prompt tokens: 60,402; completion tokens: 5,169.
- Median latency: 3.600849 s; maximum: 4.916241 s.
- GPU samples: 107; maximum utilization: 100%; minimum free memory: 9,688 MiB.
- Request/response inventory: `f2fb3e654ada272f24f20bc0ac3f8323dcd2e07b51618472e2cf5f83d6d0ee01`.
- Decision: `d8b3355fa86c58f972ed72f7da04660d7e17ad7dbf1bd888c510b8e376035976`.
- Attempt ledger: `67592eb6e1daabc558e6e36b0ffdf52dc49d09a107c4163c4fee1a5a6a5cb11e`.
- Server log: `27d8e371d4d3de980e6bd2c3521588cb50bdd70fced283c2be8d34b6008b7980`.
- GPU samples: `c4d3f56e4febf0e715e5cee152213cbeb57eae46e5e8d444f49af5e6ba97623b`.

## Reproduction

```powershell
python scripts/run_m2_v2_repair.py --iteration 2 --prepare-preflight --out runs/m2-v2/recovery-20261019/repair-02
python scripts/run_m2_v2_repair.py --iteration 2 --verify-inputs --out runs/m2-v2/recovery-20261019/repair-02
python scripts/run_m2_v2_repair.py --iteration 2 --preflight --out runs/m2-v2/recovery-20261019/repair-02
python scripts/run_m2_v2_repair.py --iteration 2 --audit-results --out runs/m2-v2/recovery-20261019/repair-02
```

The repair-02 results improve strict interface validity over repair-01 (17/30 versus 9/30), but no candidate is close to the required 10/10 gate. The remaining authorized iteration will target only the listed branch and compact-citation errors; it will use the same fixed cases and threshold. No accuracy, generalization, or collusion claim follows from this run.
