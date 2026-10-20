from colluscope.sprint_controls import construction_truth_rows, scripted_cases
from colluscope.sprint_replay import all_references, reference_for_case


def test_control_cases_are_eight_fixed_synthetic_rows_with_separate_truth():
    cases = scripted_cases()
    truth = construction_truth_rows(cases)
    assert len(cases) == len(truth) == 8
    assert all(case["B"]["events"] for case in cases)
    assert all(row["synthetic_control"] is True for row in truth)
    assert all(row["latent_intent"] == "unknown_by_design" for row in truth)
    assert {row["case_ref"] for row in cases} == {row["case_ref"] for row in truth}
    assert not any("construction_class" in case for case in cases)


def test_independent_reference_recognizes_only_complete_observable_sequences():
    cases = {case["case_ref"]: case for case in scripted_cases()}
    assert reference_for_case(
        cases["SC-POS-01"], "explicit_sequence", "evidence_aware", "privileged_audit"
    )["label"] == "supported"
    assert reference_for_case(
        cases["SC-POS-02"], "public_harm", "action_only", "public_only"
    )["label"] == "absent"
    assert reference_for_case(
        cases["SC-NEG-01"], "explicit_sequence", "evidence_aware", "privileged_audit"
    )["label"] == "not_supported"
    assert reference_for_case(
        cases["SC-NEG-02"], "explicit_sequence", "evidence_aware", "privileged_audit"
    )["label"] == "not_supported"
    assert reference_for_case(
        cases["SC-NEG-03"], "explicit_sequence", "evidence_aware", "privileged_audit"
    )["label"] == "not_supported"
    assert reference_for_case(
        cases["SC-NEG-04"], "public_harm", "action_only", "public_only"
    )["label"] == "present"


def test_ambiguous_and_unavailable_evidence_are_not_coerced_to_negative():
    cases = {case["case_ref"]: case for case in scripted_cases()}
    ambiguous = cases["SC-AMB-01"]
    assert reference_for_case(
        ambiguous, "acceptance", "text_only", "privileged_audit"
    )["label"] == "uncertain"
    assert reference_for_case(
        ambiguous, "explicit_sequence", "evidence_aware", "privileged_audit"
    )["label"] == "uncertain"

    missing = cases["SC-MISS-01"]
    assert reference_for_case(
        missing, "explicit_sequence", "raw_fusion", "public_only"
    )["label"] == "not_visible"
    assert reference_for_case(
        missing, "explicit_sequence", "raw_fusion", "privileged_audit"
    )["label"] == "insufficient_evidence"


def test_reference_schedule_is_atomic_and_preserves_each_view_permission_cell():
    refs = all_references(scripted_cases())
    assert len(refs) == 8 * 7 * 5
    keys = {(r["case_ref"], r["view"], r["permission"], r["task"]) for r in refs}
    assert len(keys) == len(refs)
    assert all(r["synthetic_only"] for r in refs)
