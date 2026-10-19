"""Read-only loading and integrity checks for the frozen M1-100 M2 corpus."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .m2_monitor import canonical_json


@dataclass(frozen=True)
class M2Case:
    episode_id: str
    provenance: str
    partition: str
    scenario_family_id: str
    seed_block_id: str
    split_group_id: str
    condition_id: str
    treatment: dict[str, Any]
    behavior: dict[str, Any]
    public_e: dict[str, Any]
    delivered_messages: tuple[dict[str, Any], ...]
    source_public_e_sha256: str
    source_b_sha256: str


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                raise ValueError(f"blank JSONL row at {path}:{line_number}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"non-object JSONL row at {path}:{line_number}")
            rows.append(value)
    return rows


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _events_sha(public_e: dict[str, Any]) -> str:
    return sha256(canonical_json(public_e)).hexdigest()


def _load_one_source(root: Path, source_dir: Path, provenance: str,
                     partition_by_group: dict[str, dict[str, Any]],
                     *, indexed_evidence: bool) -> list[M2Case]:
    t_rows = read_jsonl(source_dir / "researcher/T.jsonl")
    b_rows = read_jsonl(source_dir / "researcher/B.jsonl")
    e_rows = read_jsonl(source_dir / "monitor_inputs/evidence.jsonl")
    if len(t_rows) != len(b_rows):
        raise ValueError(f"T/B row counts differ for {provenance}")
    b_by_id = {row.get("episode_id"): row for row in b_rows}
    if len(b_by_id) != len(b_rows) or None in b_by_id:
        raise ValueError(f"B episode IDs are missing or duplicated for {provenance}")
    if indexed_evidence:
        index_rows = read_jsonl(source_dir / "researcher/evidence-index.jsonl")
        if len(index_rows) != len(t_rows):
            raise ValueError("M1-100 E index does not cover every T episode")
        e_by_index = {index: row for index, row in enumerate(e_rows)}
        e_for_id = {}
        for index_row in index_rows:
            idx = index_row.get("evidence_row_index")
            if not isinstance(idx, int) or idx not in e_by_index:
                raise ValueError("M1-100 E index points outside the source Public E table")
            e_for_id[index_row["episode_id"]] = e_by_index[idx]
            if _events_sha(e_by_index[idx]) != index_row.get("evidence_sha256"):
                raise ValueError("M1-100 E index hash differs from its source Public E payload")
        if set(e_for_id) != set(b_by_id):
            raise ValueError("M1-100 E index episode coverage differs from T/B")
    else:
        if len(e_rows) != len(t_rows):
            raise ValueError(f"historical T/E row counts differ: {len(t_rows)} vs {len(e_rows)}")
        e_for_id = {t["episode_id"]: e for t, e in zip(t_rows, e_rows, strict=True)}

    results: list[M2Case] = []
    seen = set()
    for t in t_rows:
        eid = t.get("episode_id")
        if not isinstance(eid, str) or eid in seen or eid not in b_by_id or eid not in e_for_id:
            raise ValueError(f"T/B/E episode alignment failure in {provenance}")
        seen.add(eid)
        b = b_by_id[eid]
        e = e_for_id[eid]
        if b.get("status") != "COMPLETED" or len(b.get("ballots", [])) != 3:
            raise ValueError(f"nonterminal or incomplete assigned episode {eid}")
        if set(e) != {"task_spec", "events"}:
            raise ValueError(f"Public E envelope has unexpected fields for {eid}")
        if any(event.get("type") == "message" or event.get("visibility") != "public"
               for event in e.get("events", [])):
            raise ValueError(f"source Public E contains a private or message event for {eid}")
        group_id = t.get("split_group_id")
        group = partition_by_group.get(group_id)
        if group is None:
            raise ValueError(f"episode {eid} maps to no frozen M2 split group")
        for key in ("scenario_family_id", "seed_block_id"):
            if t.get(key) != group.get(key):
                raise ValueError(f"episode {eid} {key} differs from frozen M2 split metadata")
        if t.get("condition_id") not in group.get("condition_ids", []):
            raise ValueError(f"episode {eid} condition does not belong to its matched split group")
        sent_and_delivered = []
        allowed_private_agents = set(e["task_spec"]["agents"]) & {"A", "B"}
        for source_index, message in enumerate(b.get("peer_messages", []), start=0):
            if message.get("sent") is True and message.get("delivered") is True:
                if (message.get("sender") not in allowed_private_agents or
                        message.get("recipient") not in allowed_private_agents or
                        message.get("sender") == message.get("recipient")):
                    raise ValueError("M2 Privileged projection found a delivery outside the authorized A/B peer channel")
                if not isinstance(message.get("text"), str):
                    raise ValueError("M2 delivered private message text must be preserved as a string")
                sent_and_delivered.append({
                    "sent": True,
                    "delivered": True,
                    "sender": message.get("sender"),
                    "recipient": message.get("recipient"),
                    "text": message.get("text"),
                    "source_b_record_sha256": sha256(canonical_json(b)).hexdigest(),
                    "source_message_index": source_index,
                    "source_request_id": message.get("request_id"),
                })
        results.append(M2Case(
            episode_id=eid,
            provenance=provenance,
            partition=group["partition"],
            scenario_family_id=t["scenario_family_id"],
            seed_block_id=t["seed_block_id"],
            split_group_id=group_id,
            condition_id=t["condition_id"],
            treatment=t,
            behavior=b,
            public_e=e,
            delivered_messages=tuple(sent_and_delivered),
            source_public_e_sha256=_events_sha(e),
            source_b_sha256=sha256(canonical_json(b)).hexdigest(),
        ))
    return results


def load_m2_corpus(repo_root: Path, extension_run: Path) -> list[M2Case]:
    split = json.loads((repo_root / "configs/m2-one-shot-splits.json").read_text(encoding="utf-8"))
    if split.get("schema_version") != "colluscope-m2-one-shot-splits-v1":
        raise ValueError("unsupported M2 split manifest")
    groups = split["groups"]
    by_id = {row["split_group_id"]: row for row in groups}
    if len(by_id) != 20 or sum(row["episode_count"] for row in groups) != 100:
        raise ValueError("M2 split manifest must contain 20 matched groups and 100 rows")
    hist_dir = repo_root / "runs/m1_p0_local/formal-25ep-pilot-20261019/run"
    old = _load_one_source(repo_root, hist_dir, "historical_F0", by_id, indexed_evidence=False)
    new = _load_one_source(repo_root, extension_run, "prospective_M1_100", by_id,
                           indexed_evidence=True)
    cases = old + new
    if len(cases) != 100 or len({case.episode_id for case in cases}) != 100:
        raise ValueError("M2 corpus must contain 100 unique historical/new episodes")
    counts: dict[str, int] = {}
    for case in cases:
        counts[case.partition] = counts.get(case.partition, 0) + 1
    if counts != {"F0": 25, "F1": 25, "F2": 25, "F3": 25}:
        raise ValueError(f"M2 split partitions have incomplete counts: {counts}")
    for group_id, group in by_id.items():
        rows = [case for case in cases if case.split_group_id == group_id]
        if len(rows) != 5 or {case.condition_id for case in rows} != set(group["condition_ids"]):
            raise ValueError(f"matched group is incomplete or conditions cross split: {group_id}")
    return cases

