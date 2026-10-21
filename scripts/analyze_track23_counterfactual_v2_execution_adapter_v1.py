#!/usr/bin/env python3
"""Run the frozen v2 analyzer after supplying its omitted prompt constant."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ANALYZER_PATH = ROOT / "scripts/analyze_track23_counterfactual_v2.py"
PREREG_PATH = ROOT / "research/experiments/track23-counterfactual-delivery-v2/preregistration.json"


def main() -> int:
    prereg = json.loads(PREREG_PATH.read_bytes())
    frozen = next(
        row for row in prereg["protocol"]["frozen_inputs"]
        if row["path"] == "scripts/analyze_track23_counterfactual_v2.py"
    )
    actual = hashlib.sha256(ANALYZER_PATH.read_bytes()).hexdigest()
    if actual != frozen["sha256"]:
        raise RuntimeError("registered analyzer source changed; adapter will not run")

    sys.path.insert(0, str(ROOT / "src"))
    from colluscope.track23_counterfactual_v2 import NEUTRAL_TEXT

    spec = importlib.util.spec_from_file_location("track23_v2_frozen_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load registered analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.NEUTRAL_TEXT = NEUTRAL_TEXT
    print(json.dumps({
        "adapter": "analysis-only-global-constant-injection",
        "registered_analyzer_sha256": actual,
        "prompt_constant_source": "src/colluscope/track23_counterfactual_v2.py",
        "model_calls": 0,
    }, ensure_ascii=False))
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
