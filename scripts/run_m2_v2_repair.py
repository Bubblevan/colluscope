#!/usr/bin/env python3
"""Versioned, hard-bounded M2-V2 compatibility repairs and gated formal run."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import scripts.run_m2_v2 as runner
from colluscope.m2_corpus import file_sha256

MAX_REPAIR_ITERATIONS = 3
MAX_ATTEMPTS_PER_ITERATION = 30
MAX_CUMULATIVE_PREFLIGHT_ATTEMPTS = 120  # Original 30 + at most three repairs.


def repair_paths(iteration: int) -> tuple[Path, Path, Path]:
    if not 1 <= iteration <= MAX_REPAIR_ITERATIONS:
        raise ValueError("repair iteration must be between 1 and 3")
    suffix = f"repair-{iteration:02d}"
    return (
        ROOT / "configs" / f"m2-v2-{suffix}-candidates.json",
        ROOT / "prompts" / "m2-v2" / f"{suffix}-system.txt",
        ROOT / "prompts" / "m2-v2" / f"{suffix}-system-compact.txt",
    )


def bind_repair(iteration: int) -> tuple[Path, Path, Path]:
    candidates, full_prompt, compact_prompt = repair_paths(iteration)
    for path in (candidates, full_prompt, compact_prompt):
        if not path.is_file():
            raise FileNotFoundError(f"repair freeze artifact is missing: {path.relative_to(ROOT)}")
    runner.CANDIDATES_PATH = candidates
    runner.SYSTEM_FULL = full_prompt
    runner.SYSTEM_COMPACT = compact_prompt
    return candidates, full_prompt, compact_prompt


def run_root() -> Path:
    return ROOT / "runs/m2-v2/recovery-20261019"


def _attempt_count(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank append-only attempt-ledger row: {path}:{line_number}")
        row = json.loads(line)
        count += row.get("event") == "attempt_started"
    return count


def attempt_counts() -> dict[str, int]:
    root = run_root()
    dirs = {"original": root / "study"}
    dirs.update({f"repair_{number:02d}": root / f"repair-{number:02d}"
                 for number in range(1, MAX_REPAIR_ITERATIONS + 1)})
    return {name: _attempt_count(path / "preflight-attempts.jsonl") for name, path in dirs.items()}


def _decision(path: Path) -> dict[str, Any]:
    decision_path = path / "preflight-decision.json"
    if not decision_path.is_file():
        raise PermissionError(f"required prior compatibility decision is missing: {decision_path}")
    return json.loads(decision_path.read_text(encoding="utf-8"))


def _require_prior_no_go(iteration: int) -> None:
    prior = run_root() / ("study" if iteration == 1 else f"repair-{iteration - 1:02d}")
    result = _decision(prior)
    if result.get("status") != "NO_GO_INTERFACE" or result.get("all_ten_valid") is not False:
        raise PermissionError("a repair may run only after the immediately previous gate failed 10/10")
    counts = attempt_counts()
    if sum(counts.values()) > MAX_CUMULATIVE_PREFLIGHT_ATTEMPTS:
        raise RuntimeError("cumulative compatibility HTTP-attempt budget is already exhausted")
    if sum(counts.values()) + MAX_ATTEMPTS_PER_ITERATION > MAX_CUMULATIVE_PREFLIGHT_ATTEMPTS:
        raise RuntimeError("this repair could exceed the 120-attempt cumulative hard cap")


def _require_current_pass(out: Path) -> dict[str, Any]:
    decision = _decision(out)
    if decision.get("status") != "PASS_INTERFACE" or decision.get("all_ten_valid") is not True:
        raise PermissionError("formal M2-V2 phases require a 10/10 PASS_INTERFACE gate")
    return decision


def _require_score_gates(out: Path) -> None:
    _require_current_pass(out)
    calibration_path = out / "calibration-freeze.json"
    verification_path = out / "final-verification.json"
    if not calibration_path.is_file() or json.loads(calibration_path.read_text(encoding="utf-8")).get(
            "status") != "CALIBRATION_GO":
        raise PermissionError("independent scoring requires the frozen F1 calibration gate to pass")
    if not verification_path.is_file() or json.loads(verification_path.read_text(
            encoding="utf-8")).get("status") != "PASS_LEDGER_COVERAGE":
        raise PermissionError("independent scoring requires all 1,000 evaluations to pass ledger verification")


def _verify_preflight_inputs(out: Path, registry: Path) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_m2_v2_preflight.py"),
         "--out", str(out), "--registry", str(registry)],
        cwd=ROOT, capture_output=True, text=True, timeout=180, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("independent no-call input audit failed: " + result.stderr[-2000:])
    audit = json.loads(result.stdout)
    manifest = json.loads((out / "preflight-manifest.json").read_text(encoding="utf-8"))
    if audit.get("status") != "PASS_M2_V2_PREFLIGHT_INPUT_AUDIT" or \
            audit.get("model_calls") != 0 or audit.get("http_attempts") != 0 or \
            audit.get("candidate_registry_sha256") != file_sha256(registry) or \
            audit.get("preflight_manifest_sha256") != file_sha256(out / "preflight-manifest.json"):
        raise ValueError("input auditor result does not match this versioned frozen registry")
    runner.write_json(out / "analysis/repair-preflight-input-audit.json", audit)
    return audit


def execute(iteration: int, out: Path, phase: str, resume: bool = False) -> dict[str, Any]:
    registry, _, _ = bind_repair(iteration)
    out = out.resolve()
    expected_out = run_root() / f"repair-{iteration:02d}"
    if out != expected_out.resolve():
        raise ValueError("repair outputs must use their fixed, separate ignored run directory")

    if phase in {"prepare-preflight", "verify-inputs", "preflight", "audit-results"}:
        if phase in {"prepare-preflight", "preflight"}:
            _require_prior_no_go(iteration)
        if phase == "prepare-preflight":
            if resume:
                raise ValueError("frozen preflight preparation cannot be resumed")
            result = runner.prepare_preflight(out)
        elif phase == "verify-inputs":
            result = _verify_preflight_inputs(out, registry)
        elif phase == "preflight":
            _verify_preflight_inputs(out, registry)
            result = runner.run_preflight(out, resume=resume)
            counts = attempt_counts()
            local_count = counts[f"repair_{iteration:02d}"]
            if local_count > MAX_ATTEMPTS_PER_ITERATION or \
                    sum(counts.values()) > MAX_CUMULATIVE_PREFLIGHT_ATTEMPTS:
                raise RuntimeError("compatibility repair hard attempt cap exceeded")
        else:
            _decision(out)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/audit_m2_v2_preflight_results.py"),
                 "--out", str(out), "--write", "--summary-only"],
                cwd=ROOT, capture_output=True, text=True, timeout=180, check=False,
            )
            if result.returncode != 0:
                raise RuntimeError("independent response audit failed: " + result.stderr[-2000:])
            result = json.loads(result.stdout)
            counts = attempt_counts()
            if result.get("physical_http_attempts", 0) > MAX_ATTEMPTS_PER_ITERATION or \
                    counts[f"repair_{iteration:02d}"] > MAX_ATTEMPTS_PER_ITERATION or \
                    sum(counts.values()) > MAX_CUMULATIVE_PREFLIGHT_ATTEMPTS:
                raise RuntimeError("compatibility repair hard attempt cap exceeded")
        return result

    if phase == "prepare-formal":
        _require_current_pass(out)
        if resume:
            raise ValueError("formal preparation is immutable")
        return runner.prepare_formal(out)
    if phase == "calibrate":
        _require_current_pass(out)
        return runner.execute_formal_phase(out, "calibration", resume=resume)
    if phase == "close-calibration":
        _require_current_pass(out)
        return runner.close_calibration(out)
    if phase == "held-out":
        _require_current_pass(out)
        calibration = json.loads((out / "calibration-freeze.json").read_text(encoding="utf-8"))
        if calibration.get("status") != "CALIBRATION_GO":
            raise PermissionError("held-out inference requires a passed frozen F1 calibration gate")
        return runner.execute_formal_phase(out, "held_out", resume=resume)
    if phase == "verify":
        _require_current_pass(out)
        return runner.verify_terminal(out)
    if phase == "score":
        _require_score_gates(out)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/score_m2_v2.py"), "--out", str(out)],
            cwd=ROOT, capture_output=True, text=True, timeout=180, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("independent raw-response scoring failed: " + result.stderr[-2000:])
        return json.loads(result.stdout)
    raise ValueError(f"unknown repair execution phase: {phase}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    phases = parser.add_mutually_exclusive_group(required=True)
    for phase in ("prepare-preflight", "verify-inputs", "preflight", "audit-results",
                  "prepare-formal", "calibrate", "close-calibration", "held-out", "verify", "score"):
        phases.add_argument(f"--{phase}", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    phase = next(name for name in ("prepare-preflight", "verify-inputs", "preflight", "audit-results",
                                   "prepare-formal", "calibrate", "close-calibration", "held-out",
                                   "verify", "score") if getattr(args, name.replace("-", "_")))
    result = execute(args.iteration, args.out, phase, args.resume)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
