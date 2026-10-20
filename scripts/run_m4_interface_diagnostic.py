#!/usr/bin/env python3
"""Run the fixed 18-generation M4 v4 action-interface diagnostic after separate approval."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope import m4_live_runtime as live  # noqa: E402
from colluscope.m4_action_interface_v4 import parse_action  # noqa: E402

CONFIG = ROOT / "configs/m4-live-runtime-v4.json"
SCHEDULE = ROOT / "configs/m4-interface-diagnostic-v1.json"
DEFAULT_OUT = ROOT / "runs/m4/recovery-diagnostic-v1"
MAX_GENERATIONS = 18
ARTIFACT_PATHS = (
    "configs/m4-live-runtime-v4.json",
    "configs/m4-interface-diagnostic-v1.json",
    "src/colluscope/m4_live_runtime.py",
    "src/colluscope/m4_action_interface_v4.py",
    "scripts/run_m4_interface_diagnostic.py",
    "scripts/audit_m4_interface_diagnostic.py",
    "scripts/run_m4_live.py",
    "scripts/audit_m4_live.py",
    "scripts/run_m4_offline.py",
    "scripts/local_llama_security.py",
    "scripts/run_m1_p0_local_preflight.py",
)


def _artifact_hashes() -> dict[str, str]:
    return {relative: live.sha_file(ROOT / relative) for relative in ARTIFACT_PATHS}


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()


def _approval(path: Path, approval_id: str, config_hash: str) -> dict[str, Any]:
    allowed_root = (ROOT / "runs/m4/recovery-diagnostic-v1").resolve()
    path = path.resolve()
    if allowed_root not in path.parents or not path.is_file():
        raise live.M4AuthorizationRequired("diagnostic approval receipt must be stored under the private M4 recovery root")
    receipt = json.loads(path.read_bytes())
    schedule_hash = live.sha_file(SCHEDULE)
    required = {"schema_version", "authorization_id", "protocol_id", "config_sha256", "schedule_sha256",
                "max_generation_attempts", "retries", "replacement_groups", "external_inference"}
    if (set(receipt) != required
            or receipt.get("schema_version") != "m4-interface-diagnostic-authorization-v1"
            or receipt.get("authorization_id") != approval_id
            or receipt.get("protocol_id") != "m4-interface-diagnostic-v1"
            or receipt.get("config_sha256") != config_hash
            or receipt.get("schedule_sha256") != schedule_hash
            or receipt.get("max_generation_attempts") != MAX_GENERATIONS
            or receipt.get("retries") != 0 or receipt.get("replacement_groups") != 0
            or receipt.get("external_inference") is not False):
        raise live.M4AuthorizationRequired("diagnostic authorization receipt does not match the frozen 18-call local scope")
    return {"path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _rows() -> list[dict[str, Any]]:
    schedule = json.loads(SCHEDULE.read_bytes())
    rows = schedule["rows"]
    if (schedule.get("protocol_id") != "m4-interface-diagnostic-v1"
            or schedule.get("maximum_physical_generation_attempts") != MAX_GENERATIONS
            or len(rows) != MAX_GENERATIONS):
        raise live.M4LiveError("frozen M4 action-interface diagnostic schedule is invalid")
    return rows


def _prompts(config_path: Path = CONFIG) -> list[dict[str, Any]]:
    from scripts import run_m4_offline as frozen

    _live, _base, scenarios, splits, positive = live.load_live_config(config_path)
    groups = {}
    for group in splits["groups"]:
        groups.setdefault(group["scenario_family_id"], group)
    by_family = {row["scenario_family_id"]: row for row in scenarios["families"]}
    groups_by_id = {row["split_group_id"]: row for row in splits["groups"]}
    prompts = []
    for row in _rows():
        group = groups_by_id.get(row["split_group_id"])
        family_id = row["scenario_family_id"]
        if (group is None or group != groups.get(family_id)
                or group["seed_block_id"] != row["seed_block_id"]):
            raise live.M4LiveError("diagnostic group selection differs from first-per-family frozen rule")
        scenario = by_family[family_id]
        chair = "ABC"[int(group["seed_block_id"].split("-")[-1]) % 3]
        task = frozen._task_spec(scenario, chair)
        if row["action_kind"] == "message":
            agent = "A"
            observation = frozen._observation(agent, task, [], None, include_private_rule=True)
            prompt = frozen.render_prompt("message", observation)
        elif row["action_kind"] == "ballot":
            agent = "B"
            observation = frozen._observation(
                agent, task, [], {"type": "no_message"}, include_private_rule=True)
            prompt = frozen.render_prompt("ballot", observation)
        elif row["action_kind"] == "positive_control":
            agent = "B"
            task_prompt = positive["task"]["prompt"]
            signal = group["positive_control_signal"]
            stimulus = positive["paired_messages"]["information_template"].format(signal=signal)
            observation = {"task_prompt": task_prompt, "peer_message": stimulus}
            prompt = frozen.render_positive_prompt(task_prompt, stimulus)
        else:
            raise live.M4LiveError("unknown action kind in fixed diagnostic schedule")
        prompts.append({"request_id": row["request_id"], "group": group,
                        "action_kind": row["action_kind"], "agent": agent,
                        "observation": observation, "prompt": prompt})
    if len(prompts) != MAX_GENERATIONS:
        raise live.M4LiveError("materialized diagnostic call graph differs from 18 requests")
    return prompts


def run(out: Path, *, approval_id: str, approval_receipt: Path) -> dict[str, Any]:
    config, base, _scenarios, _splits, _positive = live.load_live_config(CONFIG)
    config_hash = live.sha_file(CONFIG)
    approval = _approval(approval_receipt, approval_id, config_hash)
    schedule_rows = _rows()
    prompt_rows = _prompts()
    out = out.resolve()
    allowed_out = (ROOT / "runs/m4/recovery-diagnostic-v1").resolve()
    if allowed_out not in out.parents:
        raise live.M4LiveError("diagnostic raw output must stay under the Git-ignored private M4 root")
    if (ROOT / ".gitignore").read_text(encoding="utf-8").replace("\\", "/").find("/runs/m4/") < 0:
        raise live.M4LiveError("private M4 output root is not Git-ignored")
    out.mkdir(parents=True, exist_ok=True)
    from scripts.local_llama_security import restrict_private_directory_acl, verify_private_directory_acl
    acl = restrict_private_directory_acl(out) if not any(out.iterdir()) else verify_private_directory_acl(out)
    if acl.get("verified") is not True:
        raise PermissionError("diagnostic output directory ACL is not private")
    manifest = {
        "schema_version": "m4-interface-diagnostic-run-v1",
        "protocol_id": "m4-interface-diagnostic-v1",
        "execution_mode": "live_local_llama_cpp",
        "historical_behavioral_episode": False,
        "inference_authorized_by_runtime": False,
        "explicit_approval_id": approval_id,
        "authorization_receipt": approval,
        "config_sha256": config_hash,
        "schedule_sha256": live.sha_file(SCHEDULE),
        "artifact_sha256": _artifact_hashes(),
        "python_version": sys.version,
        "generation_attempt_limit": MAX_GENERATIONS,
        "retry_limit": 0, "replacement_limit": 0,
        "model": config["model"], "runtime": config["runtime"],
        "tokenizer": config["tokenizer"], "sampling": config["sampling"],
        "prompt_sha256_by_request": {row["request_id"]: live.sha(row["prompt"].encode("utf-8"))
                                     for row in prompt_rows},
        "private_storage_acl": acl,
    }
    manifest_path = out / "diagnostic_manifest.json"
    manifest_bytes = live.canonical(manifest) + b"\n"
    if manifest_path.exists() and manifest_path.read_bytes() != manifest_bytes:
        raise live.M4LiveError("refusing to resume diagnostic with a changed protocol/config/approval")
    if not manifest_path.exists():
        _write_once(manifest_path, manifest_bytes)
    attempts_path = out / "attempts.jsonl"
    existing = live.read_jsonl(attempts_path)
    started_ids = {row["request_id"] for row in existing if row.get("event") == "attempt_started"}
    terminal_ids = {row["request_id"] for row in existing if row.get("event") == "attempt_terminal"}
    if len(started_ids) > MAX_GENERATIONS or not started_ids <= {r["request_id"] for r in schedule_rows}:
        raise live.M4LiveError("diagnostic attempt ledger exceeds cap or contains unscheduled requests")
    if started_ids - terminal_ids:
        raise live.M4LiveError("diagnostic has an unresolved started request; never resending it")
    frozen_identity = live.verify_frozen_assets(config)
    token_counter = frozen_identity.pop("token_counter")
    _server, api_key, key_path, streams, server_identity = live._start_server(out, config)
    errors = []
    try:
        client = live.GenerationClient(out=out, config=config, api_key=api_key,
                                       token_counter=token_counter,
                                       endpoint=config["runtime"]["endpoint"],
                                       listener_guard=server_identity["process_guard"],
                                       max_generation_attempts=MAX_GENERATIONS)
        for row in prompt_rows:
            rid = row["request_id"]
            if rid in started_ids:
                continue
            try:
                action, _receipt = client.generate(
                    rid, row["group"]["split_group_id"], row["action_kind"], row["agent"],
                    row["prompt"], row["observation"], arm="interface_diagnostic",
                    seed_agent=row["agent"], comparison={"diagnostic_only": True,
                                                         "scenario_family_id": row["group"]["scenario_family_id"]})
                raw_response = json.loads((out / "responses" / f"{rid}.body").read_bytes())
                message = raw_response["choices"][0]["message"]
                action_again, _ = parse_action(message, row["action_kind"], live._validate_action)
                if action_again != action:
                    raise live.M4LiveError("offline replay of diagnostic parser changed the returned action")
                import jsonschema
                jsonschema.validate(action, json.loads((out / "requests" / f"{rid}.json").read_bytes())
                                     ["response_format"]["schema"])
            except live.M4RequestFailure as exc:
                errors.append({"request_id": rid, "status": exc.status})
                if exc.status == "SERVER_IDENTITY_MISMATCH":
                    break
        attempts = live.read_jsonl(attempts_path)
        terminal = {row["request_id"]: row for row in attempts if row.get("event") == "attempt_terminal"}
        started = [row for row in attempts if row.get("event") == "attempt_started"]
        summary = {"protocol_id": "m4-interface-diagnostic-v1",
                   "status": "DIAGNOSTIC_COLLECTED" if len(started) == len(terminal) == MAX_GENERATIONS else "INCOMPLETE_NO_RESAMPLE",
                   "assigned_generations": MAX_GENERATIONS,
                   "started_generations": len(started), "terminal_generations": len(terminal),
                   "completed_schema_valid_generations": sum(row.get("status") == "COMPLETED"
                                                               for row in terminal.values()),
                   "failed_generations": sum(row.get("status") != "COMPLETED" for row in terminal.values()),
                   "hard_generation_cap": MAX_GENERATIONS, "retries": 0, "replacement_groups": 0,
                   "per_action_kind": {kind: {"assigned": sum(r["action_kind"] == kind for r in schedule_rows),
                                              "completed": sum(terminal.get(r["request_id"], {}).get("status") == "COMPLETED"
                                                               for r in schedule_rows if r["action_kind"] == kind)}
                                       for kind in ("message", "ballot", "positive_control")},
                   "errors": errors, "real_model_calls": len(started),
                   "historical_results_modified": False,
                   "behavioral_effect_or_collusion_claimed": False}
        live.write_json(out / "diagnostic_summary.json", summary)
        return summary
    finally:
        from scripts.run_m1_p0_local_preflight import _stop_own_process
        from scripts.local_llama_security import remove_api_key_file
        live.append_jsonl(out / "server_sessions.jsonl", {"event": "server_stopped",
                          **_stop_own_process(_server), "at_utc": live.utc_now()})
        live.append_jsonl(out / "key_cleanups.jsonl", {**remove_api_key_file(key_path), "at_utc": live.utc_now()})
        for stream in streams:
            stream.close()
        live.append_jsonl(out / "storage_audits.jsonl", {"phase": "after_run",
                          **verify_private_directory_acl(out), "at_utc": live.utc_now()})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="explicit live flag; still requires a signed-off receipt")
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT / "run")
    args = parser.parse_args()
    if not args.live:
        raise live.M4AuthorizationRequired("M4 interface diagnostic is disabled without --live and an approval receipt")
    result = run(args.out, approval_id=args.approval_id, approval_receipt=args.authorization_receipt)
    print(json.dumps(result, sort_keys=True))
    return 0 if (result["status"] == "DIAGNOSTIC_COLLECTED"
                  and result["completed_schema_valid_generations"] == MAX_GENERATIONS) else 2


if __name__ == "__main__":
    raise SystemExit(main())
