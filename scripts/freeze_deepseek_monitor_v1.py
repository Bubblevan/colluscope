#!/usr/bin/env python3
"""Freeze exact DeepSeek Monitor requests from completed DeepSeek M4 evidence; no inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.deepseek_m4_v1 import canonical, now_utc, read_jsonl, sha, write_once  # noqa: E402
from colluscope.deepseek_monitor_v1 import build_plan, verify_plan  # noqa: E402
from scripts.local_llama_security import (  # noqa: E402
    restrict_private_directory_acl, verify_private_directory_acl,
)

RUN_ROOT = ROOT / "runs/deepseek-first-m4"
M4_RUN = RUN_ROOT / "agent"
MONITOR_ROOT = RUN_ROOT / "monitor"
FREEZE_ROOT = MONITOR_ROOT / "freeze-v1"
PLAN_PATH = FREEZE_ROOT / "plan.jsonl"
MANIFEST_PATH = FREEZE_ROOT / "manifest.json"
PHASES = ("m4_six", "m4_remaining", "scripted_controls", "matched_worlds")


def _acl(path: Path) -> dict[str, Any]:
    path.mkdir(parents=True, exist_ok=True)
    result = restrict_private_directory_acl(path) if not any(path.iterdir()) else verify_private_directory_acl(path)
    if result.get("verified") is not True:
        raise PermissionError(f"ACL verification failed for {path}")
    return result


def freeze() -> dict[str, Any]:
    if not (M4_RUN / "episodes.jsonl").is_file() or not (M4_RUN / "run_manifest.json").is_file():
        raise FileNotFoundError("DeepSeek M4 run evidence is missing")
    episodes = read_jsonl(M4_RUN / "episodes.jsonl")
    if len(episodes) != 24:
        raise ValueError("Monitor plan requires all 24 assigned M4 episode records")
    if not any(e.get("terminal_status") == "COMPLETED" for e in episodes):
        raise ValueError("no complete/assessable M4 behavioral episode exists; Monitor dispatch is blocked")
    from scripts.audit_deepseek_first_research import audit_agent_run
    agent_audit = audit_agent_run(M4_RUN, write_outputs=False)
    if agent_audit.get("status") != "PASS_INDEPENDENT_AGENT_REPLAY" or agent_audit.get("completed_groups") != 24:
        raise ValueError("independent raw Agent replay must pass all 24 groups before Monitor freeze")
    selection = json.loads((RUN_ROOT / "pilot/selected_interface.json").read_bytes())
    interface = selection["selected_interface"]
    _acl(MONITOR_ROOT)
    _acl(FREEZE_ROOT)
    rows: list[dict[str, Any]] = []
    phase_meta = {}
    for phase in PHASES:
        built, meta = build_plan(m4_run=M4_RUN, interface=interface, phase=phase)
        phase_meta[phase] = meta
        rows.extend({"phase_id": phase, **row} for row in built)
    expected = {"m4_six": 72, "m4_remaining": 216, "scripted_controls": 16, "matched_worlds": 72}
    counts = {phase: sum(row["phase_id"] == phase for row in rows) for phase in PHASES}
    if counts != expected or len(rows) != 376:
        raise ValueError(f"Monitor schedule differs from frozen allocation: {counts}")
    if len({row["request_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate request ID in complete Monitor schedule")
    plan_bytes = b"".join(canonical(row) + b"\n" for row in rows)
    artifact_paths = [
        ROOT / ".gitignore",
        ROOT / "configs/m4-deepseek-agent-v1.json", ROOT / "configs/m4-deepseek-monitor-v1.json",
        ROOT / "configs/m4-deepseek-pilot-plan-v1.json",
        ROOT / "docs/M4_DEEPSEEK_AGENT_V1_PROTOCOL.md", ROOT / "docs/M4_DEEPSEEK_MONITOR_V1_PROTOCOL.md",
        ROOT / "COLLUSCOPE_PERSISTENT_RESEARCH_GOAL.md", ROOT / "Codex_Continuous_Goal.md",
        ROOT / "configs/m4-scenarios-v1.json", ROOT / "configs/m4-splits-v1.json",
        ROOT / "configs/monitor-recovery-diagnostic-v1.json",
        ROOT / "data/sprint-baseline-v1/controls.jsonl",
        ROOT / "prompts/m4-deepseek-agent-v1/monitor-system.txt",
        ROOT / "src/colluscope/deepseek_m4_v1.py", ROOT / "src/colluscope/deepseek_monitor_v1.py",
        ROOT / "src/colluscope/deepseek_m4_audit.py", ROOT / "scripts/run_deepseek_monitor_v1.py",
        ROOT / "scripts/freeze_deepseek_monitor_v1.py", ROOT / "scripts/prepare_full_research_monitor.py",
        ROOT / "scripts/audit_deepseek_first_research.py", ROOT / "scripts/run_deepseek_first_research.py",
        ROOT / "src/colluscope/sprint_baselines.py", ROOT / "src/colluscope/sprint_replay.py",
        ROOT / "src/colluscope/m4_live_runtime.py", M4_RUN / "run_manifest.json",
        M4_RUN / "episodes.jsonl", RUN_ROOT / "pilot/selected_interface.json",
    ]
    manifest = {
        "schema_version": "deepseek-m4-monitor-freeze-v1", "protocol_id": "M4-DEEPSEEK-MONITOR-V1",
        "interface": interface, "created_utc": now_utc(),
        "source_commit": __import__("subprocess").check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "environment": {"python": sys.version, "platform": platform.platform()},
        "source_m4_run": "runs/deepseek-first-m4/agent",
        "source_m4_run_manifest_sha256": sha((M4_RUN / "run_manifest.json").read_bytes()),
        "source_m4_episodes_sha256": sha((M4_RUN / "episodes.jsonl").read_bytes()),
        "pre_monitor_agent_audit": {"status": agent_audit["status"],
            "completed_groups": agent_audit["completed_groups"],
            "physical_agent_requests": agent_audit["physical_agent_requests"]},
        "pilot_selection_sha256": sha((RUN_ROOT / "pilot/selected_interface.json").read_bytes()),
        "phase_counts": counts, "total_request_count": len(rows), "retry_limit": 0,
        "replacement_limit": 0, "request_schedule_sha256": sha(plan_bytes),
        "phase_metadata": phase_meta,
        "artifact_sha256": {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in artifact_paths},
        "raw_sources_include_synthetic_private_text": True,
        "raw_sources_acl_restricted": True, "auth_headers_or_credentials_saved": False,
    }
    if PLAN_PATH.exists() or MANIFEST_PATH.exists():
        if not PLAN_PATH.is_file() or not MANIFEST_PATH.is_file():
            raise RuntimeError("partial existing Monitor freeze; refusing overwrite")
        saved_manifest = json.loads(MANIFEST_PATH.read_bytes())
        comparable = {**manifest, "created_utc": saved_manifest.get("created_utc")}
        if PLAN_PATH.read_bytes() != plan_bytes or saved_manifest != comparable:
            raise RuntimeError("existing Monitor freeze differs; preserve it and create a versioned new run")
        manifest = saved_manifest
    else:
        write_once(PLAN_PATH, plan_bytes)
        write_once(MANIFEST_PATH, canonical(manifest) + b"\n")
    acl = verify_private_directory_acl(FREEZE_ROOT)
    return {"status": "PASS_FROZEN", "request_count": len(rows), "phase_counts": counts,
            "plan_sha256": sha(plan_bytes), "acl_verified": acl.get("verified") is True,
            "model_calls": 0}


def verify() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_bytes())
    if sha(PLAN_PATH.read_bytes()) != manifest.get("request_schedule_sha256"):
        raise ValueError("frozen Monitor request schedule hash mismatch")
    if sha((M4_RUN / "episodes.jsonl").read_bytes()) != manifest.get("source_m4_episodes_sha256"):
        raise ValueError("M4 source changed after Monitor freeze")
    from scripts.audit_deepseek_first_research import audit_agent_run
    agent_audit = audit_agent_run(M4_RUN, write_outputs=False)
    expected_agent_audit = {"status": agent_audit.get("status"),
        "completed_groups": agent_audit.get("completed_groups"),
        "physical_agent_requests": agent_audit.get("physical_agent_requests")}
    if agent_audit.get("status") != "PASS_INDEPENDENT_AGENT_REPLAY" or manifest.get("pre_monitor_agent_audit") != expected_agent_audit:
        raise ValueError("independent Agent raw replay no longer matches Monitor freeze")
    for rel, expected in manifest["artifact_sha256"].items():
        path = (ROOT / rel).resolve()
        if ROOT.resolve() not in path.parents and path != ROOT.resolve():
            raise ValueError("Monitor freeze artifact escaped repository/run root")
        if not path.is_file() or sha(path.read_bytes()) != expected:
            raise ValueError(f"Monitor freeze artifact changed: {rel}")
    rows = [json.loads(line) for line in PLAN_PATH.read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != manifest["total_request_count"]:
        raise ValueError("Monitor plan row count mismatch")
    for phase in PHASES:
        selected = [row for row in rows if row["phase_id"] == phase]
        rebuilt, meta = build_plan(m4_run=M4_RUN, interface=manifest["interface"], phase=phase)
        expected = [{"phase_id": phase, **row} for row in rebuilt]
        if canonical(selected) != canonical(expected):
            raise ValueError(f"frozen Monitor rows do not replay exactly: {phase}")
        verify_plan(rebuilt, meta, interface=manifest["interface"], phase=phase)
    acl = verify_private_directory_acl(FREEZE_ROOT)
    if acl.get("verified") is not True:
        raise PermissionError("frozen Monitor plan ACL is not verified")
    return {"status": "PASS_INPUTS_FROZEN", "phase_counts": manifest["phase_counts"],
            "plan_sha256": manifest["request_schedule_sha256"], "model_calls": 0,
            "acl_verified": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "verify"))
    args = parser.parse_args()
    result = freeze() if args.action == "freeze" else verify()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
