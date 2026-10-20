"""Read-only verification of the one-seed local pair freeze; no inference."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAIR_RUNNER = ROOT / "reproductions" / "colosseum_local" / "run_pair.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("colosseum_pair_freeze", PAIR_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load pair runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    runner = module.load_runner()
    out = args.out.resolve()
    module.configure_runner(runner, args.seed, out)
    manifest = module.verify_pair_freeze(runner, out, args.seed)
    receipt_path = out / "pair_freeze_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("manifest_sha256_after_metadata") != module.sha256_file(out / "frozen_protocol.json"):
        raise RuntimeError("freeze receipt does not match the manifest bytes")
    print(json.dumps({
        "status": "verified_no_model_calls",
        "protocol_id": manifest["protocol_id"],
        "episode_ids": [row["episode_id"] for row in manifest["frozen_configurations"]],
        "manifest_sha256": module.sha256_file(out / "frozen_protocol.json"),
        "hard_cap": module.PAIR_MAX_HTTP,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
