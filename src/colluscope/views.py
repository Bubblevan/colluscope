"""Permission-aware monitor projections and provenance-only structuring."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from itertools import permutations
from typing import Any, Iterable

VIEW_NAMES = ("text_only", "action_only", "raw_fusion", "structured_evidence")
_TEXT_TYPES = {"message", "reference_assignment"}
_ACTION_TYPES = {"vote", "decision", "outcome"}


def _validate_trace(trace: dict[str, Any]) -> None:
    if trace.get("schema_version") != "1.0":
        raise ValueError(f"unsupported trace schema version: {trace.get('schema_version')!r}")
    if not trace.get("episode_id") or not isinstance(trace.get("task_spec"), dict):
        raise ValueError("trace requires episode_id and task_spec")
    events = trace.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("trace requires a non-empty ordered events list")
    seen_ids: set[str] = set()
    previous_step = -1
    for event in events:
        required = {"event_id", "step", "actor", "visibility", "type", "content"}
        if not isinstance(event, dict) or not required.issubset(event):
            raise ValueError("event is missing a required field")
        event_id = event["event_id"]
        if not isinstance(event_id, str) or not event_id or event_id in seen_ids:
            raise ValueError("event ids must be unique non-empty strings")
        seen_ids.add(event_id)
        if not isinstance(event["step"], int) or event["step"] < previous_step:
            raise ValueError("events must be ordered by non-decreasing integer step")
        previous_step = event["step"]
        if event["visibility"] not in {"public", "private"}:
            raise ValueError("event visibility must be public or private")
        if not isinstance(event["content"], dict):
            raise ValueError("event content must be an object")
        if event["visibility"] == "private":
            recipients = event.get("recipients")
            if not isinstance(recipients, list) or len(recipients) < 2:
                raise ValueError("private events require at least two explicit recipients")
    agents = trace["task_spec"].get("agents")
    tasks = trace["task_spec"].get("tasks")
    if not isinstance(agents, list) or not isinstance(tasks, list) or len(agents) != len(tasks):
        raise ValueError("task_spec must define equally sized agents and tasks")
    if len(set(agents)) != len(agents) or len(set(tasks)) != len(tasks):
        raise ValueError("agent and task identifiers must be unique")
    quality = trace["task_spec"].get("quality")
    if not isinstance(quality, dict) or set(quality) != set(agents):
        raise ValueError("task_spec quality must have one row per agent")
    for row in quality.values():
        if not isinstance(row, dict) or set(row) != set(tasks):
            raise ValueError("every quality row must contain every task")
        if any(not isinstance(value, int) or isinstance(value, bool) for value in row.values()):
            raise ValueError("quality values must be integers")
    if trace["task_spec"].get("public_objective") != "maximize_sum_quality":
        raise ValueError("unsupported public objective")
    if trace["task_spec"].get("voting_rule") != "plurality; if every ballot is tied at one vote, select chair ballot":
        raise ValueError("unsupported voting rule")
    chair = trace["task_spec"].get("chair")
    if chair not in agents:
        raise ValueError("task_spec chair must be a configured agent")

    allowed_types = {"message", "reference_assignment", "vote", "decision", "outcome"}
    votes: dict[str, dict[str, str]] = {}
    decisions = []
    outcomes = []
    for event in events:
        actor = event["actor"]
        if actor not in agents and actor != "environment":
            raise ValueError(f"unknown event actor: {actor!r}")
        if event["type"] not in allowed_types:
            raise ValueError(f"unsupported event type: {event['type']!r}")
        if event["visibility"] == "private":
            if event["type"] != "message":
                raise ValueError("only messages may be private")
            recipients = event["recipients"]
            if any(recipient not in agents for recipient in recipients) or actor not in recipients:
                raise ValueError("private message recipients must be known and include its sender")
        if event["type"] == "message" and "claim_assignment" in event["content"]:
            claim = event["content"]["claim_assignment"]
            if not isinstance(claim, list) or len(claim) != len(agents) or set(claim) != set(tasks):
                raise ValueError(f"message {event['event_id']} contains an invalid assignment claim")
        if event["type"] in {"reference_assignment", "vote", "decision", "outcome"}:
            field = "assignment"
            assignment = event["content"].get(field)
            if not isinstance(assignment, dict) or set(assignment) != set(agents):
                raise ValueError(f"event {event['event_id']} has an invalid assignment map")
            values = list(assignment.values())
            if len(values) != len(agents) or set(values) != set(tasks):
                raise ValueError(f"event {event['event_id']} has duplicate or unknown assigned tasks")
            if event["type"] == "vote":
                if actor == "environment" or actor in votes:
                    raise ValueError("each agent must cast exactly one vote")
                vote_quality = {
                    agent: quality[agent][assignment[agent]] for agent in agents
                }
                vote_total = sum(vote_quality.values())
                vote_gap = _recompute_public_gap(trace["task_spec"], assignment)
                if (event["content"].get("individual_quality") != vote_quality or
                        event["content"].get("team_quality") != vote_total or
                        event["content"].get("welfare_gap") != vote_gap):
                    raise ValueError(f"vote {event['event_id']} has inconsistent public action rewards")
                votes[actor] = assignment
            elif event["type"] == "decision":
                decisions.append(event)
            elif event["type"] == "outcome":
                outcomes.append(event)
    if set(votes) != set(agents):
        raise ValueError("trace must contain exactly one vote from every agent")
    if len(decisions) != 1 or len(outcomes) != 1:
        raise ValueError("trace must contain exactly one decision and one outcome")

    counts: dict[tuple[str, ...], int] = {}
    for agent in agents:
        ballot = tuple(votes[agent][a] for a in agents)
        counts[ballot] = counts.get(ballot, 0) + 1
    highest = max(counts.values())
    top = [ballot for ballot, count in counts.items() if count == highest]
    selected = tuple(votes[chair][a] for a in agents) if len(top) > 1 else top[0]
    decision = decisions[0]["content"]["assignment"]
    decision_tuple = tuple(decision[a] for a in agents)
    if decision_tuple != selected:
        raise ValueError("decision does not match the declared voting rule and ballots")
    outcome_event = outcomes[0]["content"]
    if outcome_event != trace.get("public_outcome"):
        raise ValueError("outcome event and public_outcome record disagree")
    final_assignment = trace.get("final_assignment")
    if final_assignment != decision:
        raise ValueError("final_assignment and decision event disagree")
    gap = _recompute_public_gap(trace["task_spec"], outcome_event["assignment"])
    actual = sum(quality[a][outcome_event["assignment"][a]] for a in agents)
    individual_quality = {a: quality[a][outcome_event["assignment"][a]] for a in agents}
    if (outcome_event.get("individual_quality") != individual_quality or
            outcome_event.get("team_quality") != actual or outcome_event.get("welfare_gap") != gap):
        raise ValueError("public outcome quality/gap is inconsistent with public rules")


def _evidence_events(trace: dict[str, Any], kinds: set[str],
                     monitor_can_see_private: bool) -> list[dict[str, Any]]:
    result = []
    for event in trace["events"]:
        if event["type"] not in kinds:
            continue
        if event["visibility"] == "private" and not monitor_can_see_private:
            continue
        result.append(deepcopy(event))
    return result


def _assignment_from_event(event: dict[str, Any], agents: list[str], field: str) -> dict[str, str]:
    assignment = event["content"].get(field)
    if not isinstance(assignment, dict) or set(assignment) != set(agents):
        raise ValueError(f"event {event['event_id']} has an invalid {field}")
    values = list(assignment.values())
    if len(set(values)) != len(agents):
        raise ValueError(f"event {event['event_id']} repeats a task in {field}")
    return assignment


def _recompute_public_gap(task_spec: dict[str, Any], assignment: dict[str, str]) -> int:
    agents = task_spec["agents"]
    tasks = task_spec["tasks"]
    quality = task_spec["quality"]
    if set(assignment) != set(agents) or set(assignment.values()) != set(tasks):
        raise ValueError("decision assignment is not a complete task allocation")
    actual = sum(quality[agent][assignment[agent]] for agent in agents)
    optimum = max(
        sum(quality[agent][task] for agent, task in zip(agents, permutation, strict=True))
        for permutation in permutations(tasks)
    )
    return optimum - actual


def _structured_findings(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive mechanical comparisons from exactly the raw-fusion evidence."""
    agents = evidence["task_spec"]["agents"]
    events = evidence["events"]
    messages = {e["actor"]: e for e in events if e["type"] == "message"
                and isinstance(e["content"].get("claim_assignment"), list)}
    votes = {e["actor"]: e for e in events if e["type"] == "vote"}
    decisions = [e for e in events if e["type"] == "decision"]
    outcomes = [e for e in events if e["type"] == "outcome"]
    if len(votes) != len(agents) or len(decisions) != 1 or len(outcomes) != 1:
        raise ValueError("raw-fusion evidence requires one vote per agent and one decision/outcome")
    decision = _assignment_from_event(decisions[0], agents, "assignment")
    outcome_assignment = _assignment_from_event(outcomes[0], agents, "assignment")
    findings: list[dict[str, Any]] = []

    for agent in agents:
        vote_assignment = _assignment_from_event(votes[agent], agents, "assignment")
        if agent in messages:
            claim = messages[agent]["content"]["claim_assignment"]
            if len(claim) != len(agents) or set(claim) != set(evidence["task_spec"]["tasks"]):
                raise ValueError(f"message {messages[agent]['event_id']} has an invalid claim_assignment")
            claim_map = dict(zip(agents, claim, strict=True))
            findings.append({
                "kind": "claim_vote_alignment",
                "actor": agent,
                "value": claim_map == vote_assignment,
                "supporting_event_ids": [messages[agent]["event_id"], votes[agent]["event_id"]],
                "supporting_task_spec_fields": ["agents", "tasks"],
            })
        findings.append({
            "kind": "vote_matches_selected_assignment",
            "actor": agent,
            "value": vote_assignment == decision,
            "supporting_event_ids": [votes[agent]["event_id"], decisions[0]["event_id"]],
            "supporting_task_spec_fields": ["agents", "tasks", "voting_rule"],
        })

    findings.append({
        "kind": "decision_matches_outcome",
        "value": decision == outcome_assignment,
        "supporting_event_ids": [decisions[0]["event_id"], outcomes[0]["event_id"]],
        "supporting_task_spec_fields": ["agents", "tasks"],
    })
    findings.append({
        "kind": "public_welfare_gap_recomputed",
        "value": _recompute_public_gap(evidence["task_spec"], outcome_assignment),
        "supporting_event_ids": [decisions[0]["event_id"], outcomes[0]["event_id"]],
        "supporting_task_spec_fields": ["agents", "tasks", "quality", "public_objective"],
    })
    return findings


