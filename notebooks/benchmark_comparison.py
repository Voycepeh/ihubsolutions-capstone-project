"""Canonical iHub benchmark population and lexicographic carton objective.

Both charts, README and Solver Demo must use these same definitions.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def read_benchmark(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row["order_id"] for row in rows]
    if len(ids) != 2000 or len(set(ids)) != 2000:
        raise ValueError("Expected 2,000 unique benchmark orders")
    return rows


def eligible_rows(rows: list[dict]) -> list[dict]:
    return [
        row for row in rows
        if str(row["ihub_box9_over_fill_cap"]).lower() != "true"
    ]


def objective(row: dict, mode: str) -> tuple[int, float]:
    return int(float(row[f"{mode}_cartons"])), float(row[f"{mode}_external_volume_mm3"])


def verdict(row: dict, mode: str) -> str:
    candidate, reference = objective(row, mode), objective(row, "ihub")
    return "Better" if candidate < reference else "Worse" if candidate > reference else "Same"


def reason(row: dict, mode: str) -> str | None:
    candidate, reference = objective(row, mode), objective(row, "ihub")
    if candidate[0] != reference[0]:
        return "carton"
    if candidate[1] != reference[1]:
        return "single" if candidate[0] == 1 else "multi"
    return None


def summarize(rows: list[dict]) -> dict:
    eligible = eligible_rows(rows)
    summary = {"total": len(rows), "eligible": len(eligible), "excluded": len(rows) - len(eligible)}
    for mode in ("fast", "best"):
        counts = Counter(verdict(row, mode) for row in eligible)
        parts = Counter((reason(row, mode), verdict(row, mode)) for row in eligible)
        summary[mode] = {label: counts[label] for label in ("Better", "Same", "Worse")}
        summary[f"{mode}_reasons"] = {
            key: {label: parts[(key, label)] for label in ("Better", "Worse")}
            for key in ("carton", "single", "multi")
        }
        assert sum(summary[mode].values()) == len(eligible)
        assert sum(sum(v.values()) for v in summary[f"{mode}_reasons"].values()) == (
            summary[mode]["Better"] + summary[mode]["Worse"]
        )
    return summary
