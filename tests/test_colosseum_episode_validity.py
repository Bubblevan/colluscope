"""Counterexample tests for the independent VALID_EPISODE gate."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IGNORED_OUTPUTS = ROOT / "reference" / "colosseum" / "experiments" / "collusion" / "outputs"
MODULE_PATH = ROOT / "reproductions" / "colosseum_local" / "episode_validity.py"
spec = importlib.util.spec_from_file_location("colluscope_episode_validity_tests", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def write_json(path: Path, value):
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows):
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


class EpisodeValidityTests(unittest.TestCase):
    def fixture(self, root: Path, *, errors=0, missing_commit=False, missing_capture=False):
        episode = "pair__seed1"
        output = root / "upstream"
        output.mkdir()
        agents = [f"A{i}" for i in range(6)]
        turns = []
        for agent in agents:
            for round_number in range(1, 5):
                turns.append({"phase": "planning", "planning_round": round_number,
                              "agent": agent, "response": "", "tools_executed": 0,
                              "conversation_steps": 1})
        for index, agent in enumerate(agents):
            response = "[ERROR] synthetic continuation failure" if index < errors else "assigned"
            turns.append({"phase": "execution", "planning_round": None,
                          "agent": agent, "response": response, "tools_executed": 1,
                          "conversation_steps": 1})
        tools = []
        for index, agent in enumerate(agents):
            if missing_commit and index == 5:
                result = {"status": "error", "result": {"error": "synthetic rejection"}}
            else:
                result = {"status": "success", "result": {"state_updates": {"assigned": True}}}
            tools.append({"phase": "execution", "tool_name": "assign_task",
                          "agent_name": agent, "result": result})
        write_json(output / "agent_turns.json", turns)
        write_json(output / "tool_events.json", tools)
        write_json(output / "final_summary.json", {"status": "complete"})
        write_jsonl(root / "progress.json", [{"episode_id": episode, "event": "episode_started"},
                                              {"episode_id": episode, "event": "episode_terminal",
                                               "status": "runner_returned", "upstream_output": str(output)}])
        requests = []
        captures = []
        response_hash = hashlib.sha256(b"{}").hexdigest().upper()
        for attempt in range(1, 31):
            request_body = f"request-{attempt}".encode()
            body_hash = hashlib.sha256(request_body).hexdigest().upper()
            request_file = f"attempt-{attempt:04d}.request.bin"
            response_file = f"attempt-{attempt:04d}.response.bin"
            (root / request_file).write_bytes(request_body)
            (root / response_file).write_bytes(b"{}")
            requests.append({"episode_id": episode, "event": "http_attempt_started",
                             "attempt": attempt, "request_sha256": body_hash})
            requests.append({"episode_id": episode, "event": "http_response", "attempt": attempt,
                             "response_sha256": response_hash, "response_bytes": 2,
                             "status_code": 400 if errors and attempt == 2 else 200})
            captures.append({"episode_id": episode, "event": "http_attempt_started", "attempt": attempt,
                             "request_body_sha256": body_hash, "endpoint": "http://127.0.0.1:8081/v1/chat/completions",
                             "request_body_bytes": len(request_body), "request_body_path": request_file,
                             "method": "POST", "auth_headers_recorded": False})
            captures.append({"episode_id": episode, "event": "http_attempt_terminal", "attempt": attempt,
                             "status": "http_response", "status_code": 200,
                             "response_body_sha256": response_hash, "response_body_bytes": 2,
                             "response_body_path": response_file})
        write_jsonl(root / "http.jsonl", requests)
        capture_path = root / "capture.jsonl"
        write_jsonl(capture_path, captures)
        if missing_capture:
            capture_path.unlink()
        return episode, output, root / "progress.json", root / "http.jsonl", capture_path

    def assess(self, fixture):
        episode, output, progress, requests, capture = fixture
        return module.assess_episode(
            episode_id=episode, output_root=output,
            progress_ledger=progress, request_ledger=requests,
            raw_capture_index=capture,
        )

    def test_complete_runner_status_is_not_valid_when_turns_and_http_fail(self):
        with tempfile.TemporaryDirectory(dir=IGNORED_OUTPUTS) as temp:
            result = self.assess(self.fixture(Path(temp), errors=2))
            self.assertEqual(result["runner_status_observed"], "runner_returned")
            self.assertEqual(result["status"], "INVALID_EPISODE")
            self.assertIn("agent_turn_error_response", result["reason_codes"])
            self.assertIn("non_200_http_response", result["reason_codes"])

    def test_missing_execution_commit_is_invalid_even_with_complete_summary(self):
        with tempfile.TemporaryDirectory(dir=IGNORED_OUTPUTS) as temp:
            result = self.assess(self.fixture(Path(temp), missing_commit=True))
            self.assertEqual(result["status"], "INVALID_EPISODE")
            self.assertIn("execution_action_not_committed", result["reason_codes"])
            self.assertIn("tool_event_rejected", result["reason_codes"])

    def test_full_stage_and_attempt_evidence_is_valid_without_message_text_export(self):
        with tempfile.TemporaryDirectory(dir=IGNORED_OUTPUTS) as temp:
            result = self.assess(self.fixture(Path(temp)))
            self.assertEqual(result["status"], "VALID_EPISODE")
            self.assertTrue(result["valid_episode"])
            self.assertEqual(result["turns"]["total"], 30)
            self.assertEqual(result["turns"]["committed_execution_actions"], 6)
            self.assertFalse(result["private_content_exported"])

    def test_runner_complete_but_missing_raw_capture_is_indeterminate(self):
        with tempfile.TemporaryDirectory(dir=IGNORED_OUTPUTS) as temp:
            result = self.assess(self.fixture(Path(temp), missing_capture=True))
            self.assertEqual(result["runner_status_observed"], "runner_returned")
            self.assertEqual(result["status"], "INDETERMINATE_EPISODE")
            self.assertIn("raw_request_response_capture_missing", result["reason_codes"])

    def test_unclosed_http_attempt_is_not_valid(self):
        with tempfile.TemporaryDirectory(dir=IGNORED_OUTPUTS) as temp:
            fixture = self.fixture(Path(temp))
            episode, output, progress, request_path, capture_path = fixture
            rows = [row for row in module._read_jsonl(request_path)
                    if not (row["event"] == "http_response" and row["attempt"] == 30)]
            write_jsonl(request_path, rows)
            result = module.assess_episode(
                episode_id=episode, output_root=output, progress_ledger=progress,
                request_ledger=request_path, raw_capture_index=capture_path,
            )
            self.assertNotEqual(result["status"], "VALID_EPISODE")
            self.assertIn("http_attempt_without_terminal_record", result["reason_codes"])

    def test_hidden_retry_or_generation_count_mismatch_is_invalid(self):
        with tempfile.TemporaryDirectory(dir=IGNORED_OUTPUTS) as temp:
            episode, output, progress, requests, capture = self.fixture(Path(temp))
            turns_path = output / "agent_turns.json"
            turns = module._read_json(turns_path)
            turns[0]["conversation_steps"] = 2
            write_json(turns_path, turns)
            result = module.assess_episode(
                episode_id=episode, output_root=output, progress_ledger=progress,
                request_ledger=requests, raw_capture_index=capture,
            )
            self.assertEqual(result["status"], "INVALID_EPISODE")
            self.assertIn("http_attempt_vs_agent_generation_mismatch", result["reason_codes"])

    def test_raw_response_hash_disagreement_is_invalid(self):
        with tempfile.TemporaryDirectory(dir=IGNORED_OUTPUTS) as temp:
            episode, output, progress, requests, capture = self.fixture(Path(temp))
            rows = module._read_jsonl(capture)
            rows[1]["response_body_sha256"] = "0" * 64
            write_jsonl(capture, rows)
            result = module.assess_episode(
                episode_id=episode, output_root=output, progress_ledger=progress,
                request_ledger=requests, raw_capture_index=capture,
            )
            self.assertEqual(result["status"], "INVALID_EPISODE")
            self.assertIn("raw_capture_response_hash_mismatch", result["reason_codes"])

    def test_missing_or_changed_raw_body_file_is_not_a_valid_episode(self):
        with tempfile.TemporaryDirectory(dir=IGNORED_OUTPUTS) as temp:
            episode, output, progress, requests, capture = self.fixture(Path(temp))
            (Path(temp) / "attempt-0001.request.bin").write_bytes(b"changed")
            result = module.assess_episode(
                episode_id=episode, output_root=output, progress_ledger=progress,
                request_ledger=requests, raw_capture_index=capture,
            )
            self.assertEqual(result["status"], "INVALID_EPISODE")
            self.assertIn("raw_capture_request_file_hash_mismatch", result["reason_codes"])


if __name__ == "__main__":
    unittest.main()
