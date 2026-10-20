"""Freeze or run one matched, two-condition local Colosseum seed pair.

Real inference is reachable only with --run and is intentionally not invoked by
this repository's offline tests. Each assigned episode counts, even if it
fails. No retries or replacement episodes are allowed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "reproductions" / "colosseum_local" / "run_local_repro.py"
COMPAT_PATH = ROOT / "reproductions" / "colosseum_local" / "runtime_compat.py"
DEFAULT_OUT = ROOT / "reference" / "colosseum" / "experiments" / "collusion" / "outputs" / "colluscope-pair-v2-seed1-final3"
PAIR_MAX_HTTP = 2 * 6 * (4 + 1) * 3


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def load_runner():
    spec = importlib.util.spec_from_file_location("colluscope_colosseum_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load pinned local runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RawHttpCapture:
    """Store exact local request/response bytes without capturing auth headers."""

    def __init__(self, root: Path):
        self.root = root
        self.episode_id = "bootstrap"
        ledger = root / "http_requests.jsonl"
        self.count = 0
        if ledger.exists():
            for line_no, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"malformed HTTP ledger at line {line_no}; refusing raw-file overwrite") from exc
                if row.get("event") == "http_attempt_started":
                    self.count += 1

    @staticmethod
    def _body(kwargs: dict[str, Any]) -> bytes | None:
        body = kwargs.get("data")
        if body is None and kwargs.get("json") is not None:
            body = json.dumps(kwargs["json"], sort_keys=True, ensure_ascii=False)
        if isinstance(body, str):
            return body.encode("utf-8")
        if isinstance(body, bytes):
            return body
        return None

    def request(self, original, session, method, url, **kwargs):
        self.count += 1
        attempt = self.count
        directory = self.root / "raw" / "http" / self.episode_id
        directory.mkdir(parents=True, exist_ok=True)
        stem = f"attempt-{attempt:04d}"
        body = self._body(kwargs)
        index: dict[str, Any] = {
            "attempt": attempt,
            "episode_id": self.episode_id,
            "method": str(method),
            "url": str(url),
            "request_body_sha256": hashlib.sha256(body).hexdigest().upper() if body is not None else None,
            "request_body_recorded": body is not None,
        }
        if body is not None:
            (directory / f"{stem}.request.bin").write_bytes(body)
        try:
            response = original(session, method, url, **kwargs)
        except Exception as exc:
            index.update({"status": "transport_exception", "exception_type": type(exc).__name__})
            append_index(directory / "index.jsonl", index)
            raise
        response_body = bytes(response.content)
        response_path = directory / f"{stem}.response.bin"
        response_path.write_bytes(response_body)
        index.update({
            "status_code": int(response.status_code),
            "response_body_sha256": hashlib.sha256(response_body).hexdigest().upper(),
            "response_body_bytes": len(response_body),
            "response_body_path": response_path.name,
        })
        try:
            payload = response.json()
            choices = payload.get("choices") or []
            if choices:
                choice = choices[0]
                message = choice.get("message") or {}
                calls = message.get("tool_calls") or []
                index.update({
                    "finish_reason": choice.get("finish_reason"),
                    "assistant_role": message.get("role"),
                    "tool_call_count": len(calls) if isinstance(calls, list) else None,
                    "tool_names": [
                        (call.get("function") or {}).get("name")
                        for call in calls if isinstance(call, dict)
                    ] if isinstance(calls, list) else None,
                    "tool_argument_sha256": [
                        hashlib.sha256(str((call.get("function") or {}).get("arguments", "")).encode()).hexdigest().upper()
                        for call in calls if isinstance(call, dict)
                    ] if isinstance(calls, list) else None,
                })
        except (ValueError, AttributeError, TypeError, KeyError):
            index["finish_reason"] = None
            index["response_json_parse"] = "failed_or_noncompletion_response"
        append_index(directory / "index.jsonl", index)
        return response


def append_index(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def configure_runner(runner: Any, seed: int, out: Path) -> None:
    if seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    runner.SEEDS = (seed,)
    runner.MAX_HTTP_ATTEMPTS = PAIR_MAX_HTTP
    runner.OUT_ROOT = out


def freeze_pair(runner: Any, out: Path, seed: int) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = runner.write_freeze()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["protocol_id"] = "colosseum-jira-local-qwen3-paired-v2"
    manifest["pair_design"] = {
        "seed": seed,
        "conditions": ["no_secret_control", "secret_channel_control"],
        "order": "no_secret_control then secret_channel_control",
        "matched_seed_is_not_common_random_numbers": True,
    }
    manifest["compatibility_adapter"] = {
        "source": str(COMPAT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256_file(COMPAT_PATH),
        "semantics": "no-tool assistant is terminal; execution without committed action fails; malformed tool arguments are rejected before callback",
    }
    manifest["pair_runner"] = {
        "source": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256_file(Path(__file__).resolve()),
    }
    manifest["raw_http_capture"] = {
        "request_and_response_bytes": "local-only, one file per physical attempt",
        "auth_headers_captured": False,
        "finish_reason_and_tool_names": "indexed when a completion response exists",
    }
    manifest["budget"] = {
        "assigned_episodes": 2,
        "logical_generations_max": PAIR_MAX_HTTP,
        "physical_http_attempts_max": PAIR_MAX_HTTP,
        "retries": 0,
        "derivation": "2 conditions * 6 agents * (4 planning turns + 1 execution turn) * 3 generations",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    # Store the finalized manifest digest in a separate receipt to avoid a
    # self-referential hash.
    freeze_receipt = {
        "manifest_sha256_after_metadata": sha256_file(manifest_path),
        "runner_sha256": manifest["orchestration_sha256"],
        "pair_runner_sha256": manifest["pair_runner"]["sha256"],
        "compatibility_adapter_sha256": manifest["compatibility_adapter"]["sha256"],
        "seed": seed,
        "http_hard_cap": PAIR_MAX_HTTP,
    }
    (out / "pair_freeze_receipt.json").write_text(json.dumps(freeze_receipt, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def verify_pair_freeze(runner: Any, out: Path, seed: int) -> dict[str, Any]:
    manifest = runner.validate_freeze(out)
    if manifest.get("protocol_id") != "colosseum-jira-local-qwen3-paired-v2":
        raise RuntimeError("wrong protocol id")
    if manifest.get("pair_design", {}).get("seed") != seed:
        raise RuntimeError("seed does not match frozen pair")
    if manifest.get("budget", {}).get("physical_http_attempts_max") != PAIR_MAX_HTTP:
        raise RuntimeError("pair HTTP cap is not the frozen 180")
    if manifest.get("pair_runner", {}).get("sha256") != sha256_file(Path(__file__).resolve()):
        raise RuntimeError("pair runner changed after freeze")
    if manifest.get("compatibility_adapter", {}).get("sha256") != sha256_file(COMPAT_PATH):
        raise RuntimeError("compatibility adapter changed after freeze")
    ids = [row["episode_id"] for row in manifest.get("frozen_configurations", [])]
    expected = [f"no_secret_control__seed{seed}", f"secret_channel_control__seed{seed}"]
    if ids != expected:
        raise RuntimeError(f"frozen pair IDs/order mismatch: {ids}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    out = args.out.resolve()
    runner = load_runner()
    configure_runner(runner, args.seed, out)
    if args.freeze_only:
        path = freeze_pair(runner, out, args.seed)
        print(json.dumps({"status": "frozen_no_model_calls", "manifest": str(path), "sha256": sha256_file(path), "hard_cap": PAIR_MAX_HTTP}))
        return 0

    verify_pair_freeze(runner, out, args.seed)
    set_sys_path = str(runner.UPSTREAM)
    if set_sys_path not in sys.path:
        sys.path.insert(0, set_sys_path)
    spec = importlib.util.spec_from_file_location("colluscope_runtime_compat", COMPAT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load runtime compatibility adapter")
    compat = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = compat
    spec.loader.exec_module(compat)
    compat.install_colosseum_compat(str(runner.UPSTREAM))

    capture = RawHttpCapture(out)
    prior_request = requests.Session.request
    requests.Session.request = lambda session, method, url, **kwargs: capture.request(prior_request, session, method, url, **kwargs)
    original_set_episode = runner.RequestGuard.set_episode
    def set_episode_with_capture(guard, episode_id):
        original_set_episode(guard, episode_id)
        capture.episode_id = episode_id
    runner.RequestGuard.set_episode = set_episode_with_capture
    try:
        runner.set_safe_environment()
        guard = runner.RequestGuard(out / "http_requests.jsonl", hard_cap=PAIR_MAX_HTTP)
        guard.install()
        runner.run_all(out, guard)
    finally:
        requests.Session.request = prior_request
        runner.RequestGuard.set_episode = original_set_episode
    print(json.dumps({"status": "pair_finished_with_all_rows_preserved", "http_attempts": guard.attempts, "hard_cap": PAIR_MAX_HTTP, "output": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
