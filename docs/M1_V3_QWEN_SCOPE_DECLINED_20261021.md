# M1 v3 Qwen Scope Decision — 2026-10-21

**Decision source:** direct user response to the exact-scope M1 v3 R3 approval question.

**User decision:** decline the proposed Qwen run; do not use Qwen. If model calls prove necessary, commit and push the offline stage first, then report interim status.

**Model calls after this decision:** 0.

**Experiment registration:** none.

**Decision status:** R3 Qwen execution candidate withdrawn; no replacement model or experiment is authorized by this response.

## Scope and preservation

The user declined the proposed 120-episode / 24-group local Qwen3 run. No episode, identity check, or other request was sent. The Qwen-specific R3 approval request and its hash-pinned review manifest remain unchanged as historical review artifacts; they are not an active run authorization. The selected research question (private-target reward × chat-stage package) is not itself rejected, but a future test would require a separately versioned protocol for an explicitly selected model and a new experiment-specific decision.

The prior DeepSeek approvals name completed, closed experiments. They cannot be transferred to a new Agent run. No DeepSeek Agent or Monitor inference is started here.

## Scientific interpretation

This is an authorization decision, not a scientific outcome. It supplies no evidence for or against the private-reward × chat-stage hypothesis. The historical M1 result and its limits remain as reported: the prospective Qwen corpus selected the target in 9/15 private-reward-plus-chat groups and 0/15 in each of three other factorial cells; this finite package contrast does not identify message semantics, communication causality, collusion, or intent. The model-specific R3 protocol cannot be treated as model-agnostic after its named checkpoint was declined.

## Next permissible work

Continue offline synthesis and prepare a model-specific proposal only if it addresses a live uncertainty better than existing evidence. Before any future model request, report the exact model, experiment, request and cost ceilings, runtime, privacy boundary, and termination condition. Do not register or dispatch from this historical R3 package.

## Offline verification

- R3 snapshot verifier: `PASS_M1_V3_REVIEW_SNAPSHOT_HASHES`; all 23 runtime inputs and 36 supporting review artifacts match; `approval_present=false`.
- Research registry audit: `PASS`; four historical cycles, zero open experiments, and 352 calls / USD 0.039167058 accounted to the two closed DeepSeek experiments.
- Machine receipts: `docs/results/research-sprint-20261021/qwen-scope-declined/scope-decision-audit.json` and the raw verifier/registry outputs beside it.
- No model or API request was made while recording this decision.
