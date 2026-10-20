# Independent Post-run Critic Review

**Reviewer:** isolated Codex subagent `/root/postrun_critic`
**Review mode:** independent desk review of the sanitized packet and cited artifacts. The reviewer did not inspect the protected raw run, make API calls, or independently replay raw bytes. It is an independent scientific critique, not a second integrity audit.

## Verdict

**`INCONCLUSIVE` for the primary mechanism claim.** The preregistered package-dominant direction was not met: Public→Neutral changed 12/24 labels, while Neutral→Original changed 20/24. The observed data establish finite response sensitivity across the frozen request variants, but not which input feature caused it.

## Main counterexamples and limits

- The exact repeated Public/Neutral profile produced different transitions and is excluded from the registered deduplicated directional sensitivity. The remaining pairwise unique-profile counts do not restore a preregistered directional pattern.
- Public→Neutral adds 178 provider-reported prompt tokens in every case. Neutral→Original differs by +113 to +383 tokens (mean +184.625), so message wording is not isolated from length and salience.
- A2's arithmetic aid made the deterministic public-harm result calculable from visible inputs and yielded 39/40 exact labels. This is not an independent LLM reasoning benchmark. Reversing both prompt label order and the tool enum changes a bundled request form, so it does not isolate enum order.
- The post-hoc historical-label comparison matched current Public-only on 7/24 and Privileged-original on 22/24 cases. This asymmetric agreement does not explain the prior 20/24 contrast.

## Addendum: exact-request non-repeatability

The follow-up review considered the independent exact-byte audit. For the same 24 cases in each view, historical and current request bodies were byte-identical, and the reported system fingerprint was identical for all 48 pairs. Labels matched on 7/24 Public-only cases and 22/24 Privileged-original cases. Within the current campaign, one repeated exact Public/Neutral input-pair profile also varied.

The reviewer concluded this demonstrates finite non-repeatability for these observations, despite temperature 0 and the same reported fingerprint. It does not establish why outputs varied, prove hidden backend state was identical, or imply immutable weights. The similar marginal historical/current change totals (20/24 versus 19/24) are not case-level replication: only 7/24 cases had the same ordered transition. Historically the main transition was `insufficient_evidence`→`absent`; currently it was `present`→`absent`.

This weakens causal attribution from single-call cross-view contrasts. It does not erase the descriptive results or prove response variability explains the entire asymmetry. The reviewer considers the no-call paired recurrence analysis sufficient for now; any attempt to separate response variability from view effects would require a new preregistered repeated-call design and separate authorization.

## Artifacts

- Blind review packet: `docs/results/research-sprint-20261021/campaign-postrun-critic-packet.md`
- Independent raw replay: `docs/results/research-sprint-20261021/m4-b5-context-sensitivity-independent-audit.json`
- Sanitized row data: `docs/results/research-sprint-20261021/m4-b5-context-sensitivity-independent-rows.csv`
