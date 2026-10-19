"""Verify a retained M1-P0 startup failure before any model HTTP request."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    if not run_dir.is_relative_to(ROOT.resolve()):
        raise ValueError("run package must be inside this repository")
    manifest = _json(run_dir / "manifest.json")
    for relative, expected in manifest.get("sha256", {}).items():
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise ValueError(f"unsafe run artifact path: {relative}")
        path = (run_dir / relative).resolve()
        if not path.is_relative_to(run_dir) or not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"run artifact hash mismatch: {relative}")

    environment = _json(run_dir / "environment.json")
    source_commit = environment.get("git_head")
    if not isinstance(source_commit, str) or len(source_commit) != 40:
        raise ValueError("run does not identify its source commit")
    for relative, expected in manifest.get("runtime_source_sha256", {}).items():
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise ValueError(f"unsafe runtime source path: {relative}")
        source = subprocess.run(["git", "show", f"{source_commit}:{relative}"], cwd=ROOT,
                                capture_output=True, timeout=15, check=True).stdout
        if hashlib.sha256(source).hexdigest() != expected:
            raise ValueError(f"historical source hash mismatch: {relative}")

    terminal = _json(run_dir / "terminal-status.json")
    failure = _json(run_dir / "failure.json").get("failure", {})
    stderr = (run_dir / "logs" / "llama-server.stderr.log").read_text(encoding="utf-8")
    if (terminal.get("status") != "NO_GO_RUNTIME_FAILURE" or
            terminal.get("preflight_status") != "NOT_RUN" or
            terminal.get("pilot_logical_requests") != 0 or terminal.get("pilot_http_attempts") != 0 or
            terminal.get("episodes_attempted") != 0 or
            failure.get("type") != "URLError" or "WinError 10013" not in failure.get("error", "") or
            "model loaded" not in stderr or "listening on http://127.0.0.1:8081" not in stderr or
            (run_dir / "preflight" / "requests.jsonl").exists()):
        raise ValueError("package is not the retained preflight-startup socket denial")
    return {"status": "PASS_PACKAGE_INTEGRITY__NO_GO_NO_HTTP",
            "manifest_entries_verified": len(manifest.get("sha256", {})),
            "historical_source_files_verified": len(manifest.get("runtime_source_sha256", {})),
            "server_loaded_and_listened": True, "preflight_status": "NOT_RUN",
            "http_requests": 0, "episodes": 0, "external_calls": 0, "paid_api_calls": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.run), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
