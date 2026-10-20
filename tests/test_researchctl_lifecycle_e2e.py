from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _ref(path: Path, relative: str) -> dict[str, str]:
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _walk_refs(value):
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            yield value["path"]
        for child in value.values():
            yield from _walk_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_refs(child)


def test_researchctl_zero_call_register_close_sync_audit(tmp_path: Path):
    """Exercise the real CLI lifecycle in an isolated copy, without API dispatch."""
    sandbox = tmp_path / "repo"
    for relative in (
        "scripts/researchctl.py",
        "research/frozen_eval/evaluate_cycle.py",
        "research/frozen_eval/evaluate_cycle_v2.py",
        "research/state.json",
        "research/budget.json",
        "research/hypotheses.json",
        "research/memory.json",
        ".gitignore",
    ):
        destination = sandbox / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    shutil.copytree(ROOT / "research/handoffs", sandbox / "research/handoffs")
    for directory in ("research/experiments",):
        source = ROOT / directory
        destination = sandbox / directory
        if source.exists():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            destination.mkdir(parents=True, exist_ok=True)
    (sandbox / "research/authorizations").mkdir(parents=True, exist_ok=True)
    budget_copy = sandbox / "research/budget.json"
    isolated_budget = json.loads(budget_copy.read_text(encoding="utf-8"))
    isolated_budget["authorization"] = {
        "status": "none", "approval_id": None, "scope": None,
        "authorized_experiment_ids": [], "max_model_calls": 0,
        "max_external_cost_usd": 0.0, "source": None,
        "approved_at_utc": None, "expires_at_utc": None,
    }
    isolated_budget["project_limits"] = {"max_model_calls": 0, "max_external_cost_usd": 0.0}
    budget_copy.write_text(json.dumps(isolated_budget, indent=2) + "\n", encoding="utf-8")

    registry_sources = [
        sandbox / "research/state.json", sandbox / "research/budget.json",
        sandbox / "research/hypotheses.json", sandbox / "research/memory.json",
        *sorted((sandbox / "research/handoffs").glob("*.json")),
    ]
    reference_paths = set()
    for registry_source in registry_sources:
        reference_paths.update(_walk_refs(json.loads(registry_source.read_text(encoding="utf-8"))))
    for relative in sorted(reference_paths):
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT.resolve()) or not source.is_file():
            continue
        destination = sandbox / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)

    frozen = sandbox / "research/e2e_frozen_input.json"
    frozen.write_text(json.dumps({"fixture": "zero-call lifecycle only", "calls": 0}) + "\n",
                      encoding="utf-8")
    hypotheses = json.loads((sandbox / "research/hypotheses.json").read_text(encoding="utf-8"))
    candidate = next(item for item in hypotheses["candidates"]
                     if item["hypothesis_id"] == "observable-evidence-boundary")
    experiment_id = "LIFECYCLE-E2E-01"
    prior = _ref(sandbox / "research/handoffs/DEEPSEEK-FIRST-RESEARCH-01.json",
                 "research/handoffs/DEEPSEEK-FIRST-RESEARCH-01.json")
    frozen_ref = _ref(frozen, "research/e2e_frozen_input.json")
    prereg = {
        "schema_version": 2,
        "experiment_id": experiment_id,
        "title": "Zero-call research registry lifecycle validation",
        "evidence_class": "offline_reanalysis",
        "hypothesis_id": candidate["hypothesis_id"],
        "research_branch_id": "registry-lifecycle-validation",
        "selection_rationale": "Exercise registry integrity only; no scientific observation is generated.",
        "research_question": "Can a zero-call cycle be registered, closed, synchronized, and audited without changing its evidence class?",
        "hypothesis": candidate["hypothesis"],
        "competing_explanations": candidate["competing_explanations"],
        "prior_evidence": [{**prior, "claim": "Frozen candidate registry used for lifecycle validation."}],
        "protocol": {
            "sample_selection": "One synthetic fixture used only to exercise CLI record lifecycle.",
            "intervention": "Register and close a zero-call cycle in an isolated repository copy.",
            "held_constant": ["No model/provider calls", "All source evidence class and hypothesis text"],
            "primary_outcome": "CLI registration, closure, memory sync, and audit complete with zero calls.",
            "denominator": "One engineering lifecycle run; not a scientific sample.",
            "success_gate": "All four CLI operations succeed and audit reports zero new calls and cost.",
            "failure_gate": "Any CLI operation fails or any nonzero call/cost is recorded.",
            "ambiguous_gate": "Not applicable; this is an engineering lifecycle check.",
            "analysis_plan": "Read the CLI exit codes and final audit totals; do not interpret as hypothesis evidence.",
            "reproduction_command": "pytest -q tests/test_researchctl_lifecycle_e2e.py",
            "runtime_identity": "Python subprocesses executing copied repository CLI; provider dispatch is absent.",
            "frozen_inputs": [frozen_ref],
        },
        "budget": {"max_model_calls": 0, "max_external_cost_usd": 0.0,
                   "max_wallclock_minutes": 2},
        "authorization": {"approval_required": False, "approval_id": None,
                           "scope": "zero-call registry lifecycle test only"},
    }
    prereg_path = sandbox / "research/preregistration-e2e.json"
    prereg_path.write_text(json.dumps(prereg, indent=2) + "\n", encoding="utf-8")

    def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "scripts/researchctl.py", *args], cwd=sandbox,
                              text=True, capture_output=True, check=False, timeout=30)

    registered = run_cli("register", "research/preregistration-e2e.json")
    assert registered.returncode == 0, registered.stdout + registered.stderr
    output = sandbox / "research/experiments" / experiment_id / "lifecycle-output.json"
    output.write_text(json.dumps({"operations": ["register", "close", "sync-memory", "audit"],
                                  "calls": 0, "cost_usd": 0.0}, sort_keys=True) + "\n",
                      encoding="utf-8")
    closure = {
        "schema_version": 2,
        "experiment_id": experiment_id,
        "evidence_class": "offline_reanalysis",
        "decision": "PASS",
        "results_summary": "The registry lifecycle completed in an isolated copy with zero calls.",
        "denominator_summary": "One engineering lifecycle validation; no scientific cases.",
        "scientific_update": "No scientific hypothesis was tested or updated.",
        "actual_model_calls": 0,
        "actual_external_cost_usd": 0.0,
        "actual_wallclock_minutes": 0,
        "failures_retained": True,
        "review_mode": "adversarial_self_review",
        "review_finding": "The result validates CLI state transitions only; it does not validate research claims.",
        "review_artifact": {},
        "outputs": [_ref(output, f"research/experiments/{experiment_id}/lifecycle-output.json")],
        "next_action": "Continue offline candidate review; this test grants no provider dispatch.",
        "next_action_evidence_class": "offline_reanalysis",
        "next_action_max_model_calls": 0,
        "next_action_max_external_cost_usd": 0.0,
        "new_uncertainty_reduced": False,
        "approval_required_for_next_action": False,
        "scientific_outcome": "INCONCLUSIVE",
        "outcome_rationale": "Engineering lifecycle validation supplies no scientific evidence.",
        "belief_updates": [{
            "claim_id": "observable-evidence-boundary",
            "outcome": "UNCHANGED",
            "statement": "Zero-call CLI behavior does not change the evidence-boundary hypothesis.",
            "what_changed": "No scientific observation was collected.",
            "remaining_alternatives": "All scientific explanations remain unresolved.",
            "evidence_refs": [],
        }],
        "material_update": {"claim_id": "observable-evidence-boundary",
                            "what_changed": "No scientific material update.",
                            "remaining_alternatives": "The CLI lifecycle says nothing about the research hypothesis.",
                            "evidence_refs": [], "independent_critic_confirmed": False},
        "next_action_kind": "continue_offline",
        "authorization_id": None,
        "model_request_ledger": None,
    }
    closure_path = sandbox / "research/closure-e2e.json"
    closure_path.write_text(json.dumps(closure, indent=2) + "\n", encoding="utf-8")
    closed = run_cli("close", "research/closure-e2e.json")
    assert closed.returncode == 0, closed.stdout + closed.stderr
    synced = run_cli("sync-memory")
    assert synced.returncode == 0, synced.stdout + synced.stderr
    audit = run_cli("audit")
    assert audit.returncode == 0, audit.stdout + audit.stderr
    report = json.loads(audit.stdout)
    assert report["integrity_check"] == "PASS"
    assert report["registered_cycles"] == 1
    assert report["new_iteration_usage"]["model_calls"] == 0
    assert report["new_iteration_usage"]["external_cost_usd"] == 0.0
    print(json.dumps({
        "lifecycle": "register -> close -> sync-memory -> audit",
        "exit_codes": {"register": registered.returncode, "close": closed.returncode,
                       "sync_memory": synced.returncode, "audit": audit.returncode},
        "integrity_check": report["integrity_check"],
        "registered_cycles": report["registered_cycles"],
        "model_calls": report["new_iteration_usage"]["model_calls"],
        "external_cost_usd": report["new_iteration_usage"]["external_cost_usd"],
        "scientific_validity": report["scientific_validity"],
    }, sort_keys=True))
