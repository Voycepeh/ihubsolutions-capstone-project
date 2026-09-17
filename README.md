# 3D Bin Packing Solver

NUS Industry 4.0 Master's capstone project building a reusable Python 3D bin packing and cartonization library, benchmarked against masked iHub order data.

The package is `bin_packing_3d`. iHub is the business use case and benchmark dataset, not the package identity.

## What it does

The solver accepts:

1. **Order data**: item dimensions, weight, quantity and rotation rule.
2. **Carton catalogue**: available carton dimensions and maximum weight.
3. **Configuration**: operational packing rules such as buffer, fill limit and placement strategy.

It returns selected cartons, item placements, unpacked items and runtime.

The objective is simple: return a valid packing plan using the **fewest cartons**, then prefer the **smallest total carton volume** when carton count is equal.

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

## MVP roadmap

The MVP sequence follows the actual business problem:

1. **MVP 0: Fit one item** — generate allowed orientations and choose the smallest valid carton.
2. **MVP 1: Pack many items into one carton** — add sequencing, orientation, XYZ placement, overlap checks and remaining-space tracking.
3. **MVP 2: Pack the full order** — use the whole carton catalogue and return the fewest valid cartons, preferring smaller cartons when carton count is equal.
4. **MVP 3: Improve the result** — compare First Fit and Best Fit, retry selected item sequences, and attempt carton consolidation within a runtime limit.

The core packing loop is:

**sequence items → choose allowed orientation → choose XYZ position → validate placement → continue or retry**

This structure is adapted from the study's separation of sequencing, orientating and loading decisions, while our implementation remains focused on rectangular items rather than free-form CAD parts.

The complete functional contract is in [`src/PRODUCT_SPEC.md`](src/PRODUCT_SPEC.md).

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

The package intentionally avoids one file per helper concept. Related geometry and search logic stay together until there is a clear reason to split them.

## Key packing rules

The solver must support:

- configurable carton catalogue,
- quantity expansion into physical items,
- upright-only items through `VerticalRotation`,
- maximum carton weight,
- configurable carton buffer,
- configurable fill threshold and fill percentage,
- 3D boundary and overlap checks,
- single and multiple carton packing,
- unpackable item reporting,
- independent final validation.

The exact orientation rule is illustrated in [`docs/images/exact_vertical_rotation_orientations.png`](docs/images/exact_vertical_rotation_orientations.png).

## Documentation

| Document | Purpose |
| --- | --- |
| [`src/PRODUCT_SPEC.md`](src/PRODUCT_SPEC.md) | Functional source of truth and MVP logic |
| [`docs/solver-approach-and-literature.md`](docs/solver-approach-and-literature.md) | Algorithm rationale and literature |
| [`docs/dataset-specification.md`](docs/dataset-specification.md) | Supplied benchmark data and fields |

Exploratory findings belong in `notebooks/`. Product behavior belongs in the product spec.

## Development principle

Build capability in layers: prove one-item fit, then multi-item geometry, then solve the complete order, then improve the answer only after the core solver works.

The historical iHub outputs are a benchmark rather than mathematical ground truth. A different arrangement is acceptable when it is valid, respects the agreed constraints and improves the stated objective.
