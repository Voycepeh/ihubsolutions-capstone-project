"""Targeted diagnostic rerun for the 50 vs 75 item latency reversal.

Runs only 50 and 75 items, 20 carton types, three original seeds, Fast mode.
Uses cProfile to identify where the runtime is spent; profiling changes timings,
so compare function-call counts and cumulative time, not absolute wall time.
"""
from __future__ import annotations

import cProfile
import csv
import importlib.util
import pstats
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("scaling", ROOT / "notebooks" / "benchmark_solver_scaling.py")
benchmark = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(benchmark)

OUT = ROOT / "benchmark_results" / "diagnostics_50_vs_75"
OUT.mkdir(parents=True, exist_ok=True)
rows = []
boxes = benchmark.generate_boxes(20)
for count in (50, 75):
    for repeat in range(3):
        seed = 20261008 + repeat
        order = benchmark.generate_order(count, seed)
        profile = cProfile.Profile()
        start = perf_counter()
        profile.enable()
        result = benchmark.solve_order(order, boxes, mode="fast", max_runtime_ms=None)
        profile.disable()
        elapsed = perf_counter() - start
        stats = pstats.Stats(profile)
        interesting = ("_build_candidate", "_search_fewer_cartons", "feasible_placements",
                       "placement_envelope_volume", "combinations_with_replacement",
                       "item_fits_box", "usable_dimensions")
        counters = {}
        for (filename, line, func), (primitive_calls, total_calls, self_time, cum_time, callers) in stats.stats.items():
            if func in interesting:
                prefix = func
                counters[f"{prefix}_calls"] = counters.get(f"{prefix}_calls", 0) + total_calls
                counters[f"{prefix}_cumulative_seconds"] = round(
                    counters.get(f"{prefix}_cumulative_seconds", 0) + cum_time, 3)
        row = {"items": count, "seed": seed, "runtime_profiled_seconds": round(elapsed, 3),
               "cartons_used": result.metrics.box_count, "search_status": result.search_status,
               **counters}
        rows.append(row)
        print("DIAGNOSTIC", row, flush=True)
        with (OUT / f"profile_{count}_{seed}.txt").open("w") as output:
            stats.stream = output
            stats.sort_stats("cumulative").print_stats(35)

columns = list(dict.fromkeys(key for row in rows for key in row))
with (OUT / "diagnostics.csv").open("w", newline="") as output:
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
print("Saved", len(rows), "diagnostic runs", flush=True)
