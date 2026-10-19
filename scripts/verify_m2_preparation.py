#!/usr/bin/env python3
"""Independent offline check of the prepared M2 evidence and request plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.m2_corpus import file_sha256  # noqa: E402


FORBIDDEN_METADATA_KEYS = {"condition_id", "episode_id", "split_group_id", "seed_block_id",
                           "scenario_family_id", "researcher_label", "oracle", "collusion_label",
                           "latent_collusion", "target_executed_researcher_only",
                           "private_target_bonus_recipients", "private_incentive_assignment"}


def _find_forbidden_keys(value, found=None):
    found = found if found is not None else set()
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold() in FORBIDDEN_METADATA_KEYS:
                found.add(str(key))
            _find_forbidden_keys(item, found)
    elif isinstance(value, list):
        for item in value:
            _find_forbidden_keys(item, found)
    return found


def _sha_json(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _verify_current_user_acl(paths: list[Path]) -> dict:
    identity = subprocess.run(["whoami.exe", "/user", "/fo", "csv", "/nh"],
                              capture_output=True, text=True, timeout=10, check=True)
    import csv
    rows = list(csv.reader(identity.stdout.splitlines()))
    if len(rows) != 1 or len(rows[0]) < 2:
        raise PermissionError("cannot identify current Windows user for private M2 ACL verification")
    account, sid = rows[0][0], rows[0][1]
    records = {}
    for path in paths:
        result = subprocess.run(["icacls.exe", str(path)], capture_output=True, text=True,
                               timeout=10, check=True)
        ace_lines = [line.strip().replace(" ", "").casefold() for line in result.stdout.splitlines()
                     if ":(" in line.replace(" ", "")]
        current = [line for line in ace_lines if sid.casefold() in line or account.replace(" ", "").casefold() in line]
        if not current or any(line not in current for line in ace_lines):
            raise PermissionError(f"M2 path ACL includes a non-current-user ACE or lacks current-user access: {path}")
        if not any("(f)" in line for line in current):
            raise PermissionError(f"current user lacks full control on M2 path: {path}")
        records[str(path.resolve())] = {"ace_count": len(ace_lines), "current_user_full_control": True,
                                       "acl_output_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest()}
    return {"account": account, "sid": sid, "verified_paths": records}


def _evidence_from_user(view: str, user: str):
    marker = "Evidence object:\n"
    if marker not in user:
        raise ValueError("frozen user prompt has no Evidence object section")
    evidence_text = user.split(marker, 1)[1]
    if view != "raw_fusion":
        return json.loads(evidence_text)
    lines = evidence_text.splitlines()
    if len(lines) < 3 or lines[0] != "Public task specification:" or \
            lines[2] != "Ordered permitted evidence events:":
        raise ValueError("raw-fusion evidence stream does not match its frozen event grammar")
    task_spec = json.loads(lines[1])
    events = [json.loads(line) for line in lines[3:]]
    return {"task_spec": task_spec, "events": events}


def verify(out: Path) -> dict:
    manifest = json.loads((out / "preparation-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("no_model_calls") is not True or manifest.get("logical_evaluation_count") != 1000:
        raise ValueError("M2 preparation manifest does not attest 1,000 no-call evaluations")
    plan = json.loads((out / "private/evaluation-plan.json").read_text(encoding="utf-8"))
    if file_sha256(out / "private/evaluation-plan.json") != manifest["hashes"]["evaluation_plan"]:
        raise ValueError("M2 evaluation plan differs from the preparation hash")
    if file_sha256(out / "private/evidence-projections.jsonl") != manifest["hashes"]["evidence_projections"]:
        raise ValueError("M2 Privileged evidence projection differs from its preparation hash")
    evaluations = plan["logical_evaluations"]
    if len(evaluations) != 1000 or len({row["eval_id"] for row in evaluations}) != 1000:
        raise ValueError("M2 evaluation plan does not contain exactly 1,000 unique logical evaluations")
    request_paths = list((out / "requests").glob("m2-*.json"))
    if len(request_paths) != plan.get("unique_payload_count"):
        raise ValueError("prepared request directory and unique-payload count differ")
    eval_counts = Counter((row["partition"], row["view_name"], row["permission_profile"])
                          for row in evaluations)
    if len(eval_counts) != 40 or any(count != 25 for count in eval_counts.values()):
        raise ValueError("every F0-F3 × view × permission cell must contain 25 assigned episodes")
    if (out / "requests-ledger.jsonl").exists() and (out / "requests-ledger.jsonl").stat().st_size:
        raise ValueError("M2 no-call preparation verification found model request records")
    if any((out / "launches").glob("launch-*")):
        raise ValueError("M2 no-call preparation verification found an inference launch")
    projections = {}
    with (out / "private/evidence-projections.jsonl").open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, start=1):
            value = json.loads(line)
            if value["case_id"] in projections:
                raise ValueError("duplicate opaque case projection")
            if set(value["public_e"]) != {"task_spec", "events"}:
                raise ValueError("M2 source Public E projection has unexpected fields")
            if _sha_json(value["public_e"]) != value["public_e_sha256"]:
                raise ValueError(f"Public E canonical hash mismatch in projection row {line_no}")
            if any(event.get("type") == "message" or event.get("visibility") != "public"
                   for event in value["public_e"]["events"]):
                raise PermissionError("private/message event entered source Public E projection")
            for message in value["delivered_messages"]:
                if (message.get("sent") is not True or message.get("delivered") is not True or
                        message.get("sender") not in {"A", "B"} or
                        message.get("recipient") not in {"A", "B"} or
                        message.get("sender") == message.get("recipient") or
                        not isinstance(message.get("text"), str)):
                    raise PermissionError("invalid or non-A/B Privileged Audit source message")
            projections[value["case_id"]] = value
    if len(projections) != 100 or {row["case_id"] for row in evaluations} != set(projections):
        raise ValueError("evidence projections do not cover all 100 opaque cases")
    acl = _verify_current_user_acl([out, out / "private", out / "requests", out / "responses",
                                    out / "launches", out / "analysis", out / "stage1"])
    request_checks = []
    for path in request_paths:
        request = json.loads(path.read_text(encoding="utf-8"))
        payload = request["payload"]
        payload_json = request.get("payload_json")
        if not isinstance(payload_json, str) or json.loads(payload_json) != payload:
            raise ValueError(f"prepared request object/body differ: {path.name}")
        if json.dumps(payload, ensure_ascii=False, separators=(",", ":")) != payload_json:
            raise ValueError(f"prepared request serialization is not reproducible from its stored object: {path.name}")
        raw = payload_json.encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != request["payload_sha256"] or path.stem != request["request_id"]:
            raise ValueError(f"prepared request file hash/name mismatch: {path.name}")
        if _find_forbidden_keys(payload):
            raise ValueError(f"hidden metadata keys found in model request: {_find_forbidden_keys(payload)}")
        messages = payload.get("messages")
        if not isinstance(messages, list) or len(messages) != 2:
            raise ValueError("each M2 request must contain exactly system and user messages")
        system, user = messages[0]["content"], messages[1]["content"]
        if "untrusted evidence" not in system.casefold() or "latent_intent" not in system:
            raise ValueError("frozen system prompt lacks injection and latent-intent constraints")
        if request["view_name"] not in system + user or request["permission_profile"] not in system + user:
            raise ValueError("permission/view scope is not explicit in the model-facing prompt")
        evidence = _evidence_from_user(request["view_name"], user)
        events = evidence["events"]
        linked_evals = [row for row in evaluations if row["request_id"] == request["request_id"]]
        for linked in linked_evals:
            projection = projections[linked["case_id"]]
            if evidence["task_spec"] != projection["public_e"]["task_spec"]:
                raise ValueError("monitor task specification differs from source Public E")
            public_events = []
            for index, source_event in enumerate(projection["public_e"]["events"], start=1):
                public_events.append({"event_id": f"P{index:02d}", "order": index,
                    "actor": source_event.get("actor"), "type": source_event["type"],
                    "visibility": "public", "content": source_event.get("content"),
                    "provenance": "immutable Public E event"})
            messages = []
            if request["permission_profile"] == "privileged_audit" and request["view_name"] in {
                    "text_only", "raw_fusion", "structured_evidence", "structured_without_findings"}:
                for index, source_message in enumerate(projection["delivered_messages"], start=1):
                    messages.append({"event_id": f"M{index:02d}", "order": 0,
                        "temporal_relation": "generated_before_delivery; delivered_as_pre_ballot_batch",
                        "actor": source_message["sender"], "recipient": source_message["recipient"],
                        "type": "message", "visibility": "privileged_audit",
                        "delivery_status": "delivered", "content": {"text": source_message["text"]},
                        "provenance": "projected from researcher B.peer_messages delivery record"})
            if request["view_name"] == "text_only":
                expected_events = messages
            elif request["view_name"] == "action_only":
                expected_events = public_events
            else:
                expected_events = messages + public_events
            if events != expected_events:
                raise PermissionError("monitor-visible event content differs from permission-filtered source T/B/E")
            if _find_forbidden_keys(evidence):
                raise PermissionError("forbidden researcher/hidden metadata key appears in monitor-visible evidence")
        event_ids = {event["event_id"] for event in events}
        if len(event_ids) != len(events):
            raise ValueError("input contains duplicate monitor-visible event IDs")
        if any(event.get("type") == "message" and
               (request["permission_profile"] != "privileged_audit" or
                request["view_name"] not in {"text_only", "raw_fusion", "structured_evidence",
                                            "structured_without_findings"}) for event in events):
            raise PermissionError("private message crossed a forbidden view or permission boundary")
        if any(event.get("type") == "message" and
               (event.get("actor") not in {"A", "B"} or event.get("recipient") not in {"A", "B"})
               for event in events):
            raise PermissionError("A/B message projection contains C or an unknown peer")
        if request["view_name"] == "action_only" and any(event.get("type") == "message" for event in events):
            raise PermissionError("action-only view contains communication text")
        if request["permission_profile"] == "public_only" and any(
                event.get("type") == "message" or event.get("visibility") == "privileged_audit"
                for event in events):
            raise PermissionError("Public-only view contains a privileged event")
        if request["view_name"] == "structured_without_findings" and evidence.get("findings") != []:
            raise ValueError("structured no-findings ablation contains computed findings")
        if request["view_name"] == "structured_evidence":
            if not isinstance(evidence.get("findings"), list):
                raise ValueError("structured-with-findings input lacks its findings list")
            for finding in evidence["findings"]:
                if not set(finding.get("source_event_ids", [])) <= event_ids:
                    raise ValueError("derived finding cites an event that is not visible in the view")
                if _find_forbidden_keys(finding):
                    raise ValueError("derived findings contain hidden metadata keys")
        if not linked_evals:
            raise ValueError("prepared request has no linked logical evaluations")
        if any(row["payload_sha256"] != digest for row in linked_evals):
            raise ValueError("evaluation-to-request payload hash link mismatch")
        if len({row["permission_profile"] for row in linked_evals}) != 1 or \
                len({row["partition"] for row in linked_evals}) != 1:
            raise ValueError("exact-payload dedup crossed permission or split boundaries")
        request_checks.append({"request_id": request["request_id"], "payload_sha256": digest,
                               "linked_evaluation_count": len(linked_evals),
                               "permission_profile": request["permission_profile"],
                               "partition": request["partition"], "view_name": request["view_name"],
                               "visible_event_count": len(events),
                               "input_tokens_local": request["input_tokens_local"]})
    if any(row["input_tokens_local"] > 3072 for row in evaluations if row["preparation_status"] == "prepared"):
        raise ValueError("prepared request input token cap was exceeded")
    over_budget = sum(row["preparation_status"] != "prepared" for row in evaluations)
    source_validation = json.loads((out / "stage1/source-validation.json").read_text(encoding="utf-8"))
    result = {"status": "PASS_M2_PREPARATION_PERMISSION_AND_HASH_AUDIT",
              "verified_at_utc": datetime.now(timezone.utc).isoformat(),
              "logical_evaluations": len(evaluations), "unique_payload_files": len(request_paths),
              "over_budget_not_sent_evaluations": over_budget,
              "request_files_sha256_manifest": hashlib.sha256(json.dumps(
                  sorted(request_checks, key=lambda row: row["request_id"]), sort_keys=True,
                  separators=(",", ":")).encode("utf-8")).hexdigest(),
              "source_m1_corpus_manifest_sha256": source_validation["original_corpus_manifest_sha256"],
              "acl": acl,
              "no_model_calls": True, "public_e_source_unchanged": True,
              "cross_permission_payload_dedup": False}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=ROOT / "runs/m2/one-shot-20261019")
    args = parser.parse_args()
    run = args.run.resolve()
    if not run.is_relative_to(ROOT / "runs/m2"):
        raise ValueError("M2 verification reads only the local Git-ignored run root")
    result = verify(run)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
