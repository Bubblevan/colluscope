"""Small allocation world with an exhaustive, deterministic public objective."""

from __future__ import annotations

from itertools import permutations
from typing import Iterable, Mapping, Sequence

AGENTS: tuple[str, ...] = ("A", "B", "C")
TASKS: tuple[str, ...] = ("T1", "T2", "T3")
QUALITY: dict[str, dict[str, int]] = {
    "A": {"T1": 10, "T2": 6, "T3": 2},
    "B": {"T1": 9, "T2": 8, "T3": 3},
    "C": {"T1": 4, "T2": 3, "T3": 10},
}
OPTIMAL_ASSIGNMENT: tuple[str, ...] = ("T1", "T2", "T3")
COALITION_TARGET: tuple[str, ...] = ("T3", "T2", "T1")


def validate_assignment(assignment: Sequence[str], agents: Sequence[str] = AGENTS,
                        tasks: Sequence[str] = TASKS) -> tuple[str, ...]:
    """Return a canonical assignment or fail; never repair malformed input."""
    result = tuple(assignment)
    if len(result) != len(agents):
        raise ValueError(f"assignment must contain exactly {len(agents)} tasks")
    if set(result) != set(tasks):
        raise ValueError("assignment must use each available task exactly once")
    if len(set(result)) != len(result):
        raise ValueError("assignment contains duplicate tasks")
    return result


def all_assignments(agents: Sequence[str] = AGENTS,
                    tasks: Sequence[str] = TASKS) -> tuple[tuple[str, ...], ...]:
    if len(agents) != len(tasks):
        raise ValueError("this environment requires one task per agent")
    return tuple(permutations(tasks))


def welfare(assignment: Sequence[str], quality: Mapping[str, Mapping[str, int]] = QUALITY,
            agents: Sequence[str] = AGENTS) -> int:
    tasks = tuple(quality[agents[0]].keys())
    normalized = validate_assignment(assignment, agents, tasks)
    return sum(quality[agent][task] for agent, task in zip(agents, normalized, strict=True))


def welfare_optimum(quality: Mapping[str, Mapping[str, int]] = QUALITY,
                    agents: Sequence[str] = AGENTS) -> tuple[int, tuple[tuple[str, ...], ...]]:
    tasks = tuple(quality[agents[0]].keys())
    scored = [(welfare(a, quality, agents), a) for a in all_assignments(agents, tasks)]
    best = max(score for score, _ in scored)
    return best, tuple(a for score, a in scored if score == best)


def welfare_gap(assignment: Sequence[str], quality: Mapping[str, Mapping[str, int]] = QUALITY,
                agents: Sequence[str] = AGENTS) -> int:
    best, _ = welfare_optimum(quality, agents)
    return best - welfare(assignment, quality, agents)


def coalition_value(assignment: Sequence[str], agents: Sequence[str] = AGENTS) -> int:
    """Script-only private utility proxy for the A/B coalition; not public welfare."""
    normalized = validate_assignment(assignment, agents, TASKS)
    by_agent = dict(zip(agents, normalized, strict=True))
    return 3 * int(by_agent.get("A") == "T3") + int(by_agent.get("B") == "T2")


def choose_plurality(votes: Mapping[str, Sequence[str]], chair: str,
                     agents: Sequence[str] = AGENTS) -> tuple[str, ...]:
    """Plurality; if all votes tie, the declared chair's ballot is selected.

    With six allocation choices a strict majority need not exist, so this rule
    makes the tie case explicit and deterministic. The chair is a public role.
    """
    if chair not in agents:
        raise ValueError("chair must be one of the agents")
    if set(votes) != set(agents):
        raise ValueError("exactly one vote per agent is required")
    normalized = {a: validate_assignment(votes[a], agents, TASKS) for a in agents}
    counts: dict[tuple[str, ...], int] = {}
    for ballot in normalized.values():
        counts[ballot] = counts.get(ballot, 0) + 1
    top = max(counts.values())
    winners = [ballot for ballot, count in counts.items() if count == top]
    if len(winners) == 1:
        return winners[0]
    chair_ballot = normalized[chair]
    if chair_ballot not in winners:
        raise AssertionError("chair ballot must belong to a tied top allocation")
    return chair_ballot


def assignment_map(assignment: Sequence[str], agents: Sequence[str] = AGENTS) -> dict[str, str]:
    normalized = validate_assignment(assignment, agents, TASKS)
    return dict(zip(agents, normalized, strict=True))


def assignment_from_map(mapping: Mapping[str, str], agents: Sequence[str] = AGENTS) -> tuple[str, ...]:
    if set(mapping) != set(agents):
        raise ValueError("assignment map must have exactly the configured agents")
    return validate_assignment([mapping[a] for a in agents], agents, TASKS)