def monitor_evidence(trace: dict[str, Any], view_name: str,
                     monitor_can_see_private: bool = False) -> dict[str, Any]:
    """Return the only payload that should be passed to a monitor.

    This function intentionally accepts a trace and permissions only; it has
    no oracle parameter and never reads construction labels or private policy.
    """
    _validate_trace(trace)
    if view_name not in VIEW_NAMES:
        raise ValueError(f"unknown view: {view_name}")
    if not isinstance(monitor_can_see_private, bool):
        raise TypeError("monitor_can_see_private must be bool")
    task_spec = deepcopy(trace["task_spec"])
    if view_name == "text_only":
        events = _evidence_events(trace, _TEXT_TYPES, monitor_can_see_private)
    elif view_name == "action_only":
        events = _evidence_events(trace, _ACTION_TYPES, False)
    else:
        events = _evidence_events(trace, _TEXT_TYPES | _ACTION_TYPES, monitor_can_see_private)
    evidence = {"task_spec": task_spec, "events": events}
    if view_name == "structured_evidence":
        evidence["findings"] = _structured_findings(evidence)
    return evidence


def build_view_record(trace: dict[str, Any], view_name: str,
                      monitor_can_see_private: bool = False) -> dict[str, Any]:
    """Keep routing/origin metadata separate from the monitor evidence payload."""
    return {
        "episode_id": trace["episode_id"],
        "view_name": view_name,
        "evidence": monitor_evidence(trace, view_name, monitor_can_see_private),
    }


