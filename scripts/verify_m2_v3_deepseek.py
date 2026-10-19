from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.m2_v3_deepseek import (  # noqa: E402
    PHYSICAL_LIMIT,
    ATTEMPT_LIMIT,
    _load_responses,
    _terminal_attempts,
    apply_private_acl,
    load_prepared,
    verify_prepared,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline integrity check for M2-V3 DeepSeek run")
    parser.add_argument("--run-dir", type=Path, default=ROOT / "runs/m2-v3/deepseek-overnight-r1")
    args = parser.parse_args()
    run_dir = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    run_dir = run_dir.resolve()
    try:
        run_dir.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("M2-V3 run artifacts must stay inside this repository") from exc
    result = verify_prepared(ROOT, run_dir)
    _, physical, reserved_cost = _terminal_attempts(run_dir)
    rows, requests, _ = load_prepared(run_dir)
    attempts, _, _ = _terminal_attempts(run_dir)
    attempts_per_request = {request_id: len({item["attempt_id"] for item in values})
                            for request_id, values in attempts.items()}
    if physical > min(PHYSICAL_LIMIT, ATTEMPT_LIMIT * len(requests)) or reserved_cost > 5:
        raise RuntimeError("physical attempts or cost reserve exceed frozen cap")
    if any(count > ATTEMPT_LIMIT for count in attempts_per_request.values()):
        raise RuntimeError("a logical request exceeded the per-request retry limit")
    responses = _load_responses(run_dir)
    if not set(responses).issubset({request["request_id"] for request in requests}):
        raise RuntimeError("results ledger contains an unassigned request ID")
    decision_path = run_dir / "decision_state.json"
    terminalized = decision_path.exists()
    all_assigned_terminal = len(responses) == len(requests)
    if terminalized and not all_assigned_terminal:
        raise RuntimeError("final decision exists but not every assigned request has a terminal status")
    result.update({"physical_attempts": physical, "physical_attempt_limit": PHYSICAL_LIMIT,
                   "conservative_committed_cost_usd": str(reserved_cost),
                   "max_attempts_per_request": ATTEMPT_LIMIT,
                   "attempt_cap_passed": True, "cost_cap_passed": True,
                   "results_ledger_request_count": len(responses),
                   "assigned_requests_terminal": all_assigned_terminal,
                   "decision_terminalization_present": terminalized,
                   "attempts_per_request": attempts_per_request})
    path = run_dir / "verification/final-integrity.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    apply_private_acl(path.parent)
    artifact_index = {}
    for item in sorted(run_dir.rglob("*")):
        if not item.is_file() or item.name == "artifact_sha256.json":
            continue
        if item.is_symlink():
            raise ValueError("symlinks are forbidden in the private evidence run")
        relative = item.relative_to(run_dir).as_posix()
        artifact_index[relative] = {"sha256": hashlib.sha256(item.read_bytes()).hexdigest(),
                                    "bytes": item.stat().st_size}
    index_path = run_dir / "artifact_sha256.json"
    index_path.write_text(json.dumps(artifact_index, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    apply_private_acl(run_dir)
    result["artifact_file_count_hashed"] = len(artifact_index)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
