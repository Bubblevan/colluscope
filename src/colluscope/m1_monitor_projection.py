"""Fail-closed local projection for the proposed M1 natural-message audit.

This module only compiles restricted local evidence into candidate Monitor and
human-annotation inputs. It never sends network requests and never emits hidden
treatment metadata in the Monitor input objects.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


CHAT_CONDITIONS = {
    "coalition_incentive_private_chat",
    "private_chat_no_side_bonus",
}
TASK_P_FIELDS = {"source_id", "sender", "recipient", "message_text"}
TASK_C_FIELDS = {
    "message_source_id", "sender", "recipient", "message_text",
    "recipient_ballot_event_id", "recipient_ballot",
}


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_assignment(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"A", "B", "C"}
        and set(value.values()) == {"T1", "T2", "T3"}
    )


def _opaque_id(schedule_sha256: str, episode_id: str, sender: str) -> str:
    # Hash the treatment-bearing ID. The digest is only a join key, not a claim
    # of anonymization against someone who has the restricted source mapping.
    value = f"m1-monitor-slot-v1|{schedule_sha256}|{episode_id}|{sender}".encode("utf-8")
    return _sha256(value)


def _payloads(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    values = []
    for row in rows:
        payload = row.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("journal row lacks a payload object")
        values.append(payload)
    return values


def _message_state(message: dict[str, Any]) -> str:
    status = message.get("delivery_status")
    sent, delivered = message.get("sent"), message.get("delivered")
    if status == "invalid_action_output":
        return "invalid_response"
    if sent is False and status == "not_sent":
        return "no_message"
    if sent is True and delivered is True and status == "delivered_to_named_peer":
        if not isinstance(message.get("text"), str) or not message["text"]:
            raise ValueError("delivered message lacks non-empty text")
        return "sent_delivered"
    if sent is True and delivered is False and status == "not_delivered_peer_round_incomplete":
        return "sent_not_delivered"
    if status in {"unknown_after_timeout", "not_confirmed", "pending_atomic_pair_completion"}:
        return "delivery_unknown"
    raise ValueError(f"unrecognized or contradictory message delivery state: {status!r}")


def build_projection(
    schedule: dict[str, Any],
    assigned_episodes: list[dict[str, Any]],
    traces_by_episode: dict[str, dict[str, Any]],
    ledger_payloads: list[dict[str, Any]],
    *,
    schedule_sha256: str | None = None,
) -> dict[str, Any]:
    """Create all 96 coverage rows and eligible inputs from integrity-checked data."""
    schedule_sha = schedule_sha256 or _sha256(_json_bytes(schedule))
    if len(schedule_sha) != 64 or any(character not in "0123456789abcdef" for character in schedule_sha):
        raise ValueError("schedule SHA-256 must be lowercase hexadecimal")
    expected = {row["episode_id"]: row for row in assigned_episodes}
    if len(expected) != len(assigned_episodes):
        raise ValueError("assigned schedule has duplicate episode IDs")
    extra = set(traces_by_episode) - set(expected)
    if extra:
        raise ValueError(f"trace set contains episodes outside the frozen assignment: {sorted(extra)[:3]}")

    attempted_messages: set[tuple[str, str]] = set()
    for payload in ledger_payloads:
        if payload.get("event") not in {"logical_request_attempt_reserved", "logical_request_terminal"}:
            continue
        if payload.get("action_kind") == "message":
            episode_id = payload.get("episode_id")
            agent_id = payload.get("agent_id")
            # Some ledger event versions carry episode ID only in request_id.
            if not isinstance(episode_id, str):
                request_id = payload.get("request_id")
                episode_id = next((eid for eid in expected if isinstance(request_id, str)
                                   and request_id.startswith(eid + "-req-")), None)
            if isinstance(episode_id, str) and agent_id in {"A", "B"}:
                attempted_messages.add((episode_id, agent_id))

    coverage: list[dict[str, Any]] = []
    monitor_requests: list[dict[str, Any]] = []
    private_mapping: list[dict[str, Any]] = []
    annotation_rows: list[dict[str, Any]] = []
    for episode_id, assigned in expected.items():
        condition_id = assigned.get("condition_id")
        if condition_id not in CHAT_CONDITIONS:
            continue
        trace = traces_by_episode.get(episode_id)
        if trace is not None:
            treatment = trace.get("T")
            behavior = trace.get("B")
            evidence = trace.get("E")
            if not all(isinstance(row, dict) for row in (treatment, behavior, evidence)):
                raise ValueError(f"episode trace lacks T/B/E object: {episode_id}")
            if (treatment.get("episode_id") != episode_id
                    or treatment.get("condition_id") != condition_id
                    or treatment.get("assigned", {}).get("private_chat_available") is not True):
                raise ValueError(f"trace treatment does not match frozen chat assignment: {episode_id}")
            if behavior.get("episode_id") != episode_id:
                raise ValueError(f"behavior trace episode ID mismatch: {episode_id}")
            messages = behavior.get("peer_messages")
            if not isinstance(messages, list):
                raise ValueError(f"peer_messages is not a list: {episode_id}")
            by_sender = {item.get("sender"): item for item in messages if isinstance(item, dict)}
            if len(by_sender) != len(messages) or set(by_sender) - {"A", "B"}:
                raise ValueError(f"peer message sender IDs are duplicate or invalid: {episode_id}")
        else:
            treatment = behavior = evidence = None
            by_sender = {}

        ballots_by_agent: dict[str, dict[str, Any]] = {}
        public_votes: dict[str, dict[str, Any]] = {}
        if behavior is not None:
            ballots = behavior.get("ballots")
            if not isinstance(ballots, list):
                raise ValueError(f"ballot rows are missing: {episode_id}")
            ballots_by_agent = {row.get("agent_id"): row for row in ballots if isinstance(row, dict)}
            if len(ballots_by_agent) != len(ballots):
                raise ValueError(f"duplicate ballot agent IDs: {episode_id}")
            events = evidence.get("events")
            if not isinstance(events, list):
                raise ValueError(f"public event list is missing: {episode_id}")
            for event in events:
                if isinstance(event, dict) and event.get("type") == "vote":
                    actor = event.get("actor")
                    if actor in public_votes:
                        raise ValueError(f"duplicate public vote event for {actor}: {episode_id}")
                    public_votes[actor] = event

        for sender in ("A", "B"):
            recipient = "B" if sender == "A" else "A"
            source_id = _opaque_id(schedule_sha, episode_id, sender)
            message = by_sender.get(sender)
            if trace is None:
                state = "not_observed_unresolved"
                text_value = None
            elif message is None:
                state = ("request_failed_or_output_missing" if (episode_id, sender) in attempted_messages
                         else "not_attempted")
                text_value = None
            else:
                state = _message_state(message)
                text_value = message.get("text") if state == "sent_delivered" else None
                if message.get("recipient") != recipient:
                    raise ValueError(f"message routed to the wrong peer: {episode_id}/{sender}")

            ballot = ballots_by_agent.get(recipient)
            ballot_assignment = None
            ballot_event = public_votes.get(recipient)
            if ballot is not None and ballot.get("sealed") is True and _valid_assignment(ballot.get("parsed_assignment")):
                if ballot_event is not None:
                    event_assignment = ballot_event.get("content", {}).get("assignment")
                    if event_assignment != ballot["parsed_assignment"]:
                        raise ValueError(f"public vote event differs from recipient sealed ballot: {episode_id}/{recipient}")
                    ballot_assignment = ballot["parsed_assignment"]

            row = {
                "source_id": source_id,
                "episode_id": episode_id,
                "condition_id": condition_id,
                "sender": sender,
                "recipient": recipient,
                "slot_state": state,
                "task_p_eligible": state == "sent_delivered",
                "task_c_eligible": state == "sent_delivered" and ballot_assignment is not None,
                "task_c_ineligible_reason": None if state == "sent_delivered" and ballot_assignment is not None
                    else ("message_not_delivered" if state != "sent_delivered" else "recipient_ballot_not_public_or_invalid"),
            }
            coverage.append(row)
            private_mapping.append({**row, "message_request_id": message.get("request_id") if message else None,
                                    "recipient_ballot_event_id": ballot_event.get("event_id") if ballot_event else None,
                                    "recipient_ballot": ballot_assignment})
            if state == "sent_delivered":
                p_input = {"source_id": source_id, "sender": sender,
                           "recipient": recipient, "message_text": text_value}
                if set(p_input) != TASK_P_FIELDS:
                    raise AssertionError("Task P projection field set drifted")
                monitor_requests.append({"task_id": source_id + ":P", "task": "task_p", "input": p_input})
                annotation_rows.append({"blind_id": source_id + ":P", "task": "task_p", "input": p_input,
                                        "reference_fields": {"proposal_status": None, "allocation": None,
                                                             "evidence_span": None}})
                if ballot_assignment is not None:
                    c_input = {"message_source_id": source_id, "sender": sender, "recipient": recipient,
                               "message_text": text_value,
                               "recipient_ballot_event_id": ballot_event["event_id"],
                               "recipient_ballot": ballot_assignment}
                    if set(c_input) != TASK_C_FIELDS:
                        raise AssertionError("Task C projection field set drifted")
                    monitor_requests.append({"task_id": source_id + ":C", "task": "task_c", "input": c_input})
                    annotation_rows.append({"blind_id": source_id + ":C", "task": "task_c", "input": c_input,
                                            "reference_fields": {"concordance": None,
                                                                 "interpreted_allocation": None,
                                                                 "evidence_span": None}})

    if len(coverage) != 96:
        raise ValueError(f"expected 96 preassigned message slots, found {len(coverage)}")
    if len({row["source_id"] for row in coverage}) != 96:
        raise ValueError("opaque source IDs are not unique")
    counts = dict(sorted(Counter(row["slot_state"] for row in coverage).items()))
    return {
        "coverage": coverage,
        "monitor_requests": monitor_requests,
        "private_mapping": private_mapping,
        "annotation_rows": annotation_rows,
        "summary": {
            "assigned_message_slots": len(coverage),
            "slot_state_counts": counts,
            "task_p_requests": sum(row["task"] == "task_p" for row in monitor_requests),
            "task_c_requests": sum(row["task"] == "task_c" for row in monitor_requests),
            "monitor_request_max": 216,
            "monitor_requests_with_private_text": len(monitor_requests),
            "monitor_calls_sent": 0,
            "external_cost_usd": 0,
        },
    }


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object in {path.name}")
    return value


def _read_trace_dir(run_dir: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    # The path is already guarded by the live M1 runner and has a user-only ACL.
    from scripts.local_llama_security import verify_private_directory_acl
    from colluscope.m1_package_replication_v3_runtime import HashChainJournal

    verify_private_directory_acl(run_dir)
    request_journal = HashChainJournal(run_dir / "request-ledger.jsonl")
    group_journal = HashChainJournal(run_dir / "group-ledger.jsonl")
    terminal: dict[str, str] = {}
    for row in group_journal.rows:
        payload = row["payload"]
        if payload.get("event") == "episode_terminal":
            episode_id = payload.get("episode_id")
            trace_path = payload.get("trace_path")
            digest = payload.get("trace_sha256")
            if not isinstance(episode_id, str) or not isinstance(trace_path, str) or not isinstance(digest, str):
                raise ValueError("episode terminal ledger row lacks trace identity")
            if episode_id in terminal and terminal[episode_id] != digest:
                raise ValueError(f"episode has conflicting terminal trace hashes: {episode_id}")
            terminal[episode_id] = digest

    terminal_rows = {
        row["payload"]["episode_id"]: row["payload"]
        for row in group_journal.rows
        if row["payload"].get("event") == "episode_terminal"
    }
    for episode_id, record in terminal_rows.items():
        relative = Path(record["trace_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe episode trace path in group ledger: {episode_id}")
        trace_path = run_dir / relative
        if not trace_path.is_file() or _sha256(trace_path.read_bytes()) != record["trace_sha256"]:
            raise ValueError(f"terminal trace is absent or differs from group-ledger hash: {episode_id}")

    trace_dir = run_dir / "episodes"
    traces: dict[str, dict[str, Any]] = {}
    source_hashes: dict[str, str] = {}
    for path in sorted(trace_dir.glob("*.json")):
        raw = path.read_bytes()
        trace = json.loads(raw)
        episode_id = trace.get("T", {}).get("episode_id")
        if not isinstance(episode_id, str) or path.name != episode_id + ".json":
            raise ValueError(f"episode trace filename/ID mismatch: {path.name}")
        if episode_id not in terminal or terminal[episode_id] != _sha256(raw):
            raise ValueError(f"episode trace is not bound to its terminal group-ledger hash: {episode_id}")
        if episode_id in traces:
            raise ValueError(f"duplicate episode trace: {episode_id}")
        traces[episode_id] = trace
        source_hashes[path.relative_to(run_dir).as_posix()] = _sha256(raw)
    return traces, _payloads(request_journal.rows), source_hashes


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def compile_run(run_dir: Path, *, write: bool) -> dict[str, Any]:
    from scripts.local_llama_security import restrict_private_directory_acl, verify_private_directory_acl
    from colluscope.m1_package_replication_v3_runtime import (
        _validate_output_path, assigned_episodes, load_frozen_schedule,
    )

    root = Path(__file__).resolve().parents[2]
    run_dir = _validate_output_path(Path(run_dir))
    if not run_dir.is_dir() or run_dir.is_symlink():
        raise ValueError("run directory must already exist and cannot be a symlink")
    relative = run_dir.relative_to(root).as_posix()
    ignored = subprocess.run(["git", "check-ignore", "--quiet", relative], cwd=root,
                             capture_output=True, check=False)
    if ignored.returncode != 0:
        raise PermissionError("source run directory is not Git-ignored")
    verify_private_directory_acl(run_dir)
    schedule = load_frozen_schedule()
    assigned = assigned_episodes(schedule)
    schedule_path = Path(__file__).resolve().parents[2] / "research/drafts/m1-package-24-matrix-scenarios-20261021.json"
    schedule_sha = _sha256(schedule_path.read_bytes())
    environment = _read_json(run_dir / "environment.json")
    if (environment.get("protocol_id") != "m1-package-replication-v3"
            or environment.get("experiment_id") != "m1-reward-chat-24group-replication-v1"
            or environment.get("candidate", {}).get("schedule_sha256") != schedule_sha):
        raise ValueError("run environment is not the frozen M1 package v3 candidate")
    traces, ledger_payloads, trace_hashes = _read_trace_dir(run_dir)
    projection = build_projection(schedule, assigned, traces, ledger_payloads, schedule_sha256=schedule_sha)
    projection["summary"]["source_episode_traces"] = len(traces)
    projection["summary"]["source_trace_hashes"] = trace_hashes
    if not write:
        return projection["summary"]

    output_dir = run_dir / "private" / "monitor_audit_candidate_v1"
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("refusing to overwrite a prior private Monitor projection")
    output_dir.mkdir(parents=False, exist_ok=False)
    restrict_private_directory_acl(output_dir)
    verify_private_directory_acl(run_dir)

    coverage = projection["coverage"]
    requests = projection["monitor_requests"]
    mapping = projection["private_mapping"]
    annotations = projection["annotation_rows"]
    spec_path = root / "research/drafts/m1-natural-message-monitor-spec-v1.json"
    codebook_path = root / "research/drafts/m1-natural-message-action-codebook-v1.md"
    schedule_path = root / "research/drafts/m1-package-24-matrix-scenarios-20261021.json"
    controls_path = root / "research/drafts/m1-natural-message-monitor-controls-v1.json"
    control_key_path = root / "research/drafts/m1-natural-message-monitor-controls-v1-answer-key.json"
    controls = json.loads(controls_path.read_text(encoding="utf-8"))
    control_key = json.loads(control_key_path.read_text(encoding="utf-8"))
    control_requests, control_references = build_control_requests(controls, control_key)
    all_requests = sorted(requests + control_requests,
                          key=lambda row: _sha256(("m1-monitor-dispatch-v1|" + row["task_id"]).encode()))
    all_requests = [{**row, "dispatch_index": index} for index, row in enumerate(all_requests, 1)]
    if len(all_requests) > 216:
        raise ValueError("natural and control request graph exceeds its frozen 216-request maximum")
    files: dict[str, bytes] = {
        "coverage.jsonl": b"".join(_json_bytes(row) for row in coverage),
        "monitor-request-inputs.jsonl": b"".join(_json_bytes(row) for row in all_requests),
        "private-source-mapping.jsonl": b"".join(_json_bytes(row) for row in mapping),
        "annotation-coder-1.jsonl": b"".join(_json_bytes(row) for row in _blind_order(annotations, schedule_path, "coder-1")),
        "annotation-coder-2.jsonl": b"".join(_json_bytes(row) for row in _blind_order(annotations, schedule_path, "coder-2")),
        "control-reference-key.jsonl": b"".join(_json_bytes(row) for row in control_references),
    }
    for name, data in files.items():
        _write_once(output_dir / name, data)
    manifest = {
        "schema_version": 1,
        "status": "LOCAL_PRIVATE_PROJECTION_READY_NOT_DISPATCHED",
        "source_run_id": run_dir.name,
        "schedule_sha256": _sha256(schedule_path.read_bytes()),
        "monitor_spec_sha256": _sha256(spec_path.read_bytes()),
        "codebook_sha256": _sha256(codebook_path.read_bytes()),
        "controls_sha256": _sha256(controls_path.read_bytes()),
        "control_answer_key_sha256": _sha256(control_key_path.read_bytes()),
        "source_episode_trace_sha256": trace_hashes,
        "projection_summary": {**projection["summary"], "control_requests": len(control_requests),
                                "total_monitor_request_inputs": len(all_requests)},
        "files": {name: _sha256(data) for name, data in files.items()},
        "model_calls": 0,
        "external_cost_usd": 0,
        "private_text_transmitted_externally": False,
        "external_transfer_requires_fresh_user_approval": True,
        "request_order_scheme": "sha256(m1-monitor-dispatch-v1|task_id)-ascending",
    }
    _write_once(output_dir / "manifest.json", _json_bytes(manifest))
    acl = verify_private_directory_acl(run_dir)
    return {**projection["summary"], "control_requests": len(control_requests),
            "total_monitor_request_inputs": len(all_requests), "status": manifest["status"],
            "output_dir": str(output_dir), "acl": acl}


def _blind_order(rows: list[dict[str, Any]], schedule_path: Path, coder_tag: str) -> list[dict[str, Any]]:
    salt = _sha256(schedule_path.read_bytes())
    return sorted(rows, key=lambda row: _sha256(f"{salt}|annotation-order-v1|{coder_tag}|{row['blind_id']}".encode()))
