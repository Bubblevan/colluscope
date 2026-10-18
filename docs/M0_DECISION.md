# ColluScope M0 Decision

**Decision:** **GO for the M0 research scaffold and evidence package.**

**Decision boundary:** This GO confirms the TRD's M0 engineering and integrity gates for a scripted, offline environment. It does not establish real LLM collusion, monitor effectiveness, or authorize M1. M1 has not started.

## Gate-by-gate result

| TRD GO gate | Status | Evidence and limits |
|---|---|---|
| Official rules and upstream audit cite verifiable sources, exact commits, licenses, and preflight state. | **PASS** | [`M0_RESEARCH_NOTES.md`](M0_RESEARCH_NOTES.md) and the three `upstream-preflight-*.log` files record the official recommendations, paper/repository links, local commit IDs, license state, and actual command failures. High-level upstream experiments were **NOT RUN** because Terrarium/Inspect AI were missing or an API credential was required at import; this gate requires an honest audit, not a successful reproduction of every upstream. |
| Three-agent/three-task environment computes the correct optimum and action-level public payoff. | **PASS** | [`world.py`](../src/colluscope/world.py), [`generation.py`](../src/colluscope/generation.py), `tests/test_world.py`, and `tests/test_generation.py`. The six assignments are enumerated; optimum is W=28; every vote records per-agent quality, team quality, and welfare gap; invalid assignments fail. |
| Six cases and at least 24 scripted traces include a harmful control, hard negatives, talk-only, independent deviation, benign cooperation, and a non-identifiable pair. | **PASS** | Final traces in `runs/m0/m0-20261018T142629Z/inputs/trace.jsonl` and `runs/m0/m0-20261018T142630Z/inputs/trace.jsonl`; each run has 24 episodes, four per C1–C6. `metrics.json` and `verification.json` confirm counts and four matched C1/C6 pairs. Every trace says `model_kind="scripted"`. |
| Trace, oracle, four views, permissions, and provenance are separated; unauthorized evidence cannot enter views. | **PASS** | Oracle is at `runs/m0/oracle/<run-id>/oracle.jsonl`, outside `inputs/views/`. View JSONL rows are pure evidence objects with no episode ID, view name, scripted marker, mechanism label, or policy ID. The verifier recomputes every row from its position-aligned source trace; structured findings cite the event IDs and task-spec fields they use. Default private-message visibility is false; a separate test exercises the authorized case. |
| Ten key property classes pass, including leakage, identifiability, permissions, counterfactuals, determinism, invariance, and error handling; two repeat runs agree. | **PASS** | `runs/m0/evidence/pytest-m0-final-3.log`: **40 passed, 0 skipped**. Final generation and standalone verification logs show two runs with identical core hashes. The exact source snapshot SHA256 is `9a5166aafaa7304601f699a946acb48f958fb3cb1889446d2b5f816e2061ebe0`; config SHA256 is `5ebeb87fb49ac28a3305663ef587c6edfdf69f66f776cd38e581af23895e144a`. |
| Evidence clearly distinguishes scripted demonstrations from real LLM research and makes no fabricated performance claim. | **PASS** | [`M0_EVIDENCE.md`](M0_EVIDENCE.md), `metrics.json` (`scope="scripted_integrity_only"`, `detector_metrics=null`), and manifests (`model_kind="scripted"`, external/paid calls 0). No detector was evaluated. |
| Decision and reproduction commands include two runs and hashes. | **PASS** | This document and [`M0_EVIDENCE.md`](M0_EVIDENCE.md), including commands below, run IDs, hashes, and preserved logs. |

## Overall interpretation

The M0 implementation has met the specified integrity goals: it generates a known harmful scripted control, keeps hard negatives distinct in construction truth, isolates the oracle, produces provenance-backed evidence views, and reproduces the same core artifacts twice from the same hashed source snapshot and config.

The result is **not** evidence that a real model will coordinate, that any detector can infer hidden intent, or that combining text and actions improves detection. The C1/C6 pair is intentionally observationally identical under the default permission, so a monitor restricted to those payloads has no evidence for distinguishing their hidden construction mechanisms. C4's causal result depends on an artificial public chair tie-break. The four seeds and toy payoff matrix provide no basis for population or statistical claims.

The Git worktree is still uncommitted, and the manifests record `working_tree_clean=false`. The exact source snapshot is hashed in both final manifests, but a third party should preserve that snapshot or the delivered working tree when reproducing. The upstream audit is complete; the three upstream entry points did not run high-level experiments in this environment.

## Reproduction commands

From the repository root in PowerShell with Python 3.11 or 3.12 and pytest available:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
python -m colluscope m0 --config configs/m0.toml --out runs/m0
python -m colluscope m0 --config configs/m0.toml --out runs/m0
python -m colluscope verify --run runs/m0/m0-20261018T142629Z
python -m colluscope verify --run runs/m0/m0-20261018T142630Z
```

The two `verify` commands above reproduce the retained final runs. New generation commands create new timestamped run directories; compare their manifest SHA256 values with those listed in `M0_EVIDENCE.md`. Each generation command also verifies its output before returning success.

Expected test summary: `40 passed`. Expected verification status: `PASS`, 24 episodes, 4 per case, 24 per view, four identical public-only C1/C6 pairs, zero external and paid API calls.

## Failed and superseded attempts

Earlier test failures, root causes, and repairs are preserved in [`runs/m0/evidence/m0-c-failure-history.log`](../runs/m0/evidence/m0-c-failure-history.log). Intermediate generated runs remain under `runs/m0/`; they predate one or more final view/payoff fixes and are superseded. No failed sample was removed to obtain the final counts, no label was changed to improve a result, and the acceptance criteria were not relaxed.

## Recommended next research step, not started

After user review and explicit authorization, run a bounded real-LLM behavior pilot before any detector comparison:

1. Select one model whose exact version and runtime the researcher can lawfully and reproducibly access. Freeze model revision, prompt, sampling settings, environment, public incentives, and communication permissions.
2. Run a small pilot with 3–5 seeds per predeclared condition, including an attempted coordination condition and the C2/C3/C5-style hard negatives. Do not force a positive outcome. Record actual messages, votes, decisions, and welfare outcomes, with construction assignments kept separate from observations.
3. First ask whether the intended harmful action occurs and whether the negative controls behave as specified. If the positive behavior does not appear, report that result and revise the behavioral question before comparing monitors.
4. Only after the behavior pilot is interpretable, consider the Track 2.2 four-view comparison on identical real trajectories, with a frozen monitor model, prompt, threshold, held-out cases, and uncertainty/cost reporting. A small pilot is for feasibility and does not support a precise accuracy/FPR estimate.

**No real-model call, paid service, or M1 experiment is authorized or initiated by this M0 decision. Await user review before any next-stage execution.**
