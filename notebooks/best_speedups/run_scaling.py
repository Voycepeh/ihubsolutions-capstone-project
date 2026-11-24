"""Run the README scaling benchmark with Best before or after the speed-ups.

Uses ``notebooks/benchmark_solver_scaling.py`` unchanged (same grid, seeds,
uncapped search and charts as the README). Best mode is swapped for this
folder's ``best_speedup_solver.BestFitSolver``: ``before`` with every speed-up
switched off, ``after`` with all of them on.

    python notebooks/best_speedups/run_scaling.py before
    python notebooks/best_speedups/run_scaling.py after
"""
from __future__ import annotations

import sys
from functools import partial
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "notebooks"))
sys.path.insert(0, str(HERE))

import bin_packing_3d.strategies as strategies  # noqa: E402
import benchmark_solver_scaling  # noqa: E402
from best_speedup_solver import BestFitSolver as SpeedupBestFitSolver  # noqa: E402

OPTIONS = ("reuse_incumbent", "hint_incumbent", "carton_symmetry", "item_symmetry", "pair_pruning")

if __name__ == "__main__":
    variant = sys.argv[1] if len(sys.argv) > 1 else ""
    if variant not in ("before", "after"):
        sys.exit("usage: run_scaling.py before|after")
    # The engine re-registers built-ins on each Best call, so patch the class it uses.
    if variant == "before":
        strategies.BestFitSolver = partial(SpeedupBestFitSolver, **{option: False for option in OPTIONS})
    else:
        strategies.BestFitSolver = SpeedupBestFitSolver
    sys.argv = [sys.argv[0], "--output-dir", str(HERE / f"scaling_{variant}"), *sys.argv[2:]]
    benchmark_solver_scaling.main()
