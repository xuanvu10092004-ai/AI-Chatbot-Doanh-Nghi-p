"""Kiểm thử công cụ đánh giá chất lượng câu trả lời AI trên bộ câu hỏi chuẩn."""

from pathlib import Path

from scripts.ai_evaluation import evaluate_case, load_cases, validate_cases


DATASET = Path(__file__).parents[1] / "data" / "ai_questions" / "seed.jsonl"


def test_seed_dataset_has_ground_truth_shape():
    cases = load_cases(DATASET)
    assert len(cases) == 200
    assert validate_cases(cases) == []
    assert all(case["expected_entities"] is not None for case in cases)


def test_seed_dataset_baseline_routes_and_intents():
    cases = load_cases(DATASET)
    results = [evaluate_case(case) for case in cases]
    assert all(result["intent_ok"] for result in results)
    assert all(result["route_ok"] for result in results)
    assert all(result["plan_ok"] is not False for result in results)
