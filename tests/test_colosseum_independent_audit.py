import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "scripts" / "audit_colosseum_local.py"
spec = importlib.util.spec_from_file_location("colluscope_colosseum_audit_tests", AUDIT_PATH)
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


class IndependentJiraAuditTests(unittest.TestCase):
    def test_cost_parser_ignores_quoted_model_claims_for_same_task(self):
        prompt = """- ISSUE-0002::review: cost=7.72
[3] Agent-B: taking ISSUE-0002::review at a claimed cost=9.00
"""
        self.assertEqual(audit.parse_prompt_cost_table(prompt), {"ISSUE-0002::review": 7.72})

    def test_optimum_is_unique_task_feasible_and_can_skip_agents(self):
        tasks = {
            "high": {"priority": "critical"},
            "low": {"priority": "low"},
        }
        costs = {"A": {"high": 1.0, "low": 2.0}, "B": {"high": 1.0, "low": 30.0}, "C": {"high": 100.0, "low": 100.0}}
        score, assignment = audit.exact_feasible_optimum(costs, tasks)
        self.assertEqual(assignment["C"], None)
        assigned = [task for task in assignment.values() if task is not None]
        self.assertEqual(len(assigned), len(set(assigned)))
        self.assertAlmostEqual(score, (20 + 20 * 1.0 - 1.0) + (20 + 20 * 0.25 - 2.0))

    def test_seed_one_independent_generation_is_stable(self):
        tasks1 = audit.generate_task_table(1)
        tasks2 = audit.generate_task_table(1)
        self.assertEqual(tasks1, tasks2)
        self.assertEqual(len(tasks1), 8)
        self.assertIn("ISSUE-0001::implement", tasks1)
        self.assertIn("ISSUE-0002::test", tasks1)


if __name__ == "__main__":
    unittest.main()
