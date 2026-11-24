"""Per-step measurement of Best's search speed-ups.

Each stage switches on one more speed-up (cumulative), using the toggles on
``BestFitSolver``. Every stage solves the same order back to back, so machine
load affects all stages equally. Correctness is checked against stage S0:
a stage must prove the same carton objective on every order where both
finished their search.

    python notebooks/best_speedups/benchmark_best_speedups.py dataset
    python notebooks/best_speedups/benchmark_best_speedups.py large

Results are written next to this script.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "notebooks"))
sys.path.insert(0, str(HERE))

from bin_packing_3d import register_solver, solve_order  # noqa: E402
from best_speedup_solver import BestFitSolver  # noqa: E402  (this folder's sped-up Best)
from benchmark_solver_modes import _inputs  # noqa: E402
from benchmark_solver_scaling import generate_boxes, generate_order  # noqa: E402

OPTIONS = ("hint_incumbent", "reuse_incumbent", "carton_symmetry", "item_symmetry", "pair_pruning")
STAGES = [
    ("S0", "Current Best (no speed-ups)"),
    ("S1", "+ #5 Start from Fast's layout"),
    ("S2", "+ #1 Don't redo Fast's work"),
    ("S3", "+ #3 Identical cartons"),
    ("S4", "+ #2 Identical items"),
    ("S5", "+ #4 Impossible pairs (all on)"),
]


def register_stages() -> None:
    for position, (stage, _) in enumerate(STAGES):
        enabled = set(OPTIONS[:position])
        register_solver(stage, BestFitSolver(**{option: option in enabled for option in OPTIONS}), replace=True)


def _solve(stage, order, boxes, arguments):
    result = solve_order(order, boxes, strategy=stage, **arguments)
    return {
        "boxes": ",".join(sorted(box.box_code for box in result.packed_boxes)),
        "cartons": result.metrics.box_count,
        "volume": result.metrics.total_external_box_volume,
        "runtime_ms": round(result.runtime_ms, 3),
        "proven": result.optimality_proven,
        "source": result.best_result_source,
    }


def run(cases, arguments_for):
    register_stages()
    rows = []
    for index, (label, order, boxes) in enumerate(cases, start=1):
        arguments = arguments_for(label)
        row = {"case": label}
        for stage, _ in STAGES:
            for key, value in _solve(stage, order, boxes, arguments).items():
                row[f"{stage}_{key}"] = value
        rows.append(row)
        if index % 100 == 0 or len(cases) < 100:
            print(f"... {index}/{len(cases)} {label}", flush=True)
    return rows


def dataset_cases(path: Path):
    cases, configs = [], {}
    for record in json.loads(path.read_text(encoding="utf-8")):
        order, boxes, config = _inputs(record)
        label = str(order["OrderId"])
        configs[label] = {
            "high_item_count_threshold": config["high_item_count_threshold"],
            "high_item_count_max_fill_pct": config["high_item_count_max_fill_pct"],
            "max_fill_pct": config["max_fill_pct"],
            "bin_buffer": config["bin_buffer"],
            "max_runtime_ms": 5000,
        }
        cases.append((label, order, boxes))
    return cases, lambda label: configs[label]


def large_cases(item_counts, seeds, box_types, cap_ms):
    boxes = generate_boxes(box_types)
    cases = []
    for count in item_counts:
        for seed in seeds:
            cases.append((f"distinct-{count}-{seed}", generate_order(count, seed), boxes))
            # Same generator, but count/5 product lines with Quantity 5 each.
            repeated = generate_order(count // 5, seed)
            for item in repeated["Items"]:
                item["Quantity"] = 5
            cases.append((f"repeated-{count}-{seed}", repeated, boxes))
    return cases, lambda label: {"max_runtime_ms": cap_ms}


def _p(values, q):
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, round(q * len(ordered)) - 1))]


def summarize(rows, title):
    lines = [f"# {title}", "", f"Cases: {len(rows)}", ""]
    lines.append("| Stage | Change | Median ms | Mean ms | P95 ms | Max ms | Total s | Not proven (time limit) | Objective differs from S0 |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    summary = []
    base_median = None
    for stage, description in STAGES:
        runtimes = [row[f"{stage}_runtime_ms"] for row in rows]
        unproven = sum(not row[f"{stage}_proven"] for row in rows)
        differs = sum(
            (row[f"{stage}_cartons"], row[f"{stage}_volume"]) != (row["S0_cartons"], row["S0_volume"])
            and row[f"{stage}_proven"] and row["S0_proven"]
            for row in rows
        )
        record = {
            "stage": stage, "change": description,
            "median_ms": round(statistics.median(runtimes), 2),
            "mean_ms": round(statistics.mean(runtimes), 2),
            "p95_ms": round(_p(runtimes, 0.95), 2),
            "max_ms": round(max(runtimes), 2),
            "total_s": round(sum(runtimes) / 1000, 2),
            "not_proven": unproven,
            "objective_differs_from_s0": differs,
        }
        summary.append(record)
        lines.append(
            f"| {stage} | {description} | {record['median_ms']} | {record['mean_ms']} | {record['p95_ms']} | "
            f"{record['max_ms']} | {record['total_s']} | {unproven} | {differs} |"
        )
    return summary, lines


def group_lines(rows):
    """Median runtime per synthetic order size and kind for the large suite."""
    groups: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        kind, count, _ = row["case"].split("-")
        groups.setdefault((kind, int(count)), []).append(row)
    header = "| Order | " + " | ".join(stage for stage, _ in STAGES) + " | S0 → S5 |"
    lines = ["", "Median runtime (ms) by order size", "", header, "|---|" + "---:|" * (len(STAGES) + 1)]
    for (kind, count), members in sorted(groups.items()):
        medians = [statistics.median(m[f"{stage}_runtime_ms"] for m in members) for stage, _ in STAGES]
        speedup = medians[0] / medians[-1] if medians[-1] else float("inf")
        lines.append(f"| {count} items, {kind} | " + " | ".join(f"{m:,.1f}" for m in medians) + f" | {speedup:,.1f}× |")
    return lines


def write(rows, summary, lines, prefix):
    with (HERE / f"{prefix}_per_case.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (HERE / f"{prefix}_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    (HERE / f"{prefix}_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", choices=("dataset", "large"))
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "raw" / "data_samples_v2.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--items", default="30,50,75,100")
    parser.add_argument("--seeds", default="20261008,20261009,20261010")
    parser.add_argument("--box-types", type=int, default=5)
    parser.add_argument("--cap-ms", type=float, default=60000)
    args = parser.parse_args()

    if args.suite == "dataset":
        cases, arguments_for = dataset_cases(args.dataset)
        cases = cases[:args.limit] if args.limit else cases
        rows = run(cases, arguments_for)
        summary, lines = summarize(rows, "Best speed-ups: 2,000 iHub orders (5 s Best budget)")
    else:
        items = [int(v) for v in args.items.split(",")]
        seeds = [int(v) for v in args.seeds.split(",")]
        cases, arguments_for = large_cases(items, seeds, args.box_types, args.cap_ms)
        cases = cases[:args.limit] if args.limit else cases
        rows = run(cases, arguments_for)
        summary, lines = summarize(rows, f"Best speed-ups: large synthetic orders ({args.box_types} carton types, {args.cap_ms / 1000:g} s cap)")
        lines += group_lines(rows)
    write(rows, summary, lines, args.suite + ("_sample" if args.limit else ""))


if __name__ == "__main__":
    main()
