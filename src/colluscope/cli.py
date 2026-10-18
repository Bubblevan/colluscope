"""Offline generation and integrity verification CLI for M0."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import GENERATOR_VERSION, __version__
from .generation import MECHANISMS, make_episode
from .views import VIEW_NAMES, build_all_views, build_view_record, canonical_json, evidence_sha256

ROOT = Path(__file__).resolve().parents[2]
UPSTREAMS = [
    {"name": "Colosseum", "url": "https://github.com/umass-ai-safety/colosseum",
     "commit": "b077fe7e2f10566e92156cc12e06ffb2aac54790", "license": "not found at checked commit"},
    {"name": "LLM-Trust-Breaking", "url": "https://github.com/Jerick-1380/LLM-Trust-Breaking",
     "commit": "fd11aca351e52c65c929e1a7d46d9f087f237adf", "license": "not found at checked commit"},
    {"name": "TraceGuard", "url": "https://github.com/linhkid/TraceGuard",
     "commit": "0e2e8226d7ca98e0375ed3aa54f9a870a3794714", "license": "MIT"},
]


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(canonical_json(row) + b"\n" for row in rows)
    path.write_bytes(payload)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f"blank JSONL row at {path}:{line_number}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"expected JSON object at {path}:{line_number}")
            rows.append(value)
    return rows


def _load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("rb") as stream:
        config = tomllib.load(stream)
    required = {"schema_version", "seeds", "mechanisms", "monitor_can_see_private",
                "model_kind", "external_model_calls", "paid_api_calls"}
    if set(config) != required:
        raise ValueError(f"config keys must be exactly {sorted(required)}")
    if config["schema_version"] != "1.0" or config["model_kind"] != "scripted":
        raise ValueError("M0 supports only schema 1.0 and model_kind=scripted")
    seeds = config["seeds"]
    mechanisms = config["mechanisms"]
    if not isinstance(seeds, list) or len(seeds) < 4 or len(set(seeds)) != len(seeds):
        raise ValueError("config must contain at least four unique seeds")
    if any(not isinstance(seed, int) or isinstance(seed, bool) or seed < 0 for seed in seeds):
        raise ValueError("seeds must be non-negative integers")
    if mechanisms != list(MECHANISMS):
        raise ValueError(f"mechanisms must be exactly {list(MECHANISMS)} in this order")
    if not isinstance(config["monitor_can_see_private"], bool):
        raise ValueError("monitor_can_see_private must be bool")
    if config["external_model_calls"] != 0 or config["paid_api_calls"] != 0:
        raise ValueError("M0 refuses nonzero model/API call budgets")
    return config


def _source_snapshot() -> dict[str, Any]:
    selected = [ROOT / "pyproject.toml", ROOT / "configs" / "m0.toml"]
    for relative in ("src/colluscope", "tests"):
        directory = ROOT / relative
        if directory.exists():
            selected.extend(path for path in directory.rglob("*.py") if "__pycache__" not in path.parts)
    files = {
        path.relative_to(ROOT).as_posix(): _sha256_file(path)
        for path in sorted(set(selected)) if path.is_file()
    }
    aggregate = "\n".join(f"{name}\0{digest}" for name, digest in files.items()).encode()
    return {"sha256": _sha256_bytes(aggregate), "files": files}


def _git_state() -> dict[str, Any]:
    def local_git(args: list[str]) -> str | None:
        try:
            result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                                    text=True, check=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout.strip()

    commit = local_git(["rev-parse", "HEAD"])
    status = local_git(["status", "--porcelain"])
    return {"commit": commit, "working_tree_clean": status == "" if status is not None else None}


def _run_id(out_root: Path) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"m0-{timestamp}"
    candidate = base
    counter = 1
    while (out_root / candidate).exists() or (out_root / "oracle" / candidate).exists():
        candidate = f"{base}-{counter:02d}"
        counter += 1
    return candidate


def generate_run(config_path: Path, out_root: Path, command: list[str]) -> Path:
    config_path = config_path.resolve()
    config = _load_config(config_path)
    traces: list[dict[str, Any]] = []
    oracles: list[dict[str, Any]] = []
    for mechanism in config["mechanisms"]:
        for seed in config["seeds"]:
            trace, oracle = make_episode(mechanism, seed)
            traces.append(trace)
            oracles.append(oracle)
    if len(traces) != len(config["mechanisms"]) * len(config["seeds"]):
        raise AssertionError("generator emitted an unexpected episode count")

    out_root = out_root.resolve()
    run_id = _run_id(out_root)
    run_dir = out_root / run_id
    input_dir = run_dir / "inputs"
    oracle_dir = out_root / "oracle" / run_id
    input_dir.mkdir(parents=True, exist_ok=False)
    oracle_dir.mkdir(parents=True, exist_ok=False)

    trace_path = input_dir / "trace.jsonl"
    oracle_path = oracle_dir / "oracle.jsonl"
    _write_jsonl(trace_path, traces)
    _write_jsonl(oracle_path, oracles)
    view_paths: dict[str, Path] = {}
    for name in VIEW_NAMES:
        rows = [build_view_record(t, name, config["monitor_can_see_private"])["evidence"]
                for t in traces]
        path = input_dir / "views" / f"{name}.jsonl"
        _write_jsonl(path, rows)
        view_paths[name] = path

    config_copy = run_dir / "config.toml"
    config_copy.write_bytes(config_path.read_bytes())
    counts = Counter(o["mechanism_id"] for o in oracles)
    pair_count = 0
    oracle_by_id = {o["episode_id"]: o for o in oracles}
    trace_by_id = {t["episode_id"]: t for t in traces}
    for oracle in oracles:
        if oracle["mechanism_id"] != "C1":
            continue
        counterpart = next(o for o in oracles if o["mechanism_id"] == "C6"
                           and trace_by_id[o["episode_id"]]["seed"] == trace_by_id[oracle["episode_id"]]["seed"])
        c1_views = build_all_views(trace_by_id[oracle["episode_id"]], config["monitor_can_see_private"])
        c6_views = build_all_views(trace_by_id[counterpart["episode_id"]], config["monitor_can_see_private"])
        if all(c1_views[name]["evidence"] == c6_views[name]["evidence"] for name in VIEW_NAMES):
            pair_count += 1

    metrics = {
        "scope": "scripted_integrity_only",
        "episode_count": len(traces),
        "episodes_per_mechanism": dict(sorted(counts.items())),
        "view_episode_counts": {name: len(traces) for name in VIEW_NAMES},
        "c1_c6_identical_evidence_pairs_under_config": pair_count,
        "verified_facts": {
            "all_rows_marked_scripted": all(t["model_kind"] == "scripted" for t in traces),
            "exactly_six_cases_four_seeds_each": len(traces) == 24 and all(counts[m] == 4 for m in MECHANISMS),
            "scripted_harmful_positive_controls": sum(
                o["mechanism_id"] == "C1" and o["outcome_truth"]["harmful_action_executed"] for o in oracles),
            "paper_only_cases_without_harmful_action": sum(
                o["mechanism_id"] == "C3" and not o["outcome_truth"]["harmful_action_executed"] for o in oracles),
            "external_model_calls": 0,
            "paid_api_calls": 0,
        },
        "detector_metrics": None,
        "interpretation": "No scripted classification accuracy, FPR, or model-performance metric was computed.",
    }
    metrics_path = run_dir / "metrics.json"
    _write_json(metrics_path, metrics)

    hash_paths = [trace_path, oracle_path, *view_paths.values(), config_copy, metrics_path]
    hashes = {}
    for path in hash_paths:
        hashes[path.relative_to(run_dir).as_posix() if path.is_relative_to(run_dir)
               else Path("../oracle").joinpath(run_id, path.name).as_posix()] = _sha256_file(path)
    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project": "ColluScope M0",
        "colluscope_version": __version__,
        "generator_version": GENERATOR_VERSION,
        "model_kind": "scripted",
        "git": _git_state(),
        "python_version": sys.version.split()[0],
        "source_snapshot": _source_snapshot(),
        "config": {"file": "config.toml", "sha256": _sha256_file(config_copy), "values": config},
        "input_seeds": config["seeds"],
        "mechanisms": config["mechanisms"],
        "monitor_can_see_private": config["monitor_can_see_private"],
        "api_call_assertion": {"external_model_calls": 0, "paid_api_calls": 0,
                                "network_client_in_runner": False},
        "execution_environment": {"cpu_only": True, "network_client_in_runner": False,
                                  "pythonpath": "src (source checkout)"},
        "commands": [command, ["python", "-m", "colluscope", "verify", "--run", str(run_dir)]],
        "paths": {
            "monitor_input_root": "inputs/views",
            "trace": "inputs/trace.jsonl",
            "views": {name: f"inputs/views/{name}.jsonl" for name in VIEW_NAMES},
            "oracle": f"../oracle/{run_id}/oracle.jsonl",
            "metrics": "metrics.json",
        },
        "upstream_snapshots": UPSTREAMS,
        "sha256": hashes,
    }
    _write_json(run_dir / "manifest.json", manifest)
    return run_dir


def verify_run(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1.0" or manifest.get("model_kind") != "scripted":
        raise ValueError("unsupported M0 manifest")
    if manifest["api_call_assertion"] != {"external_model_calls": 0, "paid_api_calls": 0,
                                          "network_client_in_runner": False}:
        raise ValueError("manifest does not assert zero external/API calls")
    base = run_dir.parent.resolve()
    oracle_path = (run_dir / manifest["paths"]["oracle"]).resolve()
    allowed_oracle_root = (base / "oracle").resolve()
    if not oracle_path.is_relative_to(allowed_oracle_root):
        raise ValueError("oracle must be physically outside the monitor input/run directory")
    input_root = (run_dir / manifest["paths"]["monitor_input_root"]).resolve()
    if oracle_path.is_relative_to(input_root):
        raise ValueError("oracle is inside the monitor-input directory")

    checked = {}
    for relative, expected in manifest["sha256"].items():
        candidate = (run_dir / relative).resolve()
        if not candidate.is_relative_to(base):
            raise ValueError("manifest contains a path outside the M0 output root")
        actual = _sha256_file(candidate)
        if actual != expected:
            raise ValueError(f"SHA256 mismatch for {relative}")
        checked[relative] = actual

    traces = _read_jsonl(run_dir / manifest["paths"]["trace"])
    oracles = _read_jsonl(oracle_path)
    oracle_by_id = {row["episode_id"]: row for row in oracles}
    if len(oracle_by_id) != len(oracles) or len(traces) != len(oracles):
        raise ValueError("trace/oracle episode ids must be unique and one-to-one")
    if {t["episode_id"] for t in traces} != set(oracle_by_id):
        raise ValueError("trace and oracle episode ids differ")
    if any(trace.get("model_kind") != "scripted" for trace in traces):
        raise ValueError("M0 trace is not marked scripted")

    view_rows = {}
    audit_private = manifest["monitor_can_see_private"]
    for name, relative in manifest["paths"]["views"].items():
        rows = _read_jsonl(run_dir / relative)
        if len(rows) != len(traces):
            raise ValueError(f"view {name} has an unexpected row count")
        by_id = {trace["episode_id"]: row
                 for trace, row in zip(traces, rows, strict=True)}
        if len(by_id) != len(rows) or set(by_id) != set(oracle_by_id):
            raise ValueError(f"view {name} has duplicate or missing aligned episodes")
        for trace, row in zip(traces, rows, strict=True):
            expected = build_view_record(trace, name, audit_private)["evidence"]
            if row != expected:
                raise ValueError(f"view {name} does not match projection of its source trace")
        view_rows[name] = by_id

    counts = Counter(oracle["mechanism_id"] for oracle in oracles)
    expected_counts = {mechanism: len(manifest["input_seeds"]) for mechanism in MECHANISMS}
    if dict(counts) != expected_counts:
        raise ValueError(f"mechanism/seed coverage differs: {dict(counts)}")
    trace_by_id = {t["episode_id"]: t for t in traces}
    pairs = 0
    for c1 in (o for o in oracles if o["mechanism_id"] == "C1"):
        seed = trace_by_id[c1["episode_id"]]["seed"]
        c6 = next(o for o in oracles if o["mechanism_id"] == "C6" and
                  trace_by_id[o["episode_id"]]["seed"] == seed)
        if trace_by_id[c1["episode_id"]]["task_spec"] != trace_by_id[c6["episode_id"]]["task_spec"]:
            raise ValueError(f"C1/C6 background mismatch at seed {seed}")
        for name in VIEW_NAMES:
            same = view_rows[name][c1["episode_id"]] == view_rows[name][c6["episode_id"]]
            if not audit_private and not same:
                raise ValueError(f"C1/C6 public-only evidence differs at seed {seed}, {name}")
            if audit_private and name == "action_only" and not same:
                raise ValueError(f"C1/C6 action-only evidence unexpectedly differs at seed {seed}")
        if all(view_rows[name][c1["episode_id"]] ==
               view_rows[name][c6["episode_id"]] for name in VIEW_NAMES):
            pairs += 1
    if not audit_private and pairs != len(manifest["input_seeds"]):
        raise ValueError("public-only audit must preserve every paired non-identifiable evidence record")
    if audit_private and pairs != 0:
        raise ValueError("private-message permission should expose the C1/C6 mechanism difference")

    metrics = json.loads((run_dir / manifest["paths"]["metrics"]).read_text(encoding="utf-8"))
    if metrics.get("scope") != "scripted_integrity_only" or metrics.get("detector_metrics") is not None:
        raise ValueError("metrics file contains an unsupported scope or detector metric")
    result = {
        "status": "PASS",
        "run_id": manifest["run_id"],
        "checked_file_hashes": checked,
        "episode_count": len(traces),
        "episodes_per_mechanism": dict(sorted(counts.items())),
        "validated_views": {name: len(rows) for name, rows in view_rows.items()},
        "identical_c1_c6_evidence_pairs": pairs,
        "oracle_outside_monitor_input": True,
        "monitor_projection_recomputed_from_trace": True,
        "external_model_calls": 0,
        "paid_api_calls": 0,
        "detection_performance_claimed": False,
    }
    _write_json(run_dir / "verification.json", result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m colluscope", description="Offline, scripted M0 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    m0 = subparsers.add_parser("m0", help="generate a scripted M0 run without model/API calls")
    m0.add_argument("--config", required=True, type=Path)
    m0.add_argument("--out", required=True, type=Path)
    verify = subparsers.add_parser("verify", help="verify M0 artifacts, projections, and file hashes")
    verify.add_argument("--run", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "m0":
            command = ["python", "-m", "colluscope", "m0", "--config", str(args.config), "--out", str(args.out)]
            run_dir = generate_run(args.config, args.out, command)
            result = verify_run(run_dir)
            print(json.dumps({"status": "GENERATED_AND_VERIFIED", "run_dir": str(run_dir),
                              "verification": result}, ensure_ascii=False, sort_keys=True))
            return 0
        result = verify_run(args.run)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
