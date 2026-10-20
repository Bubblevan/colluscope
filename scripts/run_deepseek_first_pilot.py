#!/usr/bin/env python3
"""Bounded actual DeepSeek strict-tool pilot with one preregistered JSON fallback."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.deepseek_m4_v1 import (  # noqa: E402
    DeepSeekClient, DeepSeekRequestError, agent_tool, append_jsonl, canonical,
    monitor_tool, now_utc, read_jsonl, request_payload, sha, validate_agent_arguments,
    validate_monitor_arguments, write_once,
)
from colluscope import m4_live_runtime as m4  # noqa: E402
from scripts import run_m4_offline as offline  # noqa: E402
from scripts import run_monitor_recovery_diagnostic as diag  # noqa: E402
from scripts.local_llama_security import (  # noqa: E402
    restrict_private_directory_acl, verify_private_directory_acl,
)
from scripts.run_m4_deepseek_v1 import _load_key, _messages  # noqa: E402
from colluscope.sprint_baselines import TASK_DEFINITIONS, build_monitor_payload  # noqa: E402
from colluscope.deepseek_monitor_v1 import _monitor_messages  # noqa: E402

RUN_ROOT = ROOT / "runs/deepseek-first-m4"
PILOT_ROOT = RUN_ROOT / "pilot"
GLOBAL_BUDGET = RUN_ROOT / "global_budget_ledger.jsonl"
SCHEDULE_PATH = ROOT / "configs/monitor-recovery-diagnostic-v1.json"
CONTROL_PATH = ROOT / "data/sprint-baseline-v1/controls.jsonl"
PLAN_PATH = PILOT_ROOT / "frozen-plan.json"


def _secure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    result = restrict_private_directory_acl(path) if not any(path.iterdir()) else verify_private_directory_acl(path)
    if result.get("verified") is not True:
        raise PermissionError(f"ACL verification failed for {path}")


def _agent_schedule(interface: str) -> list[dict[str, Any]]:
    _base, scenarios, splits, positive = offline.load_documents()
    group = splits["groups"][0]
    family = next(row for row in scenarios["families"] if row["scenario_family_id"] == group["scenario_family_id"])
    task = offline._task_spec(family, "ABC"[int(group["seed_block_id"].split("-")[-1]) % 3])
    rows = []
    messages = []
    for agent, probe in (("A", "send_message"), ("B", "no_message")):
        observation = offline._observation(agent, task, [], None, include_private_rule=True)
        messages.append({"request_id": f"pilot-agent-{interface}-message-{agent}",
            "kind": "message", "agent": agent, "observation": observation,
            "messages": _messages("message", observation, interface, probe=probe),
            "expected_probe_action": probe})
    for agent in ("A", "B", "C"):
        observation = offline._observation(agent, task, [], None, include_private_rule=agent in {"A", "B"})
        messages.append({"request_id": f"pilot-agent-{interface}-ballot-{agent}",
            "kind": "ballot", "agent": agent, "observation": observation,
            "messages": _messages("ballot", observation, interface), "expected_probe_action": None})
    for index, (signal, arm, text) in enumerate((
        ("GOLD", "information-gold", positive["paired_messages"]["information_template"].format(signal="GOLD")),
        ("BLUE", "information-blue", positive["paired_messages"]["information_template"].format(signal="BLUE")),
        ("GOLD", "neutral", positive["paired_messages"]["neutral_message"]),
    )):
        obs = {"task_prompt": positive["task"]["prompt"], "peer_message": text}
        messages.append({"request_id": f"pilot-agent-{interface}-positive-{arm}",
            "kind": "positive_control", "agent": "receiver", "observation": obs,
            "messages": _messages("positive_control", obs, interface,
                task_prompt=obs["task_prompt"], peer_message=text), "expected_probe_action": None})
    if interface == "strict_function_calling":
        return messages[:8]
    return [messages[0], messages[1], messages[2], messages[5]]


def _monitor_schedule(interface: str) -> list[dict[str, Any]]:
    schedule = json.loads(SCHEDULE_PATH.read_bytes())
    controls = {row["case_ref"]: row for row in
        (json.loads(line) for line in CONTROL_PATH.read_text(encoding="utf-8").splitlines() if line)}
    strict_ids = [f"mrd1-{i:02d}" for i in range(1, 13)]
    fallback_ids = ["mrd1-01", "mrd1-02", "mrd1-03", "mrd1-04", "mrd1-09", "mrd1-15"]
    selected_ids = strict_ids if interface == "strict_function_calling" else fallback_ids
    rows = []
    for old in schedule["rows"]:
        if old["request_id"] not in selected_ids:
            continue
        source = controls[old["case_ref"]]
        _old_payload, evidence = build_monitor_payload(source, old["baseline_id"],
                                                        old["task"], old["permission"])
        task = TASK_DEFINITIONS[old["task"]]
        rid = "pilot-monitor-" + interface + "-" + old["request_id"]
        rows.append({"request_id": rid, "source_id": old["request_id"],
            "case_ref": old["case_ref"], "task": old["task"], "permission": old["permission"],
            "baseline_id": old["baseline_id"], "evidence": evidence, "source": source,
            "messages": _monitor_messages(task=old["task"], evidence=evidence, interface=interface),
            "allowed_labels": list(task["allowed_labels"])})
    # For the predeclared fallback subset, retain the original order above.
    return rows


def _strict_rejection(client: DeepSeekClient, request_id: str, exc: DeepSeekRequestError) -> bool:
    if exc.status != "HTTP_400":
        return False
    path = client.run_dir / "responses" / f"{request_id}.bin"
    if not path.is_file():
        return False
    try:
        body = json.loads(path.read_bytes())
    except Exception:
        return False
    error = body.get("error", body)
    if not isinstance(error, dict):
        return False
    message = " ".join(str(error.get(key, "")) for key in ("message", "type", "code")).casefold()
    # Only explicit capability rejections unlock the preregistered JSON fallback.
    # Invalid schema/parameters, auth failures, and generic 400s are not evidence
    # that Strict Function Calling is unavailable.
    capability_phrases = (
        "strict function calling is not supported",
        "strict function calling is unsupported",
        "function calling is not supported",
        "tool calling is not supported",
        "tools are not supported",
        "tool_choice is not supported",
        "tool choice is not supported",
        "does not support strict function calling",
        "does not support tool calling",
        "unsupported tool_choice",
        "unsupported tool choice",
    )
    return any(phrase in message for phrase in capability_phrases)


def _freeze_pilot_plan() -> dict[str, Any]:
    rows = []
    for interface in ("strict_function_calling", "json_object_fallback"):
        for item in _agent_schedule(interface):
            tool_name, schema = agent_tool(item["kind"])
            body = canonical(request_payload(interface=interface, messages=item["messages"],
                                             tool_name=tool_name, schema=schema))
            rows.append({"request_id": item["request_id"], "role": "agent", "interface": interface,
                         "action_kind": item["kind"], "body_sha256": sha(body),
                         "prompt_sha256": sha(canonical(item["messages"])),
                         "probe_action": item["expected_probe_action"]})
        for item in _monitor_schedule(interface):
            tool_name, schema = monitor_tool(item["allowed_labels"])
            body = canonical(request_payload(interface=interface, messages=item["messages"],
                                             tool_name=tool_name, schema=schema))
            rows.append({"request_id": item["request_id"], "role": "monitor", "interface": interface,
                         "task": item["task"], "baseline_id": item["baseline_id"],
                         "permission": item["permission"], "source_id_not_sent": item["source_id"],
                         "body_sha256": sha(body), "prompt_sha256": sha(canonical(item["messages"]))})
    code_paths = (
        ROOT / "src/colluscope/deepseek_m4_v1.py",
        ROOT / "src/colluscope/deepseek_monitor_v1.py",
        ROOT / "src/colluscope/deepseek_m4_audit.py",
        ROOT / "scripts/run_deepseek_first_pilot.py",
        ROOT / "scripts/run_deepseek_first_research.py",
        ROOT / "scripts/audit_deepseek_first_research.py",
        ROOT / "tests/test_deepseek_m4_v1.py",
        ROOT / "tests/test_deepseek_m4_audit.py",
        ROOT / "tests/test_deepseek_monitor_v1.py",
        ROOT / "tests/test_deepseek_research_audit.py",
        ROOT / "scripts/run_m4_deepseek_v1.py",
        ROOT / "scripts/freeze_deepseek_monitor_v1.py",
        ROOT / "scripts/run_deepseek_monitor_v1.py",
        ROOT / "scripts/prepare_full_research_monitor.py",
        ROOT / "scripts/run_m4_offline.py",
        ROOT / "src/colluscope/m4_live_runtime.py",
        ROOT / "src/colluscope/sprint_baselines.py",
        ROOT / "src/colluscope/sprint_replay.py",
    )
    source_hashes = {path.relative_to(ROOT).as_posix(): sha(path.read_bytes()) for path in (
        ROOT / ".gitignore",
        ROOT / "configs/m4-scenarios-v1.json", ROOT / "configs/m4-splits-v1.json",
        ROOT / "configs/m4-positive-control-v2.json", ROOT / "configs/m4-runtime-v2.json",
        ROOT / "configs/m4-deepseek-agent-v1.json", ROOT / "configs/m4-deepseek-monitor-v1.json",
        ROOT / "COLLUSCOPE_PERSISTENT_RESEARCH_GOAL.md", ROOT / "Codex_Continuous_Goal.md",
        ROOT / "docs/M4_DEEPSEEK_AGENT_V1_PROTOCOL.md",
        ROOT / "docs/M4_DEEPSEEK_MONITOR_V1_PROTOCOL.md",
        SCHEDULE_PATH, CONTROL_PATH,
        ROOT / "prompts/m4-deepseek-agent-v1/agent-system.txt",
        ROOT / "prompts/m4-deepseek-agent-v1/monitor-system.txt")}
    source_hashes.update({path.relative_to(ROOT).as_posix(): sha(path.read_bytes()) for path in code_paths})
    return {"schema_version": "deepseek-compatibility-pilot-freeze-v1",
        "protocol_sha256": sha((ROOT / "docs/M4_DEEPSEEK_AGENT_V1_PROTOCOL.md").read_bytes()),
        "config_sha256": sha((ROOT / "configs/m4-deepseek-agent-v1.json").read_bytes()),
        "source_hashes": source_hashes, "rows": rows,
        "environment": {"python": sys.version, "platform": platform.platform()},
        "max_actual_calls": 30, "retry_limit": 0, "replacement_limit": 0}


def _pilot_plan_hash(request_id: str) -> str:
    plan = json.loads(PLAN_PATH.read_bytes())
    matches = [r for r in plan["rows"] if r["request_id"] == request_id]
    if len(matches) != 1:
        raise RuntimeError(f"request ID is missing/duplicated in frozen pilot plan: {request_id}")
    return matches[0]["body_sha256"]


def _run_agent(interface: str) -> tuple[list[dict[str, Any]], bool, bool]:
    out = PILOT_ROOT / f"agent-{interface.replace('_', '-')}"
    _secure_dir(out)
    client = DeepSeekClient(run_dir=out, budget_ledger=GLOBAL_BUDGET,
                            api_key=_load_key(), interface=interface)
    results, compat_rejection = [], False
    for row in _agent_schedule(interface):
        name, schema = agent_tool(row["kind"])
        rid = row["request_id"]
        try:
            action, rec = client.call(request_id=rid, role="agent", messages=row["messages"],
                tool_name=name, schema=schema,
                semantic=lambda value, k=row["kind"]: validate_agent_arguments(k, value),
                metadata={"pilot": True, "action_kind": row["kind"], "agent": row["agent"],
                          "probe_action": row["expected_probe_action"]},
                expected_request_sha256=_pilot_plan_hash(rid))
            results.append({"request_id": rid, "action_kind": row["kind"], "status": "VALID",
                "action": action, "expected_probe_action": row["expected_probe_action"],
                "request_sha256": rec["request_sha256"], "response_sha256": rec["response_sha256"],
                "finish_reason": rec["finish_reason"], "prompt_tokens": rec["prompt_tokens"]})
        except DeepSeekRequestError as exc:
            results.append({"request_id": rid, "action_kind": row["kind"],
                            "status": exc.status, "error": str(exc)})
            if _strict_rejection(client, rid, exc):
                compat_rejection = True
                break
            return results, False, True
    if interface == "strict_function_calling":
        seen = {"message": set(), "ballot": set(), "positive_control": set()}
        for row in results:
            if row["status"] != "VALID":
                continue
            action = row["action"]
            seen[row["action_kind"]].add(action.get("type") if row["action_kind"] != "positive_control" else action.get("choice"))
        gate = (len(results) == 8 and all(r["status"] == "VALID" for r in results)
                and seen["message"] >= {"send_message", "no_message"}
                and seen["ballot"] >= {"ballot"}
                and bool(seen["positive_control"]))
    else:
        gate = (len(results) == 4 and all(r["status"] == "VALID" for r in results)
                and {r["action"].get("type") for r in results if r["action_kind"] == "message"}
                    >= {"send_message", "no_message"}
                and any(r["action_kind"] == "ballot" for r in results)
                and any(r["action_kind"] == "positive_control" for r in results))
    return results, compat_rejection, (not gate and not compat_rejection)


def _citation_valid(row: dict[str, Any], prediction: dict[str, Any]) -> bool:
    visible = {event.get("event_id") for event in row["evidence"].get("events", [])}
    refs = prediction.get("evidence_refs", [])
    return all(ref in visible for ref in refs)


def _run_monitor(interface: str) -> tuple[list[dict[str, Any]], bool, bool]:
    out = PILOT_ROOT / f"monitor-{interface.replace('_', '-')}"
    _secure_dir(out)
    client = DeepSeekClient(run_dir=out, budget_ledger=GLOBAL_BUDGET,
                            api_key=_load_key(), interface=interface)
    rows, compatibility_rejection, hard_failure = [], False, False
    requests = _monitor_schedule(interface)
    for item in requests:
        name, schema = monitor_tool(item["allowed_labels"])
        try:
            prediction, rec = client.call(request_id=item["request_id"], role="monitor",
                messages=item["messages"], tool_name=name, schema=schema,
                semantic=lambda value, task=item["task"], labels=item["allowed_labels"]:
                    validate_monitor_arguments(task, labels, value),
                metadata={"pilot": True, "task": item["task"], "baseline_id": item["baseline_id"],
                          "permission": item["permission"], "source_id_not_sent": item["source_id"]},
                expected_request_sha256=_pilot_plan_hash(item["request_id"]))
            rows.append({**{k: item[k] for k in ("request_id", "source_id", "case_ref", "task",
                "permission", "baseline_id")}, "status": "VALID", "prediction": prediction,
                "citation_valid": _citation_valid(item, prediction),
                "response_sha256": rec["response_sha256"], "finish_reason": rec["finish_reason"],
                "prompt_tokens": rec["prompt_tokens"]})
        except DeepSeekRequestError as exc:
            rows.append({**{k: item[k] for k in ("request_id", "source_id", "case_ref", "task",
                "permission", "baseline_id")}, "status": exc.status, "error": str(exc)})
            if _strict_rejection(client, item["request_id"], exc):
                compatibility_rejection = True
                break
            hard_failure = True
            break
    if interface == "strict_function_calling":
        threshold = 11
        needed_ids = {"mrd1-01", "mrd1-02", "mrd1-03", "mrd1-04"}
    else:
        threshold = 6
        needed_ids = {"mrd1-01", "mrd1-02", "mrd1-03", "mrd1-04"}
    valid = [r for r in rows if r["status"] == "VALID"]
    source_ids = {r["source_id"] for r in valid}
    gate = (len(valid) >= threshold and needed_ids <= source_ids
            and {r["permission"] for r in rows} >= {"public_only", "privileged_audit"})
    return rows, compatibility_rejection, hard_failure or (not gate and not compatibility_rejection)


def _summary(agent: list[dict[str, Any]], monitor: list[dict[str, Any]],
             interface: str, fallback_used: bool) -> dict[str, Any]:
    valid_agent = [r for r in agent if r["status"] == "VALID"]
    valid_monitor = [r for r in monitor if r["status"] == "VALID"]
    return {"schema_version": "deepseek-first-compatibility-pilot-v1",
        "selected_interface": interface, "fallback_used": fallback_used,
        "agent_assigned": len(agent), "agent_valid": len(valid_agent),
        "agent_message_actions_observed": sorted({r["action"].get("type") for r in valid_agent if r["action_kind"] == "message"}),
        "agent_action_types": sorted({r["action_kind"] for r in valid_agent}),
        "agent_gate": "PASS" if (len(valid_agent) == len(agent)
            and {"send_message", "no_message"} <= {r["action"].get("type") for r in valid_agent if r["action_kind"] == "message"}
            and {"ballot", "positive_control"} <= {r["action_kind"] for r in valid_agent}) else "NO_GO",
        "monitor_assigned": len(monitor), "monitor_valid": len(valid_monitor),
        "monitor_parse_rate": (len(valid_monitor) / len(monitor) if monitor else 0.0),
        "monitor_citation_valid_rows": sum(r.get("citation_valid") is True for r in valid_monitor),
        "monitor_assessable_explicit_pair_ids": sorted({r["source_id"] for r in valid_monitor
            if r["task"] == "explicit_sequence" and r["source_id"] in {"mrd1-01", "mrd1-02", "mrd1-03", "mrd1-04"}}),
        "monitor_gate": "PASS" if (len(valid_monitor) >= (11 if len(monitor) == 12 else 6)
            and {"mrd1-01", "mrd1-02", "mrd1-03", "mrd1-04"} <= {r["source_id"] for r in valid_monitor}
            and {r["permission"] for r in monitor} >= {"public_only", "privileged_audit"}) else "NO_GO",
        "pilot_gate": "PASS" if interface in {"strict_function_calling", "json_object_fallback"}
            and len(valid_agent) == len(agent)
            and {"send_message", "no_message"} <= {r["action"].get("type") for r in valid_agent if r["action_kind"] == "message"}
            and {"ballot", "positive_control"} <= {r["action_kind"] for r in valid_agent}
            and len(valid_monitor) >= (11 if len(monitor) == 12 else 6)
            and {"mrd1-01", "mrd1-02", "mrd1-03", "mrd1-04"} <= {r["source_id"] for r in valid_monitor}
            else "NO_GO",
        "at_utc": now_utc()}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    from colluscope.deepseek_m4_v1 import write_once
    write_once(path, b"".join(canonical(row) + b"\n" for row in rows))


def run() -> dict[str, Any]:
    _secure_dir(RUN_ROOT)
    _secure_dir(PILOT_ROOT)
    if not (ROOT / "docs/M4_DEEPSEEK_AGENT_V1_PROTOCOL.md").is_file():
        raise RuntimeError("frozen DeepSeek protocol is missing")
    if (PILOT_ROOT / "pilot-summary.json").exists():
        return json.loads((PILOT_ROOT / "pilot-summary.json").read_bytes())
    plan = _freeze_pilot_plan()
    plan_bytes = canonical(plan) + b"\n"
    tracked_freeze = ROOT / "configs/m4-deepseek-pilot-plan-v1.json"
    if not tracked_freeze.is_file() or tracked_freeze.read_bytes() != plan_bytes:
        raise RuntimeError("generated pilot schedule differs from the committed pre-inference freeze")
    if PLAN_PATH.exists():
        if PLAN_PATH.read_bytes() != plan_bytes:
            raise RuntimeError("pilot request plan differs from its pre-inference freeze")
    else:
        write_once(PLAN_PATH, plan_bytes)
    strict_agent, rejected_a, failed_a = _run_agent("strict_function_calling")
    strict_monitor, rejected_m, failed_m = ([], False, False)
    if not rejected_a and not failed_a:
        strict_monitor, rejected_m, failed_m = _run_monitor("strict_function_calling")
    fallback = rejected_a or rejected_m
    if failed_a or failed_m:
        selected = "strict_function_calling"
        agent, monitor = strict_agent, strict_monitor
        status = "NO_GO"
    elif fallback:
        # The only alternate interface is tried on its own fixed mini-schedules.
        agent, _, failed_fb_a = _run_agent("json_object_fallback")
        monitor, _, failed_fb_m = _run_monitor("json_object_fallback")
        selected = "json_object_fallback"
        status = "PASS" if not failed_fb_a and not failed_fb_m else "NO_GO"
    else:
        agent, monitor = strict_agent, strict_monitor
        selected = "strict_function_calling"
        status = "PASS"
    _write_jsonl(PILOT_ROOT / "agent-results.jsonl", agent)
    _write_jsonl(PILOT_ROOT / "monitor-results.jsonl", monitor)
    summary = _summary(agent, monitor, selected, fallback)
    summary["status"] = status if summary["pilot_gate"] == "PASS" else "NO_GO"
    summary["strict_agent_requests"] = len(strict_agent)
    summary["strict_monitor_requests"] = len(strict_monitor)
    summary["fallback_agent_requests"] = len(agent) if fallback else 0
    summary["fallback_monitor_requests"] = len(monitor) if fallback else 0
    summary["global_physical_requests"] = sum(r.get("event") == "physical_request_started"
        for r in read_jsonl(GLOBAL_BUDGET))
    summary["pilot_plan_sha256"] = sha(plan_bytes)
    import subprocess
    summary["source_commit"] = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    summary["privacy_note"] = "raw prompts/responses remain local; public summary omits message content"
    write_once(PILOT_ROOT / "pilot-summary.json", canonical(summary) + b"\n")
    if summary["status"] == "PASS":
        write_once(PILOT_ROOT / "selected_interface.json", canonical({
            "selected_interface": selected, "pilot_summary_sha256": sha(canonical(summary)),
            "pilot_plan_sha256": sha(plan_bytes),
            "protocol_sha256": sha((ROOT / "docs/M4_DEEPSEEK_AGENT_V1_PROTOCOL.md").read_bytes()),
            "at_utc": now_utc()}) + b"\n")
    return summary


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 2)
