# Sprint Results Draft — Offline Baseline Preparation

**Status:** draft of currently available evidence. No new Agent or Monitor inference has been run.

## Scope and evidence provenance

This draft reports only eight explicitly scripted synthetic evidence controls. They are software/scoring sanity cases, not model-generated behavior and not a sample of real or simulated LLM collusion. M0–M3 remain pre-sprint historical work. The Colosseum compatibility branch is excluded from detector comparisons. Ignored raw M1-100, M1-P0, and M2-V3 run directories were not present on this host; the versioned M2 synthesis is context only and was not replayed as a clean baseline.

The monitor outputs for B2–B5 are **NOT RUN**. No performance estimate for a language model is available. The table below is computed from the scripted case generator, independent event replay, B0/B1 deterministic baselines, and the frozen scorer.

## Offline sanity table

| Baseline | Permission | Assessable task rows | Exact facts correct | Hard-negative sequence false assertions | Explicit-sequence positive recognized | Appropriate abstention |
|---|---|---:|---:|---:|---:|---:|
| B0 Always-negative | Public-only | 7 | 2/7 | 0/4 | Not estimable (0 visible positives) | 33/33 |
| B0 Always-negative | Privileged Audit | 35 | 16/35 | 0/4 | 0/2 | 5/5 |
| B1 Deterministic replay | Public-only | 7 | 7/7 | 0/4 | Not estimable (0 visible positives) | 33/33 |
| B1 Deterministic replay | Privileged Audit | 35 | 35/35 | 0/4 | 2/2 | 5/5 |
| B2 Text-only LLM | Both permissions | — | **NOT RUN** | **NOT RUN** | **NOT RUN** | **NOT RUN** |
| B3 Action-only LLM | Permission-invariant | — | **NOT RUN** | **NOT RUN** | **NOT RUN** | **NOT RUN** |
| B4 Raw Fusion LLM | Both permissions | — | **NOT RUN** | **NOT RUN** | **NOT RUN** | **NOT RUN** |
| B5 Evidence-aware LLM | Both permissions | — | **NOT RUN** | **NOT RUN** | **NOT RUN** | **NOT RUN** |

The primary three-part endpoint is a vector, not a single success score. B0's zero unsupported positives coincide with zero positive recognition under Privileged Audit; they do not establish a useful auditor. B1 is a deterministic reconstruction baseline evaluated on controls authored to exercise its codebook. Its 100% exact fact score is expected software validation and must not be described as LLM reasoning, detector accuracy, or generalization. There are only four hard-negative sequence cases in four scripted families, one family for both positive examples, and one family for each ambiguous/missing case. Cluster intervals are descriptive stability checks, not population uncertainty.

## Control-level observations

- The reference distinguishes proposal, post-delivery explicit acceptance, matching action, public harm, and visibility. An explicit proposal and matching ballots without observed acceptance remains a hard negative for the full sequence.
- A public common-reward announcement with parallel ballots and an independent harmful tie-break case prevent welfare loss, a shared target, or action similarity from serving as sequence labels.
- The positive controls include both a harmful and welfare-optimal allocation, so sequence status is not defined by welfare loss.
- Public-only views with no message authorization are not scored as ordinary missing-positive facts. A positive sequence assertion on unavailable evidence remains an unsupported claim.
- These are hand-authored controls. The proposed M4 behavioral information-use positive control has not been executed; its message tokenizer equality is still unverified.

## Claims not supported by this draft

These data do not establish latent intent, real-model coordination, auditor superiority, causal communication effects, calibration, or performance on unseen scenario families. They do not support a detector benchmark. B2–B5, any historical replay requiring absent raw files, and the M4 agent experiment remain unrun.

## Reproduction

```powershell
python scripts/prepare_sprint_baselines.py --output docs/results/sprint-baseline-v1
python scripts/verify_sprint_baselines.py
python -m pytest -q tests/test_sprint_baselines.py tests/test_sprint_controls.py tests/test_sprint_preparation.py tests/test_m4_scenarios.py
python -m pytest -q
```

The first command regenerates a local timestamped receipt. The second checks the generated files, hashes, 280-row request schedule, historical source inventory, and M4 scenario/split freezes without dispatching anything. Results are stored under `docs/results/sprint-baseline-v1/`.
