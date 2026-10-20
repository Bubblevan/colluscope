import importlib.util
from unittest import mock
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "reproductions" / "colosseum_local" / "run_local_repro.py"
SPEC = importlib.util.spec_from_file_location("colosseum_local_repro", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ColosseumLocalReproTests(unittest.TestCase):
    def test_assignment_is_exactly_five_matched_seed_pairs(self):
        rows = MODULE.assignments()
        self.assertEqual(10, len(rows))
        for seed in MODULE.SEEDS:
            pair = [row for row in rows if row.seed == seed]
            self.assertEqual(2, len(pair))
            self.assertEqual({False, True}, {row.secret_channel_enabled for row in pair})
            self.assertEqual({"control"}, {row.prompt_variant for row in pair})

    def test_actual_upstream_call_graph_has_ninety_generation_upper_bound(self):
        self.assertEqual(6 * (4 + 1) * 3, MODULE.max_generation_bound())
        self.assertEqual(900, len(MODULE.assignments()) * MODULE.max_generation_bound())

    def test_llama_server_path_resolution_uses_explicit_path_or_exact_path_lookup(self):
        self.assertEqual(Path("E:/runtime/llama-server.exe"), MODULE.resolve_llama_server("E:/runtime/llama-server.exe"))
        with mock.patch.object(MODULE.shutil, "which", side_effect=lambda name: "C:/tools/llama-server.exe" if name == "llama-server.exe" else None):
            self.assertEqual(Path("C:/tools/llama-server.exe"), MODULE.resolve_llama_server(None))


if __name__ == "__main__":
    unittest.main()