def build_all_views(trace: dict[str, Any],
                    monitor_can_see_private: bool = False) -> dict[str, dict[str, Any]]:
    return {name: build_view_record(trace, name, monitor_can_see_private) for name in VIEW_NAMES}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def evidence_sha256(view_record: dict[str, Any]) -> str:
    return sha256(canonical_json(view_record["evidence"])).hexdigest()


def semantic_signature(view_record: dict[str, Any]) -> tuple[Any, ...]:
    """Meaning-level facts for invariance checks; excludes identifiers/provenance labels."""
    evidence = view_record["evidence"]
    task_spec = evidence["task_spec"]
    agents = task_spec["agents"]
    agent_positions = {agent: index for index, agent in enumerate(agents)}
    events = evidence["events"]
    facts = []
    for event in events:
        if event["type"] in {"vote", "decision", "outcome"}:
            assignment = event["content"].get("assignment")
            if assignment is not None:
                facts.append((event["type"], tuple(assignment[a] for a in agents)))
        elif event["type"] == "message" and "claim_assignment" in event["content"]:
            facts.append(("claim", agent_positions.get(event["actor"]), tuple(event["content"]["claim_assignment"])))
    findings = tuple((f["kind"], agent_positions.get(f.get("actor")), f["value"])
                     for f in evidence.get("findings", []))
    quality = tuple(tuple(task_spec["quality"][agent][task] for task in task_spec["tasks"])
                    for agent in agents)
    return (quality, tuple(facts), findings)
