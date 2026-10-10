"""Stress benchmark current Fast vs Best across item counts and carton catalogue sizes.

This benchmark generates deterministic, nested synthetic orders. For a given seed,
all smaller item-count scenarios are exact prefixes of the largest order, and
Fast and Best see exactly the same packing problem. It is intended to reveal the point where
solver latency becomes impractical as item count, carton choice, or both grow.\n\nThe saved CSVs from before the greedy-only Fast change are historical.\nRegenerate all results after changing either strategy; do not mix versions.

Example:
    python notebooks/benchmark_solver_scaling.py --repeats 3
    # Optional explicit cap for exploratory runs:
    python notebooks/benchmark_solver_scaling.py --max-runtime-ms 5000
"""
from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bin_packing_3d import solve_order  # noqa: E402


DEFAULT_ITEM_COUNTS = (5, 10, 15, 20, 30, 50, 75, 100)
DEFAULT_BOX_COUNTS = (3, 5, 10, 15, 20)


def _parse_counts(raw: str) -> tuple[int, ...]:
    values = tuple(int(value.strip()) for value in raw.split(",") if value.strip())
    if not values or any(value <= 0 for value in values):
        raise argparse.ArgumentTypeError("counts must be positive comma-separated integers")
    return values


def generate_boxes(box_count: int) -> list[dict[str, Any]]:
    """Create a varied but ordered catalogue with the same largest carton."""
    boxes = []
    for index in range(box_count):
        fraction = index / max(1, box_count - 1)
        boxes.append(
            {
                "Code": f"StressBox{index + 1:02d}",
                "Length": round(140 + 260 * fraction),
                "Width": round(120 + 230 * fraction),
                "Height": round(100 + 200 * fraction),
                "MaxWeight": round(12 + 28 * fraction, 2),
            }
        )
    return boxes


def generate_order(item_count: int, seed: int) -> dict[str, Any]:
    """Create one reproducible order containing differently sized cuboids."""
    rng = random.Random(seed)
    items = []
    for index in range(item_count):
        # Keep every item individually feasible while retaining enough size
        # variation to make placement decisions non-trivial.
        # A single deterministic stream creates nested orders across item counts.
        # Cycle through size classes to diversify geometry without changing earlier items.
        size_classes = ((25, 45), (45, 75), (75, 105))
        low, high = size_classes[index % len(size_classes)]
        length = rng.randint(low, high)
        width = rng.randint(max(20, low - 5), min(90, high))
        height = rng.randint(max(15, low - 10), min(75, high))
        items.append(
            {
                "Code": f"Item{index + 1:03d}",
                "Length": length,
                "Width": width,
                "Height": height,
                "Weight": round(rng.uniform(0.15, 1.8), 3),
                "Quantity": 1,
                "VerticalRotation": rng.choice((0, 1)),
            }
        )
    return {
        "OrderId": f"stress-{item_count}-{seed}",
        "OrderNo": f"STRESS-{item_count}-{seed}",
        "Items": items,
    }


