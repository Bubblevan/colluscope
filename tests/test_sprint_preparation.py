import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_sprint_baselines import _write_csv  # noqa: E402


def test_csv_export_accepts_offline_and_not_run_rows_with_distinct_fields(tmp_path):
    path = tmp_path / "mixed-results.csv"
    _write_csv(path, [
        {"baseline": "B1", "result_status": "SCRIPTED_OFFLINE_SANITY_ONLY", "score": 1.0},
        {"baseline": "B2", "result_status": "NOT_RUN", "score": None, "token_cost": None},
    ])
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [
        {"baseline": "B1", "result_status": "SCRIPTED_OFFLINE_SANITY_ONLY", "score": "1.0", "token_cost": ""},
        {"baseline": "B2", "result_status": "NOT_RUN", "score": "", "token_cost": ""},
    ]
