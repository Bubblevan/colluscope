#!/usr/bin/env python3
"""Independent, privacy-preserving summary of the authorized M4 live run.

This script reports only aggregate parser/episode evidence. It never writes or
prints model text, prompts, private messages, credentials, or treatment payloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def audit(run: Path, source_commit: str | None = None) -> dict:
    run = run.resolve()
    manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
    episodes = _jsonl(run / "episodes.jsonl")
    attempts = _jsonl(run / "attempts.jsonl")
    groups = _jsonl(run / "groups.jsonl")
    summaries = _jsonl(run / "run_summaries.jsonl")
    receipts = _jsonl(run / "audit_receipts.jsonl")
    started = [row for row in attempts if row.get("event") == "attempt_started"]
    terminal_attempts = [row for row in attempts if row.get("event") == "attempt_terminal"]
    response_rows = []
    for meta_path in sorted((run / "responses").glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        request_id = meta_path.name[:-len(".meta.json")]
        body_path = run / "responses" / f"{request_id}.body"
        body = body_path.read_bytes()
        response = json.loads(body)
        choices = response.get("choices")
        message = choices[0].get("message", {}) if isinstance(choices, list) and choices else {}
        text = message.get("content") if isinstance(message.get("content"), str) else ""
        response_rows.append({
            "request_id": request_id,
            "response_sha256": _sha(body),
            "metadata_status": meta.get("status"),
            "http_status": meta.get("http_status"),
            "finish_reason": meta.get("finish_reason"),
            "content_sha256": _sha(text.encode("utf-8")),
            "content_length": len(text),
            "starts_with_think_tag": text.lstrip().startswith("<think>"),
            "has_think_close_tag": "</think>" in text,
            "has_action_object_marker": "{\"type\"" in text or "{\n  \"type\"" in text,
            "usage": meta.get("usage") if isinstance(meta.get("usage"), dict) else {},
        })
    terminal_statuses = Counter(row.get("terminal_status") for row in episodes)
    failure_statuses = Counter(
        failure.get("status")
        for episode in episodes
        for failure in episode.get("failure_records", [])
    )
    message_counts = [len((row.get("researcher_B") or {}).get("messages", [])) for row in episodes]
    ballot_counts = [len((row.get("researcher_B") or {}).get("ballots", [])) for row in episodes]
    if len(episodes) != 24 or len(started) != 24 or len(terminal_attempts) != 24:
        raise ValueError("M4 assignment/attempt denominator does not match the frozen 24 groups")
    if any(row["response_sha256"] != next(
            (event.get("response_body_sha256") for event in _jsonl(run / "attempts.jsonl")
             if event.get("request_id") == row["request_id"] and event.get("event") == "attempt_terminal"),
            None) for row in response_rows):
        raise ValueError("raw M4 response body hash differs from terminal ledger")
    summary = summaries[-1] if summaries else {}
    independent = receipts[-1] if receipts else {}
    return {
        "schema_version": "colluscope-full-research-m4-audit-v1",
        "run_manifest_sha256": _sha((run / "run_manifest.json").read_bytes()),
        "source_commit": source_commit or manifest.get("source_commit"),
        "assigned_groups": len([row for row in groups if row.get("event") == "group_assigned"]),
        "group_started": sum(row.get("event") == "group_started" for row in groups),
        "group_terminal": sum(row.get("event") == "group_terminal" for row in groups),
        "terminal_statuses": dict(terminal_statuses),
        "attempts_started": len(started),
        "attempts_terminal": len(terminal_attempts),
        "retry_count": summary.get("retry_count"),
        "replacement_groups": summary.get("replacement_groups"),
        "failure_statuses": dict(failure_statuses),
        "http_statuses": dict(Counter(row.get("http_status") for row in response_rows)),
        "finish_reasons": dict(Counter(row.get("finish_reason") for row in response_rows)),
        "response_statuses": dict(Counter(row.get("metadata_status") for row in response_rows)),
        "think_tag_prefix_count": sum(row["starts_with_think_tag"] for row in response_rows),
        "think_close_tag_count": sum(row["has_think_close_tag"] for row in response_rows),
        "messages_recorded": sum(message_counts),
        "ballots_recorded": sum(ballot_counts),
        "proposal_eligible_groups": sum(bool(row.get("proposal_eligible")) for row in episodes),
        "response_action_links": independent.get("response_actions_linked"),
        "settlements_recomputed": independent.get("settlements_recomputed"),
        "independent_trace_replay_status": independent.get("status"),
        "usage_totals": {
            "prompt_tokens": sum(int(row["usage"].get("prompt_tokens", 0)) for row in response_rows),
            "completion_tokens": sum(int(row["usage"].get("completion_tokens", 0)) for row in response_rows),
            "total_tokens": sum(int(row["usage"].get("total_tokens", 0)) for row in response_rows),
        },
        "per_response_private_digests": [
            {key: row[key] for key in ("request_id", "response_sha256", "content_sha256", "content_length")}
            for row in response_rows
        ],
        "raw_model_text_in_report": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    result = audit(args.run, source_commit=args.source_commit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in {"per_response_private_digests"}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
