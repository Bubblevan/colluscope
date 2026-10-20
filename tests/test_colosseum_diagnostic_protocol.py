import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "colosseum-llama-tool-diagnostic-v1.json"


class ColosseumDiagnosticProtocolTests(unittest.TestCase):
    def test_diagnostic_is_one_forced_harmless_local_completion(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["request_budget"], {
            "logical_requests_max": 1,
            "physical_http_attempts_max": 1,
            "generated_completions_max": 1,
            "max_tokens": 128,
            "retries": 0,
            "episode_replays": 0,
        })
        self.assertEqual(config["endpoint"], "http://127.0.0.1:8081/v1/chat/completions")
        self.assertEqual(config["request"]["n"], 1)
        self.assertFalse(config["request"]["stream"])
        self.assertEqual(config["request"]["tool_choice"]["function"]["name"], "compat_probe")
        self.assertEqual(
            config["request"]["tools"][0]["function"]["parameters"]["properties"]["probe_id"]["enum"],
            ["COLLUSCOPE-CANARY-1"],
        )
        self.assertEqual(config["request"]["temperature"], 0)

    def test_diagnostic_does_not_authorize_paired_run_or_monitor_inference(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertIn("the 180-attempt paired episode experiment", config["not_authorized_by_this_file"])
        self.assertIn("monitor inference", config["not_authorized_by_this_file"])


if __name__ == "__main__":
    unittest.main()
