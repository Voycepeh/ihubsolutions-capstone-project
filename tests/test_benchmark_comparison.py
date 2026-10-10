"""Guard against disagreement between notebook, README and comparison figures."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))
from benchmark_comparison import eligible_rows, objective, read_benchmark, reason, summarize, verdict  # noqa: E402


def test_canonical_benchmark_counts_reconcile():
    rows = read_benchmark(ROOT / "notebooks/artifacts/benchmark_2000_best_vs_ihub.csv")
    score = summarize(rows)
    assert score["total"] == 2000
    assert score["eligible"] + score["excluded"] == 2000
    assert score["eligible"] == len(eligible_rows(rows))
    for mode in ("fast", "best"):
        assert sum(score[mode].values()) == score["eligible"]
        breakdown = score[f"{mode}_reasons"]
        assert sum(sum(part.values()) for part in breakdown.values()) == (
            score[mode]["Better"] + score[mode]["Worse"]
        )
        for row in eligible_rows(rows):
            assert (reason(row, mode) is None) == (verdict(row, mode) == "Same")


def test_objective_ignores_largest_carton_tie_break():
    row = {
        "ihub_cartons": 2, "ihub_external_volume_mm3": 100,
        "ihub_largest_carton_volume_mm3": 80,
        "best_cartons": 2, "best_external_volume_mm3": 90,
        "best_largest_carton_volume_mm3": 85,
    }
    assert objective(row, "best") < objective(row, "ihub")
    assert verdict(row, "best") == "Better"
    assert reason(row, "best") == "multi"


def test_single_box_volume_breakdown():
    row = {
        "ihub_cartons": 1, "ihub_external_volume_mm3": 100,
        "fast_cartons": 1, "fast_external_volume_mm3": 80,
    }
    assert verdict(row, "fast") == "Better"
    assert reason(row, "fast") == "single"
