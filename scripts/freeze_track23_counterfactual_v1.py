#!/usr/bin/env python3
"""Freeze and preflight the Track 2.3 counterfactual-delivery schedule offline."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tokenizers import Tokenizer  # noqa: E402
from colluscope.deepseek_m4_v1 import agent_tool, canonical, request_payload, sha  # noqa: E402
from colluscope.track23_counterfactual_v1 import (  # noqa: E402
    ARMS, EXPERIMENT_ID, INPUT_BOUND, MAIN_CONTEXTS, OUTPUT_LIMIT,
    action_prompt, build_schedule, choose_counterproposal, message_for,
    settle, task_observation,
)

SOURCE = ROOT / "research/drafts/m1-package-24-matrix-scenarios-20261021.json"
TOKENIZER_PATH = ROOT / ".cache/deepseek-recipe/tokenizer-v41.json"
SCHEDULE_PATH = ROOT / "research/schedules/track23-counterfactual-delivery-v1.json"


def read_json(path: Path):
    return json.loads(path.read_bytes())


def all_assignments():
    import itertools
    return [dict(zip(("A", "B", "C"), values, strict=True))
            for values in itertools.permutations(("T1", "T2", "T3"))]


def token_upper(tokenizer: Tokenizer, messages: list[dict[str, str]]) -> tuple[int, int]:
    tool_name, schema = agent_tool("ballot")
    body = request_payload(interface="strict_function_calling", messages=messages,
                           tool_name=tool_name, schema=schema, output_limit=OUTPUT_LIMIT)
    prompt_tokens = len(tokenizer.encode(canonical(body).decode("utf-8")).ids)
    return prompt_tokens + 256, len(canonical(body))


def preflight(schedule: dict) -> dict:
    tokenizer = Tokenizer.from_file(str(TOKENIZER_PATH))
    assignments = all_assignments()
    contexts = schedule["pilot"] + schedule["main"]
    maximum = 0
    maximum_bytes = 0
    checked = 0
    for context in contexts:
        for agent in ("A", "B", "C"):
            messages = action_prompt(context, agent, stage="initial")
            upper, byte_count = token_upper(tokenizer, messages)
            maximum, maximum_bytes = max(maximum, upper), max(maximum_bytes, byte_count)
            checked += 1
        if context["phase"] == "pilot":
            ballot_triples = ((a, b, c) for a in assignments for b in assignments for c in assignments)
        else:
            ballot_triples = ((assignments[(i + 1) % 6], b, assignments[(i + 3) % 6])
                              for i, b in enumerate(assignments))
        for a, b, c in ballot_triples:
            ballots = {"A": a, "B": b, "C": c}
            proposal = choose_counterproposal(context, b)
            rendered: dict[str, bytes] = {}
            for arm in ARMS:
                msg = message_for(arm, b, proposal)
                messages = action_prompt(context, "B", stage="revision",
                                         ballots=ballots, message=msg)
                upper, byte_count = token_upper(tokenizer, messages)
                maximum, maximum_bytes = max(maximum, upper), max(maximum_bytes, byte_count)
                rendered[arm] = canonical(messages)
                checked += 1
            if rendered["N"] != rendered["P_MINUS"]:
                raise RuntimeError(f"N/P- prompt parity failed for {context['context_id']}")
            obs_hidden = task_observation(context, "B", stage="revision", ballots=ballots,
                                          message=message_for("P_PLUS", b, proposal))
            if not context["visible_target_to_AB"]:
                reward = obs_hidden["your_reward_rule"]
                if "the target is {" in reward or "target_allocation" in obs_hidden:
                    raise RuntimeError(f"hidden-target leak in {context['context_id']}")
                if proposal == context["target"]:
                    raise RuntimeError(f"hidden target appears in proposal for {context['context_id']}")
    if maximum > INPUT_BOUND:
        raise RuntimeError(f"prompt input upper bound {maximum} exceeds frozen {INPUT_BOUND}")
    peak_cost = (maximum * 1.32 + OUTPUT_LIMIT * 3.96) * schedule["maximum_frozen_schedule_requests"] / 1_000_000
    if peak_cost > 1.80:
        raise RuntimeError(f"maximum prompt cost reserve ${peak_cost:.8f} exceeds $1.80")
    if len(schedule["pilot"]) != 8 or len(schedule["main"]) != MAIN_CONTEXTS:
        raise RuntimeError("pilot/main context counts differ from preregistration")
    if schedule["assigned_agent_requests"] != 336:
        raise RuntimeError("agent-request schedule must contain 336 calls")
    return {
        "status": "PASS_OFFLINE_PREFLIGHT",
        "experiment_id": EXPERIMENT_ID,
        "prompt_variants_checked": checked,
        "max_tokenizer_tokens_plus_256_framing": maximum,
        "max_serialized_request_bytes": maximum_bytes,
        "max_output_tokens": OUTPUT_LIMIT,
        "maximum_schedule_peak_rate_reserve_usd": round(peak_cost, 10),
        "pilot_assigned_requests": schedule["pilot_contexts"] * 7 if "pilot_contexts" in schedule else 56,
        "main_assigned_requests": MAIN_CONTEXTS * 7,
        "N_P_MINUS_byte_parity": "PASS",
        "hidden_target_message_leak_check": "PASS",
        "model_calls": 0,
        "network_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if not args.freeze and not args.preflight:
        parser.error("choose --freeze and/or --preflight")
    if args.freeze:
        if SCHEDULE_PATH.exists():
            raise SystemExit("refusing to overwrite frozen schedule")
        schedule = build_schedule(read_json(SOURCE))
        core = dict(schedule)
        schedule["schedule_sha256"] = sha(canonical(core))
        SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULE_PATH.write_bytes(canonical(schedule) + b"\n")
        print(json.dumps({"frozen": str(SCHEDULE_PATH.relative_to(ROOT)),
                          "schedule_sha256": schedule["schedule_sha256"]}, indent=2))
    if args.preflight:
        schedule = read_json(SCHEDULE_PATH)
        core = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
        if sha(canonical(core)) != schedule.get("schedule_sha256"):
            raise SystemExit("frozen schedule digest mismatch")
        report = preflight(schedule)
        report["schedule_sha256"] = schedule["schedule_sha256"]
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
