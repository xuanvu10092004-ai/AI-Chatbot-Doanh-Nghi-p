import json
from pathlib import Path

from scripts.run_ai_training_pilot import all_cases, run


def test_pilot_has_required_split_and_counts():
    cases = all_cases()
    assert len(cases) == 150
    assert {c["dataset_split"] for c in cases} == {"development", "validation", "test"}
    assert sum(c["dataset_split"] == "development" for c in cases) == 100
    assert sum(c["dataset_split"] == "validation" for c in cases) == 25
    assert sum(c["dataset_split"] == "test" for c in cases) == 25
    required = {"id", "question", "conversation_context", "department", "intent",
                "expected_route", "expected_entities", "required_permission",
                "expected_scope", "expected_behavior", "expected_result",
                "required_answer_facts", "difficulty", "source", "dataset_split"}
    assert all(required <= case.keys() for case in cases)


def test_pilot_offline_preflight_has_no_route_failures():
    _, counts = run(all_cases())
    assert counts["pass"] == 150
