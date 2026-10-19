from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.m2_v3_deepseek import (  # noqa: E402
    _append_jsonl,
    _load_responses,
    _now,
    apply_private_acl,
    build_run,
    gate_format_rate,
    load_prepared,
    run_requests,
    verify_prepared,
)


def _write_private_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    apply_private_acl(path.parent)


def _resolve_run_dir(value: Path) -> Path:
    resolved = value if value.is_absolute() else ROOT / value
    resolved = resolved.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("M2-V3 run artifacts must stay inside this repository") from exc
    return resolved


def _phase(run_dir: Path, repo_root: Path, requests: list[dict], phase: str, every: int) -> dict:
    result = run_requests(run_dir, repo_root, requests, phase=phase, progress_every=every)
    result["recorded_at_utc"] = _now().isoformat()
    _append_jsonl(run_dir / "phase_results.jsonl", result)
    return result


def _terminalize_unstarted(run_dir: Path, requests: list[dict], *, reason: str,
                           partitions: set[str], diagnostic_only: bool = False) -> None:
    stored = _load_responses(run_dir)
    for request in requests:
        if request["partition"] not in partitions or request["request_id"] in stored:
            continue
        if diagnostic_only and not request.get("diagnostic"):
            continue
        _append_jsonl(run_dir / "results.jsonl", {
            "request_id": request["request_id"], "status": "not_dispatched",
            "error_class": reason, "terminal": True, "recorded_at_utc": _now().isoformat()})
        stored[request["request_id"]] = {"status": "not_dispatched"}


def run_all(repo_root: Path, run_dir: Path, progress_every: int) -> dict:
    verify = verify_prepared(repo_root, run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    git_head = __import__("subprocess").run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=True
    ).stdout.strip()
    git_dirty = bool(__import__("subprocess").run(
        ["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True, check=True
    ).stdout.strip())
    if git_head != manifest["source_commit"] or manifest["source_tree_was_dirty_at_prepare"] or git_dirty:
        raise RuntimeError("paid execution requires the exact clean, pushed source freeze")
    rows, requests, _ = load_prepared(run_dir)

    diagnostic = _phase(run_dir, repo_root, requests, "diagnostic", progress_every)
    diagnostic_gate = gate_format_rate(rows, requests, run_dir, diagnostic=True)
    diagnostic_gate["phase_execution"] = diagnostic
    _write_private_json(run_dir / "gates/diagnostic.json", diagnostic_gate)
    if not diagnostic_gate["passed"]:
        _terminalize_unstarted(run_dir, requests, reason=(
            "stop_cutoff_diagnostic_incomplete" if diagnostic["cutoff_reached"] else "diagnostic_gate_failed"),
            partitions={"F1", "F2", "F3"})
        decision = {"status": "NO_GO_DIAGNOSTIC", "diagnostic_gate": diagnostic_gate,
                    "calibration_started": False, "evaluation_started": False}
        _write_private_json(run_dir / "decision_state.json", decision)
        return decision

    calibration = _phase(run_dir, repo_root, requests, "f1", progress_every)
    calibration_gate = gate_format_rate(rows, requests, run_dir, diagnostic=False)
    calibration_gate["phase_execution"] = calibration
    _write_private_json(run_dir / "gates/calibration.json", calibration_gate)
    if not calibration_gate["passed"]:
        _terminalize_unstarted(run_dir, requests, reason=(
            "stop_cutoff_calibration_incomplete" if calibration["cutoff_reached"] else "calibration_gate_failed"),
            partitions={"F2", "F3"})
        decision = {"status": "NO_GO_CALIBRATION", "diagnostic_gate": diagnostic_gate,
                    "calibration_gate": calibration_gate, "evaluation_started": False}
        _write_private_json(run_dir / "decision_state.json", decision)
        return decision

    evaluation = _phase(run_dir, repo_root, requests, "f23", progress_every)
    if evaluation["cutoff_reached"]:
        _terminalize_unstarted(run_dir, requests, reason="stop_before_2026_10_20_0900_asia_hong_kong",
                               partitions={"F2", "F3"})
    elif evaluation["selected_logical_requests"] and evaluation["failed_evaluation_rows"]:
        _terminalize_unstarted(run_dir, requests, reason="evaluation_stopped_after_terminal_error",
                               partitions={"F2", "F3"})
    terminal = _load_responses(run_dir)
    status_counts = {}
    for result in terminal.values():
        status_counts[result.get("status", "unknown")] = status_counts.get(result.get("status", "unknown"), 0) + 1
    decision = {"status": "RUN_COMPLETE" if not evaluation["cutoff_reached"] else "STOPPED_AT_CUTOFF",
                "diagnostic_gate": diagnostic_gate, "calibration_gate": calibration_gate,
                "evaluation": evaluation, "evaluation_started": True,
                "completed_logical_requests": status_counts.get("completed", 0),
                "terminal_logical_request_status_counts": status_counts,
                "assigned_requests_terminal": len(terminal) == len(requests),
                "verification": verify}
    _write_private_json(run_dir / "decision_state.json", decision)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the frozen M2-V3 DeepSeek research protocol")
    parser.add_argument("command", choices=("prepare", "verify", "run"))
    parser.add_argument("--run-dir", type=Path, default=ROOT / "runs/m2-v3/deepseek-overnight-r1")
    parser.add_argument("--progress-every", type=int, default=10)
    args = parser.parse_args()
    run_dir = _resolve_run_dir(args.run_dir)

    if args.command == "prepare":
        if run_dir.exists() and any(run_dir.iterdir()):
            if (run_dir / "manifest.json").exists():
                report = verify_prepared(ROOT, run_dir)
                print(json.dumps({"status": "already_prepared", **report}, sort_keys=True))
                return 0
            contents = {path.name for path in run_dir.iterdir()}
            if contents != {"preflight"}:
                raise RuntimeError("refusing to overwrite a non-empty unrecognized run directory")
        manifest = build_run(ROOT, run_dir)
        print(json.dumps({k: manifest[k] for k in (
            "source_commit", "source_tree_was_dirty_at_prepare", "logical_evaluation_rows",
            "unique_logical_requests", "conservative_peak_cost_upper_bound_two_attempts_usd",
            "max_payload_bytes", "diagnostic_rows", "inference_status_at_prepare")}, sort_keys=True))
        return 0
    if not (run_dir / "manifest.json").exists():
        raise FileNotFoundError("prepared run manifest is missing")
    if args.command == "verify":
        report = verify_prepared(ROOT, run_dir)
        _write_private_json(run_dir / "verification/prepared.json", report)
        print(json.dumps(report, sort_keys=True))
        return 0
    result = run_all(ROOT, run_dir, max(1, args.progress_every))
    print(json.dumps({"status": result["status"],
                      "completed_logical_requests": result.get("completed_logical_requests"),
                      "evaluation_started": result.get("evaluation_started", False)}, sort_keys=True))
    return 0 if result["status"] in {"RUN_COMPLETE", "STOPPED_AT_CUTOFF", "NO_GO_DIAGNOSTIC", "NO_GO_CALIBRATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
