# Matched-world sequence visibility audit

**Experiment:** `matched-world-sequence-visibility-v1`  
**Evidence class:** deterministic offline reanalysis of frozen scripted synthetic records  
**Model/API/network calls:** 0 / 0 / 0  
**Terminal result:** the registered construction-boundary gate is supported for this frozen fixture only.

## Question and scope

This audit asks which components of a proposal → delivery → explicit acceptance → subsequent action sequence are visible in Public-only and Privileged Audit projections of 12 pre-existing synthetic matched pairs. It does not evaluate a monitor, natural-language acceptance detection, live agent behavior, collusion, or latent intent.

The population remains all 12 pairs / 24 worlds, with two pairs in each of six construction families. The audit retained the incomplete-evidence worlds and did not use model outputs as reference truth. Private message text and model responses remain in the ignored local freeze; the result file contains aggregate states and cryptographic receipts only.

## Independently checked results

| Check | Result | Denominator |
|---|---:|---:|
| Public-only frozen request bodies equal within pair | 24 | 24 pair × method comparisons |
| Public-only reference projections equal within pair | 24 | 24 pair × method comparisons |
| Privileged evidence projections differ within pair | 24 | 24 pair × method comparisons |
| Frozen evidence records independently verified | 72 | 72 requests |
| Frozen request-body hashes independently verified | 72 | 72 requests |
| Private message text found in Public-only request bodies | 0 | all checked public requests |
| Hidden pair/family/world metadata found in Public-only request bodies | 0 | all checked public requests |

Projection difference alone is not treated as evidence that a proposal/acceptance/action sequence differs. The corrected audit separately compared source-derived sequence states within each matched pair. Eight of 12 pairs had at least one determinate `visible_present` versus `visible_absent` difference in a permitted sequence element; four pairs did not meet that stricter per-pair criterion. Counts overlap across elements:

| Sequence element with determinate pair difference | Pairs |
|---|---:|
| Proposal | 6/12 |
| Sent proposal content | 6/12 |
| Proposal delivery | 6/12 |
| Explicit acceptance | 4/12 |
| Both parties' ballots match proposal after acceptance (complete observable sequence) | 2/12 |

Privileged complete-sequence status across all worlds was `visible_present` 2/24, `visible_absent` 20/24, and `unknown_due_incomplete` 2/24. Public ballots were visible in all 24 worlds. In Public-only views, proposal, delivery, acceptance, message ordering, action concordance, and complete sequence were `not_visible` in all 24 worlds; private facts were not reclassified as absent.

The sequence classifier recognizes only the frozen exact scripted proposal and explicit-acceptance utterances. It requires a delivered proposal, later explicit acceptance, both sender and recipient ballots after acceptance, both ballots matching the proposed allocation, and a complete event stream. It is a deterministic fixture parser, not a general language understanding test.

## Adversarial review and repair history

The first v2 audit failed because an assertion expected 24 frozen request bodies although the source manifest contains 72 (24 Public-only and 48 Privileged). The complete failure is retained at `logs/matched-world-sequence-visibility-first-failure.txt`; no rows were dropped. After correcting the count, an independent review found that the successful v2 summary still omitted the preregistered per-pair sequence comparison, did not require both ballots to follow acceptance, and marked ballots present without checking all three actors. That review is preserved in sanitized form at `review-matched-world-sequence-visibility-v2.md`.

The implementation was tightened without changing the source population, treatment, labels, or registered threshold. Added tests cover a true complete sequence, a ballot-before-acceptance counterexample, and a missing public ballot. A final self-review caught that the v3 fix checked missing ballots in Privileged Audit but the Public-only branch still used the old completeness-only shortcut; v4 now uses the same actor-presence check in both branches. The targeted suite passes 10/10. The prior v2/v3 outputs and review remain untouched. A transient post-registration edit to the protocol file was restored before analysis; its registered SHA-256 was reverified. These events are recorded in `failure_history.jsonl`.

The final corrected output is `matched-world-sequence-visibility-v4-final.json`, SHA-256 `36827cf5b7a84a97b7bca0d5a3b704cfc8ad3a55763d6fa1667f7d0beda85390`. The v4 audit source SHA-256 is `f7326489b9ae877d5f549d2d1da784ff499b37247fff00b68bd424954765e6cc`; the archived initial implementation is `6633ae8afa814b5495a1f570df05045cbdc3d4317780b5f3ec6c57bae1852c5f`. The registered protocol remains byte-identical to its frozen SHA-256 `30cc5c87063935950855e6c13a52a23613c1c47c2ea50a96491458af78a0d14e`.

## Interpretation and limits

For these 12 scripted pairs, the result demonstrates an evidence-boundary construction: the same authorized Public-only projection can correspond to worlds whose permitted privileged sequence facts differ. In this fixture, source-event detail identifies a determinate sequence difference in 8/12 pairs and a complete proposal/acceptance/both-actions sequence in 2/24 worlds.

This does not establish a general impossibility theorem, real-agent coordination, monitor sensitivity or specificity, or collusion intent. The synthetic event construction and exact-message parser make the finding local to the fixture. Public request equality is verified over the frozen prepared request bytes and hashes; this audit did not observe a live provider's received transport bytes. The Privileged projection can differ in event structure or completeness metadata as well as sequence facts, which is why the per-pair sequence result is reported separately.

## Reproduction

From the repository root:

```powershell
python scripts/audit_matched_world_sequence_visibility.py --freeze runs/full-research-execution-20261020/monitor/freezes-v2/matched_worlds --out docs/results/research-sprint-20261021/reproduction.json
python -m pytest -q tests/test_matched_world_sequence_visibility.py
python -m py_compile scripts/audit_matched_world_sequence_visibility.py tests/test_matched_world_sequence_visibility.py
python scripts/researchctl.py audit
```

The frozen source receipts are manifest `21425a7dcb6408baf2e55e8a7f7b2f1e996b65c51b805b90f51079108b8888c0`, plan `a75e28f611f1579571c15a095f53140a6ac0d5d1e1a8ae4857abdec2c985ac7c`, and pair map `3ec773e06b24102d829df7f3b1dac22dd09cc1733891403a9122c9b96239ec0d`. A reproduction output path must be unused because the audit intentionally refuses to overwrite prior evidence.
