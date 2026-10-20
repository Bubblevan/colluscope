from __future__ import annotations

import json
from pathlib import Path

from colluscope.deepseek_monitor_v1 import build_plan, verify_plan
from scripts import prepare_full_research_monitor as legacy
from scripts import run_m4_offline

ROOT = Path(__file__).resolve().parents[1]


def _controls():
    return [json.loads(line) for line in
        (ROOT / "data/sprint-baseline-v1/controls.jsonl").read_text(encoding="utf-8").splitlines() if line]


def test_scripted_and_matched_monitor_plans_are_complete_and_blind():
    for interface in ("strict_function_calling", "json_object_fallback"):
        controls, control_meta = build_plan(m4_run=Path("unused"), interface=interface,
                                             phase="scripted_controls")
        assert len(controls) == 16
        assert verify_plan(controls, control_meta, interface=interface,
                           phase="scripted_controls")["status"] == "PASS"
        worlds, world_meta = build_plan(m4_run=Path("unused"), interface=interface,
                                         phase="matched_worlds")
        assert len(worlds) == 72
        result = verify_plan(worlds, world_meta, interface=interface, phase="matched_worlds")
        assert result["matched_public_equal_checks"] == 24
        public_rows = [row for row in worlds if row["permission"] == "public_only"]
        assert len(public_rows) == 24
        assert all(len(row["references"]) == 2 for row in public_rows)
        assert all(row["deduplicated_world_ids"] and len(row["deduplicated_world_ids"]) == 2
                   for row in public_rows)


def test_all_288_trace_rows_keep_every_group_and_permission(monkeypatch):
    _base, _scenarios, splits, _positive = run_m4_offline.load_documents()
    control = next(row for row in _controls() if row["case_ref"] == "SC-POS-01")
    sources = []
    for index, group in enumerate(splits["groups"]):
        source = json.loads(json.dumps(control))
        source["case_ref"] = f"TEST-M4-{index:02d}"
        source["split_group_id"] = group["split_group_id"]
        source["scenario_family_id"] = group["scenario_family_id"]
        source["partition"] = "synthetic_offline_plan_fixture"
        source["T"]["split_group_id"] = group["split_group_id"]
        sources.append(source)

    monkeypatch.setattr(legacy, "_m4_sources",
        lambda _run: (sources, {"fixture_only": True, "real_model_behavior": False}))
    six, meta_six = build_plan(m4_run=Path("unused"), interface="strict_function_calling", phase="m4_six")
    rest, meta_rest = build_plan(m4_run=Path("unused"), interface="strict_function_calling", phase="m4_remaining")
    assert len(six) == 72 and len(rest) == 216
    assert len({row["split_group_id"] for row in six}) == 6
    assert len({row["split_group_id"] for row in rest}) == 18
    for rows, metadata, phase in ((six, meta_six, "m4_six"), (rest, meta_rest, "m4_remaining")):
        assert verify_plan(rows, metadata, interface="strict_function_calling", phase=phase)["status"] == "PASS"
        assert {row["baseline_id"] for row in rows} == {"B4_raw_fusion", "B5_evidence_aware"}
        assert {row["permission"] for row in rows} == {"public_only", "privileged_audit"}
        assert {row["task"] for row in rows} == {"explicit_sequence", "action_concordance", "public_harm"}


def test_public_only_request_excludes_private_message_text():
    controls, _ = build_plan(m4_run=Path("unused"), interface="strict_function_calling",
                             phase="scripted_controls")
    row = next(item for item in controls if item["case_ref"] == "SC-POS-01"
               and item["permission"] == "public_only")
    serialized = json.dumps(row["messages"], ensure_ascii=False)
    private_texts = [event.get("content", {}).get("text", "") for event in
        row["source"]["B"]["events"] if event.get("type") == "message"
        and event.get("visibility") == "private" and event.get("delivered") is True]
    assert private_texts
    assert all(text not in serialized for text in private_texts)


def test_public_and_privileged_same_world_are_distinct_permissions():
    controls, _ = build_plan(m4_run=Path("unused"), interface="strict_function_calling",
                             phase="scripted_controls")
    positive_public = next(row for row in controls if row["case_ref"] == "SC-POS-01"
                           and row["task"] == "public_harm" and row["permission"] == "public_only"
                           and row["baseline_id"] == "B4_raw_fusion")
    positive_privileged = next(row for row in controls if row["case_ref"] == "SC-POS-01"
                               and row["task"] == "public_harm" and row["permission"] == "privileged_audit"
                               and row["baseline_id"] == "B4_raw_fusion")
    assert positive_public["body_sha256"] != positive_privileged["body_sha256"]
    assert positive_public["references"][0]["label"] == "present"
    assert positive_privileged["references"][0]["label"] == "present"
