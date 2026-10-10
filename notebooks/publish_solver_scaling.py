"""Publish only complete solver scaling benchmarks into the README.

Chart SVGs are copied unchanged from the existing plotting implementation.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import statistics
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEM_COUNTS = (5, 10, 15, 20, 30, 50, 75, 100)
BOX_COUNTS = (3, 5, 10, 15, 20)
MODES = ("fast", "best")
CHARTS = (
    "solver_scaling_fast_heatmap.svg",
    "solver_scaling_best_heatmap.svg",
    "solver_scaling_best_breakdown.svg",
)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate(source: Path, repeats: int) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    raw = load_csv(source / "raw_results.csv")
    summary = load_csv(source / "summary.csv")
    expected = {
        (items, boxes, repeat, mode)
        for items in ITEM_COUNTS
        for boxes in BOX_COUNTS
        for repeat in range(1, repeats + 1)
        for mode in MODES
    }
    observed = [
        (int(row["items"]), int(row["box_types"]), int(row["repeat"]), row["mode"])
        for row in raw
    ]
    if len(observed) != len(expected) or set(observed) != expected:
        raise ValueError("Incomplete or duplicate raw benchmark runs; refusing to publish")
    expected_summary = {(items, boxes, mode) for items in ITEM_COUNTS for boxes in BOX_COUNTS for mode in MODES}
    actual_summary = [(int(row["items"]), int(row["box_types"]), row["mode"]) for row in summary]
    if len(actual_summary) != len(expected_summary) or set(actual_summary) != expected_summary:
        raise ValueError("Incomplete or duplicate summary; refusing to publish")
    for row in raw:
        if float(row["runtime_ms"]) < 0:
            raise ValueError("Negative runtime in raw results")
    for row in summary:
        key = (int(row["items"]), int(row["box_types"]), row["mode"])
        samples = [float(item["runtime_ms"]) for item in raw if
                   (int(item["items"]), int(item["box_types"]), item["mode"]) == key]
        if abs(float(row["median_runtime_ms"]) - statistics.median(samples)) > 0.002:
            raise ValueError(f"Summary median does not match raw results: {key}")
    for chart in CHARTS:
        path = source / chart
        if not path.is_file() or "<svg" not in path.read_text(encoding="utf-8")[:1000]:
            raise ValueError(f"Missing or invalid chart: {chart}")
    return raw, summary


def publish(source: Path, destination: Path, readme_path: Path, repeats: int) -> None:
    _, summary = validate(source, repeats)
    lookup = {(int(row["items"]), int(row["box_types"]), row["mode"]): row for row in summary}
    fast = float(lookup[(100, 20, "fast")]["median_runtime_ms"])
    best = float(lookup[(100, 20, "best")]["median_runtime_ms"])
    date_label = f"{date.today().day} {date.today():%B %Y}"
    readme = readme_path.read_text(encoding="utf-8")
    heading_pattern = r"### Solver execution time: Fast vs Best \([^\n]*\)"
    conclusion_pattern = r"\*\*Conclusion \([^\n]*?\):\*\*[^\n]*"
    heading = f"### Solver execution time: Fast vs Best ({date_label})"
    conclusion = (
        f"**Conclusion (refreshed uncapped {len(summary) * repeats}-run simulation):** "
        f"At 100 items and 20 carton types, Fast's median runtime was **{fast:,.1f} ms** "
        f"and Best's was **{best:,.1f} ms**. "
        "These are synthetic, uncapped runs, not measurements of the 5-second production Best budget. "
        "The objective is fewest cartons, then lowest total external carton volume. "
        "The charts and figures are generated from the saved benchmark results."
    )
    readme, heading_count = re.subn(heading_pattern, lambda _: heading, readme)
    readme, conclusion_count = re.subn(conclusion_pattern, lambda _: conclusion, readme)
    if heading_count != 1 or conclusion_count != 1:
        raise ValueError("Expected exactly one scaling heading and conclusion; README unchanged")
    destination.mkdir(parents=True, exist_ok=True)
    for filename in ("raw_results.csv", "summary.csv", *CHARTS):
        shutil.copyfile(source / filename, destination / filename)
    readme_path.write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--readme", type=Path, default=ROOT / "README.md")
    parser.add_argument("--repeats", type=int, required=True)
    args = parser.parse_args()
    publish(args.source, args.destination, args.readme, args.repeats)


if __name__ == "__main__":
    main()
