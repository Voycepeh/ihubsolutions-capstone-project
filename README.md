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

The solver is built in four MVPs that follow the actual packing problem.

1. **MVP 1: Fit one item** — test allowed orientations and identify the smallest valid carton for one physical item.
2. **MVP 2: Pack one carton** — expand order quantities into physical item instances, then use First Fit to sequence, orient and place as many items as possible into one carton. Return the packed items and the remaining items.
3. **MVP 3: Pack the whole order** — repeatedly use the one-carton engine until the full order is packed. This produces the fast validated **First Fit baseline plan**.
4. **MVP 4: Improve the plan** — use the remaining runtime to try Best Fit and selected alternative sequences. Keep an alternative only when it reduces carton count, or uses smaller total carton volume with the same carton count. If the time limit is reached, return the best validated plan already found, with the First Fit baseline as the guaranteed fallback.

The core packing loop is:

**sequence items → choose allowed orientation → choose XYZ position → validate placement → continue or retry**

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

Build capability in layers: prove one-item fit, then pack one carton, then solve the complete order with a fast First Fit baseline, then spend only the remaining runtime trying to improve that validated result.

The historical iHub outputs are a benchmark rather than mathematical ground truth. A different arrangement is acceptable when it is valid, respects the agreed constraints and improves the stated objective.
