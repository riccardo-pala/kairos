import importlib.util
from pathlib import Path
import sys


RUNNER_PATH = Path(__file__).parents[1] / "evals/run_event_prompt_benchmark.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("event_prompt_benchmark", RUNNER_PATH)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = RUNNER
RUNNER_SPEC.loader.exec_module(RUNNER)
paired_turn_summary = RUNNER.paired_turn_summary


def _turn(tokens: int | None, elapsed_ms: float | None) -> dict:
    return {
        "ollama_metrics": {"prompt_eval_count": tokens},
        "end_to_end_ms": elapsed_ms,
    }


def test_paired_summary_compares_only_matching_scenario_turn_indexes() -> None:
    results = [
        {"scenario": "chain", "variant": "baseline", "turns": [_turn(100, 20), _turn(80, 10)]},
        {"scenario": "chain", "variant": "compact", "turns": [_turn(90, 25)]},
        {"scenario": "other", "variant": "baseline", "turns": [_turn(None, None)]},
        {"scenario": "other", "variant": "compact", "turns": [_turn(50, 5)]},
    ]

    summary = paired_turn_summary(results)

    assert summary["paired_turn_count"] == 2
    assert summary["paired_input_token_savings_mean"] == 10
    assert summary["paired_end_to_end_ms_delta_mean"] == -5
    assert [(p["scenario"], p["turn_index"]) for p in summary["pairs"]] == [
        ("chain", 0), ("other", 0)
    ]


def test_paired_summary_returns_null_metrics_without_valid_pairs() -> None:
    results = [
        {"scenario": "one-sided", "variant": "baseline", "turns": [_turn(12, 2)]},
        {"scenario": "all-null", "variant": "baseline", "turns": [_turn(None, None)]},
        {"scenario": "all-null", "variant": "compact", "turns": [_turn(None, None)]},
    ]

    summary = paired_turn_summary(results)

    assert summary["paired_turn_count"] == 1
    assert summary["paired_input_token_savings_mean"] is None
    assert summary["paired_end_to_end_ms_delta_mean"] is None
