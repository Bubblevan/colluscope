"""Verify the retained M1-P0 run that stopped before research episodes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _verify_manifest(run_dir: Path, manifest: dict[str, Any]) -> int:
    count = 0
    for relative, expected in manifest.get("sha256", {}).items():
        path = (run_dir / relative).resolve()
        if not path.is_relative_to(run_dir.resolve()) or not path.is_file():
            raise ValueError(f"manifest entry is missing or escapes its run: {relative}")
        if _sha256(path) != expected:
            raise ValueError(f"artifact hash mismatch: {relative}")
        count += 1
    return count


def verify(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    if not run_dir.is_relative_to(ROOT.resolve()):
        raise ValueError("run package must be inside this repository")
    manifest = _read_json(run_dir / "manifest.json")
    checked = _verify_manifest(run_dir, manifest)
    environment = _read_json(run_dir / "environment.json")
    source_commit = environment.get("git_head")
    if not isinstance(source_commit, str) or len(source_commit) != 40:
        raise ValueError("retained run does not identify its source commit")
    for relative, expected in manifest.get("runtime_source_sha256", {}).items():
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise ValueError(f"runtime source path is unsafe: {relative}")
        try:
            source = subprocess.run(["git", "show", f"{source_commit}:{relative}"], cwd=ROOT,
                                    capture_output=True, timeout=15, check=True).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise ValueError(f"historical source is unavailable at {source_commit}: {relative}") from exc
        if hashlib.sha256(source).hexdigest() != expected:
            raise ValueError(f"historical runtime source hash mismatch: {relative}")

    terminal = _read_json(run_dir / "terminal-status.json")
    preflight = _read_json(run_dir / "preflight" / "result.json")
    rows = _read_jsonl(run_dir / "preflight" / "requests.jsonl")
    if (terminal.get("status") != "NO_GO_PREFLIGHT" or terminal.get("episodes_attempted") != 0 or
            terminal.get("episodes_completed") != 0 or terminal.get("episodes_failed") != 0 or
            terminal.get("pilot_logical_requests") != 0 or terminal.get("pilot_http_attempts") != 0):
        raise ValueError("run is not the retained zero-episode preflight stop")
    if preflight.get("status") != "FAIL":
        raise ValueError("expected the live strict-action preflight failure")
    state = preflight.get("budget_state", {})
    if (state.get("logical_requests") != 4 or state.get("http_attempts") != 4 or
            state.get("completion_attempts") != 1):
        raise ValueError("current preflight usage does not match the recorded continuation")
    completion = next((row for row in rows if row.get("request_id") == "preflight-completion-1"), None)
    parse_failure = next((row for row in rows if row.get("request_id") == "preflight-parse-1"), None)
    if completion is None or parse_failure is None:
        raise ValueError("the first raw action response and strict-parser failure are required")
    raw = json.loads(completion["raw_response"])
    text = raw["choices"][0]["message"]["content"]
    if not text.startswith("<think>\n\n</think>\n\n{"):
        raise ValueError("raw model output no longer matches the retained Qwen3 empty-think-prefix case")
    if parse_failure.get("raw_response") != text or "malformed JSON" not in parse_failure.get("error", ""):
        raise ValueError("strict parser failure did not preserve the exact raw response")
    if _read_json(run_dir / "server-health.json").get("status") != "PASS":
        raise ValueError("local server health did not pass")
    owner = _read_json(run_dir / "listener-owner-attestation.json")
    launch = _read_json(run_dir / "launch.json")
    if owner.get("status") != "verified_exact_pid" or owner.get("expected_pid") != launch.get("pid"):
        raise ValueError("local llama.cpp process ownership is not independently attested")

    resume = _read_json(run_dir / "preflight-resume.json")
    copied_parent = (run_dir / resume["previous_run_copy"]).resolve()
    if not copied_parent.is_relative_to(run_dir):
        raise ValueError("copied parent path escapes the current run")
    parent_manifest_path = copied_parent / "manifest.json"
    if _sha256(parent_manifest_path) != resume["previous_manifest_sha256"]:
        raise ValueError("copied parent manifest hash mismatch")
    parent_manifest = _read_json(parent_manifest_path)
    parent_checked = _verify_manifest(copied_parent, parent_manifest)
    prior = _read_json(copied_parent / "preflight" / "result.json")
    prior_terminal = _read_json(copied_parent / "terminal-status.json")
    if (prior.get("error") != "local GGUF tokenizer IDs differ from llama.cpp /tokenize" or
            prior_terminal.get("episodes_attempted") != 0 or
            prior_terminal.get("pilot_logical_requests") != 0):
        raise ValueError("copied parent is not the exact zero-episode tokenizer failure")
    setup_responses = sum(row.get("status") == "response_returned" and
                          row.get("request_id") in {"preflight-props", "preflight-template", "preflight-tokenize"}
                          for row in rows)
    if setup_responses != 3 or preflight.get("error") != (
            "preflight action failed the frozen strict parser: malformed JSON response: "
            "Expecting value: line 1 column 1 (char 0)"):
        raise ValueError("continuation did not re-use three setup responses and stop at strict parsing")
    if (run_dir / "researcher" / "T.jsonl").exists() or (run_dir / "monitor_inputs" / "evidence.jsonl").exists():
        raise ValueError("a preflight failure package must not contain research episodes")

    return {"status": "PASS_PACKAGE_INTEGRITY__NO_GO_PREFLIGHT",
            "manifest_entries_verified": checked,
            "copied_parent_manifest_entries_verified": parent_checked,
            "current_preflight_logical_requests": state["logical_requests"],
            "current_preflight_http_attempts": state["http_attempts"],
            "current_preflight_completion_attempts": state["completion_attempts"],
            "cumulative_setup_requests_reused": setup_responses,
            "episodes": 0, "pilot_logical_requests": 0, "pilot_http_attempts": 0,
            "strict_parser_failure_preserved": True,
            "external_calls": 0, "paid_api_calls": 0,
            "collusion_or_behavior_performance_claimed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.run), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
