#!/usr/bin/env python3
"""Score frozen M1 Monitor requests fieldwise without exporting raw text."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.m1_monitor_scoring import score_rows  # noqa: E402


def _read_jsonl(path: Path) -> tuple[list[dict], bytes]:
    raw = path.read_bytes()
    rows = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"JSONL row {line_number} in {path.name} is not an object")
        rows.append(value)
    return rows, raw


def _write_once(path: Path, raw: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()


def main() -> int:
    import argparse
    import subprocess

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    allowed_root = (ROOT / "runs/m1_100/m1-package-replication-v3").resolve()
    if run_dir == allowed_root or not run_dir.is_relative_to(allowed_root) or run_dir.is_symlink():
        raise PermissionError("scoring is restricted to a real M1 v3 run directory")
    ignored = subprocess.run(["git", "check-ignore", "--quiet", run_dir.relative_to(ROOT).as_posix()],
                             cwd=ROOT, check=False)
    if ignored.returncode != 0:
        raise PermissionError("run directory is not Git-ignored")
    from scripts.local_llama_security import verify_private_directory_acl
    verify_private_directory_acl(run_dir)

    source = run_dir / "private/monitor_audit_candidate_v1"
    requests, req_bytes = _read_jsonl(source / "monitor-request-inputs.jsonl")
    references, ref_bytes = _read_jsonl(source / "adjudicated-references.jsonl")
    responses, response_bytes = _read_jsonl(source / "responses.jsonl")
    result = score_rows(requests, references, responses)
    out_dir = source / "scoring_v1"
    out_dir.mkdir(parents=False, exist_ok=False)
    from scripts.local_llama_security import restrict_private_directory_acl
    restrict_private_directory_acl(out_dir)
    sanitized_rows = result.pop("rows")
    result["input_sha256"] = {
        "requests": hashlib.sha256(req_bytes).hexdigest(),
        "adjudicated_references": hashlib.sha256(ref_bytes).hexdigest(),
        "raw_responses": hashlib.sha256(response_bytes).hexdigest(),
    }
    result["score_rows_sha256"] = hashlib.sha256(
        (json.dumps(sanitized_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    result["output_contains_raw_message_or_response_text"] = False
    _write_once(out_dir / "summary.json", (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode())
    _write_once(out_dir / "scored-rows.jsonl", b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
        for row in sanitized_rows))
    acl = verify_private_directory_acl(run_dir)
    print(json.dumps({"status": result["status"], "assigned_request_count": result["assigned_request_count"],
                      "missing_response_count": result["missing_response_count"], "output_dir": str(out_dir),
                      "acl": acl}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
