# 3D Bin Packing Solver

NUS Industry 4.0 Master's capstone project building a reusable Python 3D bin packing and cartonization library, benchmarked against masked iHub order data.

The package is `bin_packing_3d`. iHub is the business use case and benchmark dataset, not the package identity.

## What it does

The solver accepts:

1. **Order data**: item dimensions, weight, quantity and rotation rule.
2. **Carton catalogue**: available carton dimensions and maximum weight.
3. **Configuration**: operational packing rules such as buffer, fill limit and placement strategy.

It returns selected cartons, item placements, unpacked items and runtime.

## Public interface

```python
from bin_packing_3d import solve_order

result = solve_order(
    order=order,
    boxes=boxes,
    config=config,
)
```

`solve_order()` is the only public solver function normal users need.

## Product direction

The solver is a lightweight deterministic heuristic rather than an exact optimizer.

The implementation sequence is deliberately simple:

1. **MVP 1: First Fit** — complete end to end solver including single carton, multiple carton fallback, iHub packing rules, 3D coordinates, validation and runtime.
2. **MVP 2: Best Fit** — use the same geometry and candidates, but compare all valid positions before selecting one. Benchmark the quality versus latency tradeoff against First Fit.
3. **MVP 3: Bounded improvement** — only if benchmark evidence justifies it, try a small number of alternative item orders or carton consolidation attempts within the runtime budget.

The complete functional contract is in [`src/PRODUCT_SPEC.md`](src/PRODUCT_SPEC.md). That is the single source of truth for implementation behavior.

## Simplified package structure

```text
ihubsolutions-capstone-project/
├── src/
│   ├── PRODUCT_SPEC.md
│   └── bin_packing_3d/
│       ├── __init__.py
│       ├── models.py
│       ├── rules.py
│       ├── packing.py
│       └── validate.py
├── tests/
│   ├── test_rules.py
│   ├── test_packing.py
│   ├── test_validate.py
│   ├── test_solver.py
│   └── fixtures/
├── notebooks/
├── data/raw/
├── docs/
└── README.md
```

The package intentionally avoids one file per helper concept. Geometry, remaining empty spaces, First Fit, Best Fit and single or multiple carton search all belong to the same packing engine until there is a clear reason to split them.

## Key packing rules

The solver must support:

- configurable carton catalogue,
- quantity expansion into physical items,
- upright only items through `VerticalRotation`,
- maximum carton weight,
- configurable carton buffer,
- configurable fill threshold and fill percentage,
- 3D boundary and overlap checks,
- single and multiple carton packing,
- unpackable item reporting,
- deterministic First Fit and Best Fit strategies,
- independent final validation.

## Documentation

Keep supporting documentation small:

| Document | Purpose |
| --- | --- |
| [`src/PRODUCT_SPEC.md`](src/PRODUCT_SPEC.md) | Functional source of truth and MVP logic |
| [`docs/solver-approach-and-literature.md`](docs/solver-approach-and-literature.md) | Algorithm rationale and literature |
| [`docs/dataset-specification.md`](docs/dataset-specification.md) | Supplied benchmark data and fields |

Exploratory findings belong in `notebooks/`. Product behavior belongs in the product spec rather than being duplicated across several architecture, roadmap and interface documents.

## Development principle

Build the smallest complete valid solver first, test it end to end, then add packing intelligence only when benchmark evidence shows the extra complexity is worthwhile.

The historical iHub outputs are a benchmark rather than mathematical ground truth. A different arrangement is acceptable when it is valid, respects the agreed constraints and improves the stated objective.
