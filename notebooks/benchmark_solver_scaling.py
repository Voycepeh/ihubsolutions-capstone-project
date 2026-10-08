"""Stress benchmark Fast vs Best across item counts and carton catalogue sizes.

This benchmark generates deterministic synthetic orders so the two solver modes
see exactly the same packing problem. It is intended to reveal the point where
solver latency becomes impractical as item count, carton choice, or both grow.

Example:
    python notebooks/benchmark_solver_scaling.py --repeats 3 --max-runtime-ms 5000
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
        length = rng.randint(25, 105)
        width = rng.randint(20, 90)
        height = rng.randint(15, 75)
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
    max_runtime_ms: float,
    seed: int,
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

    output_dir.mkdir(parents=True, exist_ok=True)

    # Direct Fast vs Best comparison using the full generated carton catalogue.
    comparison_box_count = max(row["box_types"] for row in summary)
    figure, axis = plt.subplots(figsize=(10, 6))
    for mode in ("fast", "best"):
        selected = sorted(
            (
                row
                for row in summary
                if row["mode"] == mode and row["box_types"] == comparison_box_count
            ),
            key=lambda row: row["items"],
        )
        axis.plot(
            [row["items"] for row in selected],
            [row["median_runtime_ms"] / 1000 for row in selected],
            marker="o",
            linewidth=2,
            label=mode.title(),
        )
    axis.set_xlabel("Items in one order")
    axis.set_ylabel("Median end-to-end latency (seconds)")
    axis.set_title(
        f"Fast vs Best solver latency ({comparison_box_count} available box types)"
    )
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_dir / "solver_scaling_fast_vs_best.png", dpi=160)
    plt.close(figure)

    # Curves: one line per catalogue size, Fast and Best in separate figures.
    for mode in ("fast", "best"):
        figure, axis = plt.subplots(figsize=(10, 6))
        mode_rows = [row for row in summary if row["mode"] == mode]
        for box_count in sorted({row["box_types"] for row in mode_rows}):
            selected = sorted(
                (row for row in mode_rows if row["box_types"] == box_count),
                key=lambda row: row["items"],
            )
            axis.plot(
                [row["items"] for row in selected],
                [row["median_runtime_ms"] for row in selected],
                marker="o",
                label=f"{box_count} box types",
            )
        axis.set_yscale("log")
        axis.set_xlabel("Items in one order")
        axis.set_ylabel("Median latency (ms, log scale)")
        axis.set_title(f"{mode.title()} solver scaling")
        axis.grid(True, alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(output_dir / f"solver_scaling_{mode}.png", dpi=160)
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
        matrix = [[lookup[(item_count, box_count)] for box_count in boxes] for item_count in items]

        figure, axis = plt.subplots(figsize=(9, 6))
        image = axis.imshow(matrix, aspect="auto")
        axis.set_xticks(range(len(boxes)), labels=boxes)
        axis.set_yticks(range(len(items)), labels=items)
        axis.set_xlabel("Available box types")
        axis.set_ylabel("Items in one order")
        axis.set_title(f"{mode.title()} latency: items x box choices")
        colorbar = figure.colorbar(image, ax=axis)
        colorbar.set_label("Median latency (ms)")

        for row_index, item_count in enumerate(items):
            for column_index, box_count in enumerate(boxes):
                value = lookup[(item_count, box_count)]
                axis.text(column_index, row_index, f"{value:,.0f}", ha="center", va="center")

        figure.tight_layout()
        figure.savefig(output_dir / f"solver_scaling_{mode}_heatmap.png", dpi=160)
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
        default=5000,
        help="Per-solver search budget. Best may return its Fast fallback when this is reached.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "benchmark_results" / "solver_scaling",
    )
    args = parser.parse_args()

    if args.repeats <= 0:
        parser.error("--repeats must be positive")
    if args.max_runtime_ms <= 0:
        parser.error("--max-runtime-ms must be positive")

    rows = run_grid(args.items, args.boxes, args.repeats, args.max_runtime_ms, args.seed)
    summary = summarize(rows)
    write_csv(args.output_dir / "raw_results.csv", rows)
    write_csv(args.output_dir / "summary.csv", summary)
    plot_results(summary, args.output_dir)

    print(f"\nResults written to {args.output_dir}")
    print("Use summary.csv to identify the latency cliff and timeout region.")


if __name__ == "__main__":
    main()
