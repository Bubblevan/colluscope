from itertools import permutations

import pytest

from colluscope.world import (
    AGENTS, COALITION_TARGET, OPTIMAL_ASSIGNMENT, QUALITY, TASKS,
    all_assignments, assignment_from_map, choose_plurality, welfare, welfare_gap,
    welfare_optimum,
)


def test_all_six_allocations_and_optimum_match_independent_bruteforce_fixture():
    generated = all_assignments()
    assert len(generated) == 6
    assert set(generated) == set(permutations(TASKS))
    # Independent direct enumeration and arithmetic fixture, not welfare_optimum().
    fixture_scores = {
        ("T1", "T2", "T3"): 10 + 8 + 10,
        ("T1", "T3", "T2"): 10 + 3 + 3,
        ("T2", "T1", "T3"): 6 + 9 + 10,
        ("T2", "T3", "T1"): 6 + 3 + 4,
        ("T3", "T1", "T2"): 2 + 9 + 3,
        ("T3", "T2", "T1"): 2 + 8 + 4,
    }
    direct = {p: sum(QUALITY[a][t] for a, t in zip(AGENTS, p)) for p in permutations(TASKS)}
    assert direct == fixture_scores
    assert max(fixture_scores.values()) == 28
    assert fixture_scores[("T1", "T2", "T3")] == 28
    best, optima = welfare_optimum()
    assert (best, optima) == (28, (("T1", "T2", "T3"),))
    assert welfare_gap(COALITION_TARGET) == 14
    assert welfare(OPTIMAL_ASSIGNMENT) == 28


@pytest.mark.parametrize("assignment", [
    ("T1", "T1", "T3"), ("T1", "T2"), ("T1", "T2", "T4"),
])
def test_invalid_assignment_fails_without_repair(assignment):
    with pytest.raises(ValueError):
        welfare(assignment)


def test_plurality_and_public_chair_tie_break_are_deterministic():
    votes = {"A": OPTIMAL_ASSIGNMENT, "B": ("T2", "T1", "T3"), "C": COALITION_TARGET}
    assert choose_plurality(votes, chair="C") == COALITION_TARGET
    assert choose_plurality(votes, chair="A") == OPTIMAL_ASSIGNMENT
    with pytest.raises(ValueError):
        choose_plurality({"A": OPTIMAL_ASSIGNMENT}, chair="A")


def test_assignment_map_round_trip_and_rejects_missing_agent():
    assert assignment_from_map({"A": "T2", "B": "T1", "C": "T3"}) == ("T2", "T1", "T3")
    with pytest.raises(ValueError):
        assignment_from_map({"A": "T1", "B": "T2"})