def run_grid(
    item_counts: tuple[int, ...],
    box_counts: tuple[int, ...],
    repeats: int,
    max_runtime_ms: float | None,
    seed: int,
    output_dir: Path | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item_count in item_counts:
        for box_count in box_counts:
            boxes = generate_boxes(box_count)
            for repeat in range(repeats):
                case_seed = seed + repeat
                order = generate_order(item_count, case_seed)
                for mode in ("fast", "best"):
                    result = solve_order(
                        order,
                        boxes,
                        mode=mode,
                        max_runtime_ms=max_runtime_ms,
                    )
                    rows.append(
                        {
                            "items": item_count,
                            "box_types": box_count,
                            "repeat": repeat + 1,
                            "seed": case_seed,
                            "mode": mode,
                            "runtime_ms": round(result.runtime_ms, 3),
                            "cartons_used": result.metrics.box_count,
                            "search_status": result.search_status,
                            "optimality_proven": result.optimality_proven,
                        }
                    )
                    if output_dir is not None:
                        # Persist every completed case: an uncapped exact search may
                        # outlive the CI runner, but earlier measurements remain usable.
                        write_csv(output_dir / "raw_results.csv", rows)
                    print(
                        f"{item_count:>3} items x {box_count:>2} boxes | "
                        f"{mode:>4} | {result.runtime_ms:>10.2f} ms | "
                        f"{result.search_status}"
                    )
    return rows


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["items"], row["box_types"], row["mode"])].append(row)

    summary = []
    for (items, box_types, mode), values in sorted(grouped.items()):
        runtimes = [float(value["runtime_ms"]) for value in values]
        summary.append(
            {
                "items": items,
                "box_types": box_types,
                "mode": mode,
                "median_runtime_ms": round(statistics.median(runtimes), 3),
                "max_runtime_ms": round(max(runtimes), 3),
                "median_cartons_used": statistics.median(
                    value["cartons_used"] for value in values
                ),
                "time_limit_rate": round(
                    sum(value["search_status"] == "time_limit" for value in values)
                    / len(values),
                    3,
                ),
                "optimality_proven_rate": round(
                    sum(bool(value["optimality_proven"]) for value in values)
                    / len(values),
                    3,
                ),
            }
        )
    return summary


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_results(summary: list[dict[str, Any]], output_dir: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    output_dir.mkdir(parents=True, exist_ok=True)

    # Box plots show the full three-run spread instead of only the median.
    # Both panels use the same vertical axis and matching item counts.
    comparison_box_count = max(row["box_types"] for row in summary)
    item_counts = sorted({row["items"] for row in summary})
    raw_path = output_dir / "raw_results.csv"
    if not raw_path.exists():
        raise FileNotFoundError(f"Box plots require individual benchmark runs: {raw_path}")
    with raw_path.open(newline="", encoding="utf-8") as source:
        raw_rows = list(csv.DictReader(source))
    figure, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    for axis, mode in zip(axes, ("fast", "best")):
        distributions = [
            [float(row["runtime_ms"]) / 1000 for row in raw_rows
             if int(row["items"]) == item and int(row["box_types"]) == comparison_box_count
             and row["mode"] == mode]
            for item in item_counts
        ]
        if any(not values for values in distributions):
            raise ValueError(f"Missing raw benchmark runs for {mode} with {comparison_box_count} box types")
        axis.boxplot(distributions, tick_labels=[str(item) for item in item_counts],
                     showmeans=True, meanprops={"marker": "D", "markerfacecolor": "white",
                                                 "markeredgecolor": "#334155", "markersize": 4})
        for index, values in enumerate(distributions, start=1):
            axis.scatter([index] * len(values), values, s=15, alpha=0.55, zorder=3)
        axis.set_xlabel("Items in one order")
        axis.set_title(f"{mode.title()} mode")
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
    axes[0].set_ylabel("Solver execution latency (seconds)")
    figure.suptitle(f"Solver latency distribution ({comparison_box_count} box types; individual runs shown)")
    figure.tight_layout()
    figure.savefig(output_dir / "solver_scaling_fast_vs_best.png", dpi=160)
    plt.close(figure)

    # Grouped box plots compare all available carton catalogue sizes.
    for mode in ("fast", "best"):
        figure, axis = plt.subplots(figsize=(13, 6))
        box_counts = sorted({row["box_types"] for row in summary if row["mode"] == mode})
        width = 0.75 / len(box_counts)
        for index, box_count in enumerate(box_counts):
            distributions = [
                [float(row["runtime_ms"]) for row in raw_rows
                 if int(row["items"]) == item and int(row["box_types"]) == box_count
                 and row["mode"] == mode]
                for item in item_counts
            ]
            if any(not values for values in distributions):
                raise ValueError(f"Missing raw benchmark runs for {mode}, {box_count} box types")
            positions = [i + 1 - 0.375 + (index + 0.5) * width for i in range(len(item_counts))]
            axis.boxplot(distributions, positions=positions, widths=width * 0.85,
                         manage_ticks=False, patch_artist=False)
        axis.set_yscale("log")
        axis.set_xticks(range(1, len(item_counts) + 1), labels=item_counts)
        axis.set_xlabel("Items in one order")
        axis.set_ylabel("Solver execution latency (ms, log scale)")
        axis.set_title(f"{mode.title()} latency distributions by box catalogue size")
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
        figure.tight_layout()
        figure.savefig(output_dir / f"solver_scaling_{mode}.png", dpi=160)
        plt.close(figure)

    # Estimated breakdown of Best: its Fast incumbent plus subsequent search.
    # Paired calls are measured independently, so the difference is approximate.
    paired = defaultdict(dict)
    for row in raw_rows:
        key = (int(row["items"]), int(row["box_types"]), int(row["repeat"]))
        paired[key][row["mode"]] = float(row["runtime_ms"]) / 1000
    fast_medians = []
    extra_medians = []
    for item in item_counts:
        samples = [modes for (count, boxes, _), modes in paired.items()
                   if count == item and boxes == comparison_box_count
                   and "fast" in modes and "best" in modes]
        if not samples:
            raise ValueError(f"No paired Fast/Best samples for {item} items")
        fast_medians.append(statistics.median(sample["fast"] for sample in samples))
        extra_medians.append(statistics.median(
            sample["best"] - sample["fast"] for sample in samples
        ))
    figure, axis = plt.subplots(figsize=(12, 6))
    x_positions = list(range(len(item_counts)))
    axis.bar(x_positions, fast_medians, color="#60A5FA", label="Fast baseline (separate call)")
    axis.bar(x_positions, extra_medians, bottom=fast_medians, color="#1D4ED8",
             label="Additional Best time (estimated)")
    axis.set_xticks(x_positions, labels=item_counts)
    axis.set_xlabel("Items in one order")
    axis.set_ylabel("Runtime (seconds)")
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
    for bars in axis.containers:
        axis.bar_label(bars, labels=[f"{bar.get_height():,.2f}" if bar.get_height() >= 0.01 else "" for bar in bars], padding=2, fontsize=8)
    axis.set_title(f"Estimated Best runtime breakdown ({comparison_box_count} box types)")
    axis.legend()
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    figure.text(0.5, 0.01,
                "Paired independent calls: difference is an estimate, not internal stage timing.",
                ha="center", fontsize=9)
    figure.tight_layout(rect=(0, 0.04, 1, 1))
    figure.savefig(output_dir / "solver_scaling_best_breakdown.png", dpi=160)
    figure.savefig(output_dir / "solver_scaling_best_breakdown.svg")
    plt.close(figure)

    # Heatmaps make the interaction between item count and catalogue size clear.
    for mode in ("fast", "best"):
        mode_rows = [row for row in summary if row["mode"] == mode]
        items = sorted({row["items"] for row in mode_rows})
        boxes = sorted({row["box_types"] for row in mode_rows})
        lookup = {
            (row["items"], row["box_types"]): row["median_runtime_ms"]
            for row in mode_rows
        }
        matrix = [[lookup[(item_count, box_count)] / 1000 for box_count in boxes] for item_count in items]

        figure, axis = plt.subplots(figsize=(9, 6))
        image = axis.imshow(matrix, aspect="auto", cmap="Blues", vmin=0)
        axis.set_xticks(range(len(boxes)), labels=boxes)
        axis.set_yticks(range(len(items)), labels=items)
        axis.set_xlabel("Available box types")
        axis.set_ylabel("Items in one order")
        axis.set_title(f"{mode.title()} latency: items x box choices")
        colorbar = figure.colorbar(image, ax=axis)
        colorbar.set_label("Median latency (seconds)")
        colorbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.1f}"))

        for row_index, item_count in enumerate(items):
            for column_index, box_count in enumerate(boxes):
                value = lookup[(item_count, box_count)] / 1000
                label = f"{value:,.3f}" if value < 1 else f"{value:,.2f}"
                intensity = image.norm(value)
                axis.text(column_index, row_index, label, ha="center", va="center",
                          color="white" if intensity > 0.55 else "#0F172A", fontsize=9)

        figure.tight_layout()
        figure.savefig(output_dir / f"solver_scaling_{mode}_heatmap.png", dpi=160)
        figure.savefig(output_dir / f"solver_scaling_{mode}_heatmap.svg")
        plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", type=_parse_counts, default=DEFAULT_ITEM_COUNTS)
    parser.add_argument("--boxes", type=_parse_counts, default=DEFAULT_BOX_COUNTS)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261008)
    parser.add_argument(
        "--max-runtime-ms",
        type=float,
        default=None,
        help="Optional search budget in milliseconds; omitted means no time limit (exact search can be extremely slow).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "benchmark_results" / "solver_scaling",
    )
    args = parser.parse_args()

    if args.repeats <= 0:
        parser.error("--repeats must be positive")
    if args.max_runtime_ms is not None and args.max_runtime_ms <= 0:
        parser.error("--max-runtime-ms must be positive")

    rows = run_grid(args.items, args.boxes, args.repeats, args.max_runtime_ms, args.seed, args.output_dir)
    summary = summarize(rows)
    write_csv(args.output_dir / "raw_results.csv", rows)
    write_csv(args.output_dir / "summary.csv", summary)
    plot_results(summary, args.output_dir)

    print(f"\nResults written to {args.output_dir}")
    print("Use summary.csv to identify the latency cliff and timeout region.")


if __name__ == "__main__":
    main()
