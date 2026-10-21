from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.deepseek_m4_v1 import (  # noqa: E402
    append_jsonl, canonical, request_payload, sha,
)
from colluscope.deepseek_real_coordination_v1 import (  # noqa: E402
    MAX_REQUESTS, build_schedule, messages_for, schemas,
)


def _write_first_control(run_dir: Path, *, tamper_request: bool = False) -> None:
    analyzer = importlib.import_module("scripts.analyze_deepseek_real_coordination_v1")
    schedule = build_schedule()
    row = schedule["requests"][0]
    messages, _meta = messages_for(row, schedule, {})
    tool_name, schema = schemas(row["kind"])
    body = canonical(request_payload(interface="strict_function_calling", messages=messages,
                                     tool_name=tool_name, schema=schema,
                                     output_limit=analyzer.OUTPUT_LIMIT))
    if tamper_request:
        body += b" "
    response = {
        "model": "deepseek-flash", "system_fingerprint": "unit-test-fingerprint",
        "choices": [{"finish_reason": "tool_calls", "message": {
            "content": None, "tool_calls": [{"type": "function", "function": {
                "name": tool_name, "arguments": json.dumps({"answer": "ALPHA"})
            }}]
        }}],
        "usage": {"prompt_tokens": 17, "completion_tokens": 3},
    }
    raw_response = canonical(response)
    request_id = row["request_id"]
    (run_dir / "requests").mkdir(parents=True)
    (run_dir / "responses").mkdir()
    (run_dir / "requests" / f"{request_id}.bin").write_bytes(body)
    (run_dir / "responses" / f"{request_id}.bin").write_bytes(raw_response)
    (run_dir / "requests" / f"{request_id}.meta.json").write_bytes(canonical({
        "request_id": request_id, "request_sha256": sha(body), "auth_header_saved": False,
        "metadata_not_sent": {"local_prompt_tokens_v41": 7},
    }))
    (run_dir / "provider_identity.json").write_bytes(canonical({
        "model": "deepseek-flash", "system_fingerprint": "unit-test-fingerprint",
    }))
    append_jsonl(run_dir / "attempts.jsonl", {
        "event": "attempt_started", "request_id": request_id,
        "request_sha256": sha(body), "reserved_peak_cost_usd": "0.0001",
        "at_utc": "2026-10-21T04:00:00Z", "auth_header_saved": False,
    })
    append_jsonl(run_dir / "attempts.jsonl", {
        "event": "attempt_terminal", "request_id": request_id, "status": "COMPLETED",
        "http_status": 200, "request_sha256": sha(body), "response_sha256": sha(raw_response),
        "estimated_peak_cost_usd": "0.0001",
    })


def test_independent_replay_reconstructs_raw_request_and_keeps_unattempted_denominator(tmp_path, monkeypatch):
    analyzer = importlib.import_module("scripts.analyze_deepseek_real_coordination_v1")
    tokenizer_path = tmp_path / ".cache/deepseek-recipe/tokenizer-v41.json"
    tokenizer_path.parent.mkdir(parents=True)
    tokenizer_path.write_bytes(b"fake-tokenizer")
    tokenizer_sha = sha(b"fake-tokenizer")

    class FakeTokenizer:
        @classmethod
        def from_file(cls, _path):
            return cls()

        def encode(self, _text):
            return SimpleNamespace(ids=[0] * 7)

    monkeypatch.setattr(analyzer, "ROOT", tmp_path)
    monkeypatch.setattr(analyzer, "TOKENIZER_SHA256", tokenizer_sha)
    monkeypatch.setattr(analyzer, "Tokenizer", FakeTokenizer)
    run_dir = tmp_path / "run"
    _write_first_control(run_dir)

    result = analyzer.replay(run_dir)

    assert result["issues"] == []
    assert result["physical_attempts"] == 1
    assert result["valid_actions_reconstructed"] == 1
    assert result["unattempted_assigned"] == MAX_REQUESTS - 1
    assert result["independent_behavioral_analysis"]["fact_control_rows"]["C1-delivered"]["correct"] is True


def test_independent_replay_detects_request_tampering_even_when_hashes_are_rewritten(tmp_path, monkeypatch):
    analyzer = importlib.import_module("scripts.analyze_deepseek_real_coordination_v1")
    tokenizer_path = tmp_path / ".cache/deepseek-recipe/tokenizer-v41.json"
    tokenizer_path.parent.mkdir(parents=True)
    tokenizer_path.write_bytes(b"fake-tokenizer")
    class FakeTokenizer:
        @classmethod
        def from_file(cls, _path):
            return cls()

        def encode(self, _text):
            return SimpleNamespace(ids=[0] * 7)
    monkeypatch.setattr(analyzer, "ROOT", tmp_path)
    monkeypatch.setattr(analyzer, "TOKENIZER_SHA256", sha(b"fake-tokenizer"))
    monkeypatch.setattr(analyzer, "Tokenizer", FakeTokenizer)
    run_dir = tmp_path / "run"
    _write_first_control(run_dir, tamper_request=True)

    result = analyzer.replay(run_dir)

    assert "reconstructed_request_mismatch:C1-delivered" in result["issues"]

