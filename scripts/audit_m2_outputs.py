#!/usr/bin/env python3
"""Independently verify the completed M2 call, permission, and artifact ledgers."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.m2_corpus import file_sha256  # noqa: E402
from colluscope.openai_compat_llamacpp import llama_runtime_bundle_identity  # noqa: E402

M2_CONFIG = tomllib.loads((ROOT / "configs/m2-one-shot.toml").read_text(encoding="utf-8"))
MODEL_SHA256 = "d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785"
SERVER_SHA256 = "3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb"
BUNDLE_SHA256 = "9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, start=1):
            if not line.strip():
                raise ValueError(f"blank ledger row: {path}:{line_no}")
            rows.append(json.loads(line))
    return rows


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def audit(out: Path) -> dict:
    prep = _json(out / "preparation-manifest.json")
    plan = _json(out / "private/evaluation-plan.json")
    evals = plan["logical_evaluations"]
    if len(evals) != 1000 or len({row["eval_id"] for row in evals}) != 1000:
        raise ValueError("assigned M2 plan is not exactly 1,000 unique logical evaluations")
    if prep.get("logical_evaluation_count") != 1000 or prep.get("no_model_calls") is not True:
        raise ValueError("M2 preparation manifest is not the frozen no-call plan")
    projection_audit = _json(out / "stage1/preparation-verification.json")
    if (projection_audit.get("status") != "PASS_M2_PREPARATION_PERMISSION_AND_HASH_AUDIT" or
            projection_audit.get("logical_evaluations") != 1000 or
            projection_audit.get("no_model_calls") is not True):
        raise PermissionError("independent pre-inference projection and permission audit did not pass")
    source_hash_check = _json(out / "stage1/m1-source-hashes-after.json")
    if source_hash_check.get("status") != "PASS_M1_SOURCE_HASHES_UNCHANGED":
        raise ValueError("M1 source corpus hashes changed during M2")
    if file_sha256(out / "private/evaluation-plan.json") != prep["hashes"]["evaluation_plan"]:
        raise ValueError("M2 evaluation plan changed after preparation")
    environment = _json(out / "environment.json")
    if (environment.get("model_sha256") != MODEL_SHA256 or
            environment.get("server_sha256") != SERVER_SHA256 or
            environment.get("runtime_bundle_sha256") != BUNDLE_SHA256 or
            environment.get("endpoint") != "http://127.0.0.1:8081/v1" or
            environment.get("offline") is not True or environment.get("third_party_fallback") is not False or
            environment.get("api_spend_usd") != 0.0):
        raise PermissionError("M2 prepared environment differs from the pinned local-only runtime")
    if file_sha256(Path(M2_CONFIG["model_path"])) != MODEL_SHA256 or \
            file_sha256(Path(M2_CONFIG["server_path"])) != SERVER_SHA256 or \
            llama_runtime_bundle_identity(M2_CONFIG["server_path"]).get("sha256") != BUNDLE_SHA256:
        raise PermissionError("M2 checkpoint/server/runtime bundle bytes changed after the run")

    eval_events = _jsonl(out / "evaluation-ledger.jsonl")
    terminal_eval = {}
    for event in eval_events:
        if event.get("event") == "evaluation_terminal":
            terminal_eval[event["eval_id"]] = event.get("status")
    if set(terminal_eval) != {row["eval_id"] for row in evals}:
        missing = len({row["eval_id"] for row in evals} - set(terminal_eval))
        raise ValueError(f"M2 evaluation ledger leaves {missing} assigned rows nonterminal")

    request_events = _jsonl(out / "requests-ledger.jsonl")
    attempt_rows = [row for row in request_events if row.get("event") == "attempt_started"]
    attempt_by_request = Counter(row["request_id"] for row in attempt_rows)
    attempt_pairs = [(row["request_id"], row["attempt"]) for row in attempt_rows]
    if len(attempt_pairs) != len(set(attempt_pairs)):
        raise ValueError("M2 request ledger repeats a physical attempt number")
    if len(attempt_by_request) > 1000 or len(attempt_rows) > 2000 or any(n > 2 for n in attempt_by_request.values()):
        raise RuntimeError("M2 logical, physical, or per-request hard cap was breached")

    request_paths = sorted((out / "requests").glob("m2-*.json"))
    request_rows = {path.stem: _json(path) for path in request_paths}
    if len(request_rows) != plan["unique_payload_count"]:
        raise ValueError("M2 frozen request-file inventory differs from preparation plan")
    for request_id, request in request_rows.items():
        payload_json = request.get("payload_json")
        if not isinstance(payload_json, str) or json.loads(payload_json) != request["payload"]:
            raise ValueError(f"M2 frozen request object/body differ: {request_id}")
        if json.dumps(request["payload"], ensure_ascii=False, separators=(",", ":")) != payload_json:
            raise ValueError(f"M2 request object cannot reproduce the frozen HTTP bytes: {request_id}")
        raw = payload_json.encode("utf-8")
        if _digest(raw) != request["payload_sha256"] or request_id != "m2-" + request["payload_sha256"][:28]:
            raise ValueError(f"M2 request payload hash or ID is invalid: {request_id}")
        if request_id not in attempt_by_request and request.get("input_tokens_local", 99999) <= 3072:
            # An exact logical duplicate or an already not-sent item can have no request only when over cap.
            linked = [row for row in evals if row["request_id"] == request_id]
            if any(row["preparation_status"] == "prepared" for row in linked):
                raise ValueError(f"prepared M2 unique request has no HTTP attempt: {request_id}")

    http_rows = []
    launch_failures = []
    launches = sorted((out / "launches").glob("launch-*"))
    for launch in launches:
        attempts_path = launch / "http-attempts.jsonl"
        launch_http_rows = _jsonl(attempts_path)
        launch_record_path = launch / "launch.json"
        listener_path = launch / "listener-owner-attestation.json"
        if not launch_http_rows and not listener_path.exists():
            summary_path, failure_path = launch / "phase-summary.json", launch / "run-failure.json"
            if not summary_path.exists() or not failure_path.exists():
                raise ValueError(f"M2 launch lacks both an owner attestation and a recorded pre-HTTP failure: {launch.name}")
            phase_failure = _json(failure_path)
            if _json(summary_path).get("model_responses_this_launch") != 0:
                raise ValueError("M2 pre-HTTP launch failure claims model responses")
            key_cleanup = launch / "api-key-cleanup.json"
            if key_cleanup.exists():
                cleanup = _json(key_cleanup)
                if cleanup.get("status") != "REMOVED" or cleanup.get("exists_after_cleanup") is not False:
                    raise PermissionError("M2 pre-HTTP launch left its ephemeral API key file")
            launch_failures.append({"launch_id": launch.name,
                                    "error_type": phase_failure.get("error_type"),
                                    "phase": phase_failure.get("phase")})
            continue
        launch_record = _json(launch_record_path)
        listener = _json(listener_path)
        if (launch_record.get("offline") is not True or launch_record.get("endpoint") != "http://127.0.0.1:8081/v1" or
                launch_record.get("server_sha256") != SERVER_SHA256 or
                launch_record.get("runtime_bundle_sha256") != BUNDLE_SHA256 or
                Path(launch_record.get("image_path", "")).resolve().as_posix().casefold() !=
                Path(M2_CONFIG["server_path"]).resolve().as_posix().casefold()):
            raise PermissionError("M2 launch is not the frozen offline loopback runtime")
        if listener.get("status") != "verified_exact_pid_loopback_listener" or \
                listener.get("pid") != launch_record.get("pid"):
            raise PermissionError("M2 listener-owner attestation does not match the launched process")
        if listener.get("rows") != [{"LocalAddress": "127.0.0.1", "LocalPort": 8081,
                                     "OwningProcess": launch_record["pid"]}]:
            raise PermissionError("M2 server did not own exactly the frozen 127.0.0.1:8081 listener")
        cleanup_path = launch / "api-key-cleanup.json"
        if not cleanup_path.exists():
            raise PermissionError("M2 launch omitted ephemeral API key cleanup evidence")
        cleanup = _json(cleanup_path)
        if cleanup.get("status") != "REMOVED" or cleanup.get("exists_after_cleanup") is not False or \
                Path(cleanup.get("path", "")).exists():
            raise PermissionError("M2 ephemeral API key file was not removed after server shutdown")
        if not launch_http_rows and not (launch / "phase-summary.json").exists():
            raise ValueError(f"M2 launch has no attempt log or terminal summary: {launch.name}")
        for row in launch_http_rows:
            if (row.get("url", "").startswith("http://127.0.0.1:8081/") is False or
                    row.get("listener_pid") != launch_record["pid"] or
                    row.get("api_key_sha256") != launch_record.get("api_key_sha256")):
                raise PermissionError("M2 HTTP attempt escaped the pinned local server/auth profile")
            request = request_rows.get(row.get("request_id"))
            if request is None or row.get("request_body_sha256") != request.get("payload_sha256"):
                raise ValueError("M2 physical HTTP request body does not match its frozen request payload")
            http_rows.append(row)
    if len(http_rows) != len(attempt_rows):
        raise ValueError("request reservations and actual HTTP-attempt log rows differ")
    if {(row.get("request_id"), row.get("attempt")) for row in http_rows} != set(attempt_pairs):
        raise ValueError("M2 request reservation IDs do not match actual physical HTTP attempts")
    if (out / "private/llama-api-key.txt").exists():
        raise PermissionError("M2 per-run local server key remains after completed execution")

    responses = {}
    for response_path in sorted((out / "responses").glob("m2-*.json")):
        response = _json(response_path)
        request_id = response_path.stem
        request = request_rows.get(request_id)
        raw_body, raw_text = response.get("raw_response_body"), response.get("raw_assistant_text")
        if request is None or response.get("payload_sha256") != request.get("payload_sha256"):
            raise ValueError(f"M2 response is not linked to its exact frozen request: {request_id}")
        if not isinstance(raw_body, str) or _digest(raw_body.encode("utf-8")) != response.get("raw_response_body_sha256"):
            raise ValueError(f"M2 raw response body hash mismatch: {request_id}")
        if not isinstance(raw_text, str) or _digest(raw_text.encode("utf-8")) != response.get("raw_assistant_text_sha256"):
            raise ValueError(f"M2 assistant response text hash mismatch: {request_id}")
        if response.get("model") != M2_CONFIG["model_id"]:
            raise ValueError(f"M2 response model alias differs from frozen identity: {request_id}")
        if response.get("validation_status") not in {"valid", "invalid_output"}:
            raise ValueError(f"M2 response has an unknown validator result: {request_id}")
        responses[request_id] = response
    if len(responses) != len(list((out / "responses").glob("m2-*.json"))):
        raise ValueError("M2 response inventory has duplicate request IDs")

    for evaluation in evals:
        request_id = evaluation["request_id"]
        status = terminal_eval[evaluation["eval_id"]]
        if request_id in responses:
            expected = responses[request_id]["validation_status"]
            if status not in {expected, "deduplicated_" + expected}:
                raise ValueError(f"M2 evaluation terminal status disagrees with response: {evaluation['eval_id']}")
        elif status in {"valid", "invalid_output", "deduplicated_valid", "deduplicated_invalid_output"}:
            raise ValueError(f"M2 evaluation claims a returned output that is missing: {evaluation['eval_id']}")

    calibration = _json(out / "calibration-freeze.json")
    if calibration.get("status") != "CALIBRATION_CLOSED_SETTINGS_UNCHANGED":
        raise ValueError("M2 calibration freeze is absent or not closed")
    phases = _jsonl(out / "phase-ledger.jsonl")
    cal_rows = [row for row in phases if row.get("phase") == "calibration"]
    test_rows = [row for row in phases if row.get("phase") == "held_out"]
    if not cal_rows or not test_rows:
        raise ValueError("M2 calibration and held-out phases are not both recorded")
    freeze_time = datetime.fromisoformat(calibration["closed_at_utc"])
    earliest_test = min(datetime.fromisoformat(row["started_at_utc"]) for row in test_rows)
    if earliest_test < freeze_time:
        raise PermissionError("M2 held-out inference began before calibration settings were closed")
    for row in attempt_rows:
        if row.get("phase") == "held_out" and datetime.fromisoformat(row["at_utc"]) < freeze_time:
            raise PermissionError("held-out request attempt predates calibration freeze")

    summary = {"status": "PASS_M2_INDEPENDENT_CALL_AND_ARTIFACT_AUDIT",
        "audited_at_utc": datetime.now().astimezone().isoformat(),
        "assigned_logical_evaluations": len(evals),
        "terminal_logical_evaluations": len(terminal_eval),
        "prepared_unique_payloads": len(request_rows),
        "physical_http_attempts": len(http_rows),
        "unique_response_files": len(responses),
        "pre_http_launch_failures_retained": launch_failures,
        "valid_response_files": sum(row["validation_status"] == "valid" for row in responses.values()),
        "invalid_response_files": sum(row["validation_status"] == "invalid_output" for row in responses.values()),
        "requests_all_loopback": all(row.get("url", "").startswith("http://127.0.0.1:8081/") for row in http_rows),
        "external_model_fallback_configured": False,
        "paid_api_spend_usd": 0,
        "source_m1_corpus_manifest_sha256": _json(out / "stage1/source-validation.json")["original_corpus_manifest_sha256"],
        "preparation_manifest_sha256": file_sha256(out / "preparation-manifest.json"),
        "calibration_freeze_sha256": file_sha256(out / "calibration-freeze.json"),
        "response_file_hashes": {request_id: file_sha256(out / "responses" / f"{request_id}.json")
                                  for request_id in sorted(responses)},
        "request_file_hashes": {request_id: file_sha256(out / "requests" / f"{request_id}.json")
                                 for request_id in sorted(request_rows)},
    }
    write_path = out / "independent-audit-summary.json"
    write_path.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                          encoding="utf-8", newline="\n")
    inventory = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "artifact-hashes.json":
            inventory.append({"path": path.relative_to(out).as_posix(), "size_bytes": path.stat().st_size,
                              "sha256": file_sha256(path)})
    hash_doc = {"schema_version": "colluscope-m2-artifact-hashes-v1",
                "run_path": str(out.resolve()), "file_count_excluding_this_manifest": len(inventory),
                "files": inventory}
    (out / "artifact-hashes.json").write_text(json.dumps(hash_doc, ensure_ascii=False,
        sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, sort_keys=True))
    return summary


def write_path(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=ROOT / "runs/m2/one-shot-20261019")
    args = parser.parse_args()
    out = args.run.resolve()
    if not out.is_relative_to(ROOT / "runs/m2"):
        raise ValueError("M2 audit must read/write only the local Git-ignored run root")
    audit(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
