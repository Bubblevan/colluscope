# M2-V2 Repair-02 Plan

## Evidence that motivates this change

Repair-01 produced three valid outputs out of ten for each candidate. Its all-violation diagnostics show that the remaining failures are structured, not syntax failures:

- In both full candidates, `action_only + privileged_audit` still made all five message-dependent claims as if uncertain, even though the selected row forces those fields to `not_visible`.
- In `text_only + privileged_audit`, both public-action claims were populated even though action events were omitted; in `text_only + public_only`, both action and message claims were populated despite both omissions.
- `raw_fusion + privileged_audit` added `messages_not_in_view`, and `structured_without_findings + privileged_audit` called a non-empty visible stream empty.
- `structured_evidence + privileged_audit` repeated an event ID within the same `action_concordance` citation list.
- Compact C3 missed message citations on two privileged rows and a second ballot citation on a public-only row.

Repair-01 and the original gate remain immutable. The observed identical C1/C2 outputs again do not identify whether response-format choice has any effect; schema format and deterministic seed differ together in the payload.

## Change and falsifiable claim

Repair-02 replaces the prose-first permission guidance with an explicit branch table containing the forced value for each claim family, sequence status, and required omission reason. It instructs the model to select a row from the two labels before reading evidence and to copy forced values first. It separately states that each event ID may appear at most once per claim, and keeps the exact M/P citation requirements. Full and compact citation encodings remain as originally frozen.

Falsifier: any invalid response among the candidate's ten fixed requests. The 10/10 gate, candidate order C1 → C2 → C3, evidence, task, schema, parser, runtime, sampling, and 512-token output cap are unchanged. The new system prompts have been GGUF-tokenized against every fixed request: maximum 2,620 tokens (full) and 2,497 (compact), all below 3,072; prompt plus 512 output remains below the 4,096 context limit.

## Before inference

1. Commit and push this plan, candidate registry, prompts, and regression tests.
2. Run `--prepare-preflight` to create 30 requests with zero calls.
3. Run `--verify-inputs`; require `PASS_M2_V2_PREFLIGHT_INPUT_AUDIT`, 30 unique payloads, all 1,450 V1 hashes verified, no model call, and no permission leak.
4. Only then run `--preflight`, at most 30 HTTP attempts and no retries.
5. Independently audit every raw response. If all candidates fail 10/10, proceed to repair-03 only if cumulative attempts remain ≤120; never edit this run.

After the original 30 and repair-01's 30 attempts, repair-02 has an available cap of 30 and cumulative maximum 90. Formal inference remains prohibited until an independently verified `PASS_INTERFACE` (10/10). The formal 1,000-evaluation run retains the 95% F1 validity gate.
