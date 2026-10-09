"""Benchmark Fast and Best modes against the masked iHub reference service.

The source dataset and solver both use millimetres for item, carton, buffer,
and coordinate dimensions, so no unit conversion is performed. Solver runtime
and the reference service's recorded ``latency_ms`` are warm latency
measurements.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bin_packing_3d import solve_order  # noqa: E402


def _inputs(record: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    raw = record["input"]
    items = [dict(item) for item in raw["Items"]["ItemsList"]]
    boxes = [dict(box) for box in raw["Bins"]["BinsList"]]
    parameters = raw["Bins"]["Parameters"]
    buffer = parameters["BinBuffer"]
    order = {"OrderId": raw.get("OrderId"), "OrderNo": raw.get("OrderNo"), "Items": items}
    config = {
        "high_item_count_threshold": parameters["BinMaxFillCheckMinItemQty"],
        "high_item_count_max_fill_pct": parameters["BinMaxFillPct"],
        "max_fill_pct": 100,
        "bin_buffer": {
            "length": buffer["Length"],
            "width": buffer["Width"],
            "height": buffer["Height"],
        },
    }
    return order, boxes, config


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def benchmark(records: list[dict[str, Any]], best_timeout_ms: float = 5000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        order, boxes, config = _inputs(record)
        box_by_code = {box["Code"]: box for box in boxes}
        reference = record["output"]["Data"]["BinsPacked"]
        reference_codes = [box["Code"] for box in reference]
        reference_volume = sum(
            box_by_code[code]["Length"]
            * box_by_code[code]["Width"]
            * box_by_code[code]["Height"]
            for code in reference_codes
        )
        solver_arguments = {
            "high_item_count_threshold": config["high_item_count_threshold"],
            "high_item_count_max_fill_pct": config["high_item_count_max_fill_pct"],
            "max_fill_pct": config["max_fill_pct"],
            "bin_buffer": config["bin_buffer"],
        }
        fast = solve_order(order, boxes, mode="fast", **solver_arguments)
        best = solve_order(order, boxes, mode="best", max_runtime_ms=best_timeout_ms, **solver_arguments)
        rows.append({
            "order_id": order["OrderId"],
            "physical_items": sum(item["Quantity"] for item in order["Items"]),
            "ihub_boxes": ",".join(reference_codes),
            "ihub_cartons": len(reference_codes),
            "ihub_external_volume_mm3": reference_volume,
            "ihub_largest_carton_volume_mm3": max(
                box_by_code[code]["Length"]
                * box_by_code[code]["Width"]
                * box_by_code[code]["Height"]
                for code in reference_codes
            ),
            "ihub_latency_ms": record["latency_ms"],
            "ihub_box9_over_fill_cap": any(
                box["Code"] == "Box9" and box["UsedSpace"] > config["high_item_count_max_fill_pct"]
                for box in reference
            ),
            "fast_boxes": ",".join(box.box_code for box in fast.packed_boxes),
            "fast_cartons": fast.metrics.box_count,
            "fast_external_volume_mm3": fast.metrics.total_external_box_volume,
            "fast_largest_carton_volume_mm3": max(
                box_by_code[box.box_code]["Length"]
                * box_by_code[box.box_code]["Width"]
                * box_by_code[box.box_code]["Height"]
                for box in fast.packed_boxes
            ),
            "fast_runtime_ms": fast.runtime_ms,
            "fast_optimality_proven": fast.optimality_proven,
            "fast_search_status": fast.search_status,
            "best_boxes": ",".join(box.box_code for box in best.packed_boxes),
            "best_cartons": best.metrics.box_count,
            "best_external_volume_mm3": best.metrics.total_external_box_volume,
            "best_largest_carton_volume_mm3": max(
                box_by_code[box.box_code]["Length"]
                * box_by_code[box.box_code]["Width"]
                * box_by_code[box.box_code]["Height"]
                for box in best.packed_boxes
            ),
            "best_runtime_ms": best.runtime_ms,
            "best_optimality_proven": best.optimality_proven,
            "best_search_status": best.search_status,
            "best_result_source": best.best_result_source,
        })
    return rows


def print_summary(rows: list[dict[str, Any]]) -> None:
    print(f"Orders benchmarked: {len(rows):,}")
    for mode in ("fast", "best"):
        runtimes = [row[f"{mode}_runtime_ms"] for row in rows]
        fewer = sum(row[f"{mode}_cartons"] < row["ihub_cartons"] for row in rows)
        same = sum(row[f"{mode}_cartons"] == row["ihub_cartons"] for row in rows)
        more = len(rows) - fewer - same
        print(
            f"{mode.title():4} solver runtime median/P95: "
            f"{statistics.median(runtimes):.3f}/{_p95(runtimes):.3f} ms; "
            f"cartons vs iHub fewer/same/more: {fewer}/{same}/{more}"
        )
    ihub_times = [row["ihub_latency_ms"] for row in rows]
    print(
        "iHub recorded warm latency median/P95: "
        f"{statistics.median(ihub_times):.3f}/{_p95(ihub_times):.3f} ms"
    )
    better = sum(
        (row["best_cartons"], row["best_external_volume_mm3"])
        < (row["fast_cartons"], row["fast_external_volume_mm3"])
        for row in rows
    )
    worse = sum(
        (row["best_cartons"], row["best_external_volume_mm3"])
        > (row["fast_cartons"], row["fast_external_volume_mm3"])
        for row in rows
    )
    print(f"Best objective vs Fast: improved {better}, tied {len(rows) - better - worse}, worse {worse}")
    print(
        "Best optimality proven / time-bounded fallback: "
        f"{sum(row['best_optimality_proven'] for row in rows)}/"
        f"{sum(not row['best_optimality_proven'] for row in rows)}"
    )
    print(
        "iHub Box9 usage / Box9 above supplied fill cap: "
        f"{sum('Box9' in row['ihub_boxes'].split(',') for row in rows)}/"
        f"{sum(row['ihub_box9_over_fill_cap'] for row in rows)}"
    )
    best_more = [row for row in rows if row["best_cartons"] > row["ihub_cartons"]]
    cap_failures = sum(row["ihub_box9_over_fill_cap"] for row in best_more)
    print(
        "Best uses more cartons with iHub reported fill pass / Box9 cap failure: "
        f"{len(best_more) - cap_failures}/{cap_failures}"
    )
    eligible = [row for row in rows if not row["ihub_box9_over_fill_cap"]]
    comparisons = []
    for row in eligible:
        best_objective = (
            row["best_cartons"],
            row["best_external_volume_mm3"],
        )
        ihub_objective = (
            row["ihub_cartons"],
            row["ihub_external_volume_mm3"],
        )
        comparisons.append((best_objective > ihub_objective) - (best_objective < ihub_objective))
    print(
        "Best full objective vs fill-cap-pass iHub better/equal/worse: "
        f"{comparisons.count(-1)}/{comparisons.count(0)}/{comparisons.count(1)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "dataset",
        nargs="?",
        type=Path,
        default=ROOT / "data" / "raw" / "data_samples_v2.json",
    )
    parser.add_argument("--limit", type=int, help="Benchmark only the first N records")
    parser.add_argument("--start", type=int, default=0, help="Starting record offset for parallel batches")
    parser.add_argument("--best-timeout-ms", type=float, default=5000, help="Best solver search budget in milliseconds")
    parser.add_argument("--csv", type=Path, help="Optionally write per-order results")
    args = parser.parse_args()

    records = json.loads(args.dataset.read_text(encoding="utf-8"))
    if args.limit is not None:
        records = records[args.start:args.start + args.limit]
    rows = benchmark(records, best_timeout_ms=args.best_timeout_ms)
    print_summary(rows)
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"Per-order results written to {args.csv}")


if __name__ == "__main__":
    main()
