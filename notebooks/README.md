# Notebooks and experiments

This directory contains exploratory analysis, demonstrations, historical packing prototypes, and benchmarks for the iHub 3D carton-packing capstone. **The maintained solver lives in [`src/`](../src/)** and is called through `bin_packing_3d.solve_order()`. See the [project README](../README.md) for the current API, configuration, input format, and packing constraints.

## Where to start

| File | Purpose |
| --- | --- |
| [Initial EDA v2](Inital%20EDA%20v2.ipynb) | Explore the newer sample dataset and interpret order and carton characteristics. |
| [Initial EDA v1](Inital%20EDA.ipynb) | Earlier exploratory analysis for the original sample. |
| [Solver Demo](Solver%20Demo.ipynb) | Interactive demonstration of carton packing. |
| [Simulated Rule Proof](Simulated%20Rule%20Proof.ipynb) | Explore and test simulated packing rules. |
| [Capstone notebook](capstone.ipynb) | Earlier capstone exploration. |

## Benchmarks and diagnostics

| File | Purpose |
| --- | --- |
| [`benchmark_solver_modes.py`](benchmark_solver_modes.py) | Compare the maintained solver's Fast and Best modes with the masked iHub reference results, including carton usage and latency. |
| [`benchmark_solver_scaling.py`](benchmark_solver_scaling.py) | Stress test Fast and Best with synthetic orders across different item counts and carton catalogue sizes. |
| [`diagnose_50_vs_75.py`](diagnose_50_vs_75.py) | Profile the 50-item versus 75-item latency anomaly from the scaling benchmark. |

Run the benchmarks from the repository root after installing the project's dependencies. For example:

```bash
python notebooks/benchmark_solver_modes.py --help
python notebooks/benchmark_solver_scaling.py --help
```

## Historical experiments and supporting files

| File or folder | Purpose |
| --- | --- |
| [`packer_first_fit.py`](packer_first_fit.py) | Standalone, earlier extreme-point/first-fit packing implementation and dataset runner. **Not the maintained public API.** |
| [`retry_pack.py`](retry_pack.py) | Experimental item-placement routine, not a standalone entry point. |
| [`Volumetric + 3D engine/`](Volumetric%20%2B%203D%20engine/) | Earlier volumetric and 3D packing experiments. |
| [`Volumetric +3D engine.zip`](Volumetric%20%2B3D%20engine.zip) | Archived experiment bundle. |
| [`results_first_fit.csv`](results_first_fit.csv) | Output from the historical first-fit experiment; not a current benchmark result. |

## Current implementation versus experiments

Use [the root README](../README.md) and [`src/`](../src/) when integrating or evaluating the current solver. The notebooks and older scripts are research and demonstration materials; their assumptions, defaults, and results may differ from the maintained implementation. Keep comparisons between Fast and Best modes on the same orders and carton catalogue, and report both carton counts and runtime.
