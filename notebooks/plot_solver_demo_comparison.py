"""Generate a README-ready, data-grounded Fast / Best / iHub comparison chart."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()

    with args.csv_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError("Benchmark CSV is empty")

    eligible = [r for r in rows if r["ihub_box9_over_fill_cap"].lower() != "true"]
    if not eligible:
        raise ValueError("No policy-compliant reference orders")

    fields = ("cartons", "external_volume_mm3")
    def objective(row: dict[str, str], mode: str) -> tuple[float, ...]:
        return tuple(float(row[f"{mode}_{field}"]) for field in fields)

    categories = ("Better", "Same", "Worse")
    counts = {}
    for mode in ("fast", "best"):
        results = []
        for row in eligible:
            current, reference = objective(row, mode), objective(row, "ihub")
            results.append("Better" if current < reference else "Same" if current == reference else "Worse")
        counts[mode] = [results.count(label) for label in categories]

    fig, ax = plt.subplots(figsize=(10, 4.3))
    positions = np.arange(2)
    left = np.zeros(2)
    colors = ("#087f8c", "#aab8c2", "#d97745")
    for index, label in enumerate(categories):
        values = np.array([counts[mode][index] for mode in ("fast", "best")])
        bars = ax.barh(positions, values, left=left, color=colors[index], label=label, height=0.55)
        for bar, value in zip(bars, values):
            if value:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                        str(value), ha="center", va="center", fontsize=10, fontweight="bold",
                        color="white" if index != 1 else "#1d2935")
        left += values

    ax.set_yticks(positions, ["Fast", "Best"])
    ax.invert_yaxis()
    ax.set_xlim(0, len(eligible) * 1.04)
    ax.set_xlabel("Number of orders")
    ax.set_title("Packing objective vs iHub reference", loc="left", fontsize=15, fontweight="bold", pad=18)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.38), ncol=3, frameon=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", alpha=0.15)
    ax.set_axisbelow(True)
    fig.text(0.125, 0.01,
             f"{len(eligible):,} policy-compliant reference orders; {len(rows)-len(eligible):,} flagged iHub fill-cap exceptions excluded. "
             "Rank: fewer cartons, then lower total external carton volume.",
             fontsize=8, color="#536273")
    fig.subplots_adjust(bottom=0.31, top=0.81)
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"Generated {args.output_path} from {len(rows)} benchmark rows")


if __name__ == "__main__":
    main()
