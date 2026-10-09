"""Reproduce Fast carton-count outliers without changing the solver.

Run:
    python notebooks/inspect_fast_carton_outliers.py
    python notebooks/inspect_fast_carton_outliers.py --items 50 75 100 --seed 20261008 --trace

The scaling benchmark uses seed + repeat (repeat starts at zero), so use
--seed 20261008, 20261009 or 20261010 to inspect individual repetitions.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark_solver_scaling import generate_boxes, generate_order  # noqa: E402
from bin_packing_3d import solve_order  # noqa: E402


def inspect(item_count: int, box_count: int, seed: int, trace: bool) -> None:
    order = generate_order(item_count, seed)
    boxes = generate_boxes(box_count)
    total_volume = sum(
        item["Length"] * item["Width"] * item["Height"] * item["Quantity"]
        for item in order["Items"]
    )
    total_weight = sum(item["Weight"] * item["Quantity"] for item in order["Items"])
    largest = max(boxes, key=lambda box: box["Length"] * box["Width"] * box["Height"])
    usable_largest_volume = largest["Length"] * largest["Width"] * (largest["Height"] - 6)
    volume_lower_bound = -(-total_volume // (usable_largest_volume * 0.70))
    weight_lower_bound = -(-total_weight // largest["MaxWeight"])

    print(f"\n{item_count} items | {box_count} carton types | seed={seed}")
    print(
        f"Order volume={total_volume:,.0f} mm^3 | weight={total_weight:.3f} kg | "
        f"optimistic lower bound={max(1, int(volume_lower_bound), int(weight_lower_bound))} cartons"
    )
    result = solve_order(order, boxes, mode="fast", max_runtime_ms=None, logs=trace)
    counts = Counter(box.box_code for box in result.packed_boxes)
    print(
        f"Fast cartons={result.metrics.box_count} | runtime={result.runtime_ms:.2f} ms | "
        f"validated={result.validation.valid} | types={dict(sorted(counts.items()))}"
    )
    print("Carton sequence (code:items:fill%):")
    print(
        "  " + ", ".join(
            f"{box.box_code}:{len(box.placements)}:{metric.utilization_pct:.1f}"
            for box, metric in zip(result.packed_boxes, result.metrics.boxes)
        )
    )
    print(
        "Interpretation: low-fill small cartons suggest the greedy new-carton choice "
        "is preventing consolidation. The lower bound checks volume and weight only; "
        "it does not prove geometric packability."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", nargs="+", type=int, default=[50, 75, 100])
    parser.add_argument("--box-count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261008)
    parser.add_argument("--trace", action="store_true", help="Print full item-level solver decisions")
    args = parser.parse_args()
    for item_count in args.items:
        inspect(item_count, args.box_count, args.seed, args.trace)


if __name__ == "__main__":
    main()
