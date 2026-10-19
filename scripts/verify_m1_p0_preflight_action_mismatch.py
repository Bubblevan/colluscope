"""Verify a parser-V2 preflight that parsed its output but chose another valid action."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EMPTY_THINK_PREFIX = "<think>\n\n</think>\n\n"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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

    preflight = _json(run_dir / "preflight" / "result.json")
    terminal = _json(run_dir / "terminal-status.json")
    rows = _jsonl(run_dir / "preflight" / "requests.jsonl")
    state = preflight.get("budget_state", {})
    if (preflight.get("status") != "FAIL" or
            preflight.get("error") != "preflight expected send_message, received no_message" or
            state.get("logical_requests") != 5 or state.get("http_attempts") != 5 or
            state.get("completion_attempts") != 2 or
            terminal.get("status") != "NO_GO_PREFLIGHT" or
            terminal.get("episodes_attempted") != 0 or
            terminal.get("pilot_logical_requests") != 0 or terminal.get("pilot_http_attempts") != 0):
        raise ValueError("run does not match the retained zero-episode action-mismatch stop")

    by_id = {row.get("request_id"): row for row in rows}
    ballot_envelope = json.loads(by_id["preflight-completion-1"]["raw_response"])
    ballot_text = ballot_envelope["choices"][0]["message"]["content"]
    ballot_action = json.loads(ballot_text.removeprefix(EMPTY_THINK_PREFIX))
    message_envelope = json.loads(by_id["preflight-completion-2"]["raw_response"])
    message_text = message_envelope["choices"][0]["message"]["content"]
    message_action = json.loads(message_text.removeprefix(EMPTY_THINK_PREFIX))
    mismatch = by_id.get("preflight-action-2", {})
    if (not ballot_text.startswith(EMPTY_THINK_PREFIX) or ballot_action.get("type") != "ballot" or
            not message_text.startswith(EMPTY_THINK_PREFIX) or message_action != {"type": "no_message"} or
            mismatch.get("expected_action") != "send_message" or
            mismatch.get("actual_action") != "no_message" or mismatch.get("raw_response") != message_text):
        raise ValueError("raw actions do not match the retained parser-V2 counterexample")
    if _json(run_dir / "server-health.json").get("status") != "PASS":
        raise ValueError("server health did not pass")
    owner = _json(run_dir / "listener-owner-attestation.json")
    launch = _json(run_dir / "launch.json")
    if owner.get("status") != "verified_exact_pid" or owner.get("expected_pid") != launch.get("pid"):
        raise ValueError("server process ownership was not verified")
    for relative in ("researcher/T.jsonl", "researcher/B.jsonl", "monitor_inputs/evidence.jsonl"):
        if (run_dir / relative).exists():
            raise ValueError(f"preflight failure must not contain Pilot data: {relative}")

    return {"status": "PASS_PACKAGE_INTEGRITY__NO_GO_ACTION_MISMATCH",
            "manifest_entries_verified": len(manifest.get("sha256", {})),
            "historical_source_files_verified": len(manifest.get("runtime_source_sha256", {})),
            "preflight_logical_requests": state["logical_requests"],
            "preflight_http_attempts": state["http_attempts"],
            "preflight_completion_attempts": state["completion_attempts"],
            "empty_prefix_parser_accepted_ballot": True,
            "empty_prefix_parser_accepted_message_branch": True,
            "message_probe_expected": "send_message", "message_probe_actual": "no_message",
            "episodes": 0, "external_calls": 0, "paid_api_calls": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.run), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
