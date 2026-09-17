# 3D Bin Packing Solver

NUS Industry 4.0 Master's capstone project building a reusable Python 3D bin-packing and cartonization library, benchmarked against masked iHub order data.

The package is **`bin_packing_3d`**. iHub is the business use case and benchmark dataset, not the package identity.

## What it does

The solver accepts three things:

1. **Order data** — item dimensions, weight, quantity and rotation rule.
2. **Carton catalogue** — available carton dimensions and maximum weight.
3. **Configuration** — operational packing rules such as buffer and fill limits.

It returns the selected cartons, item placements, unpacked items and runtime.

## Python interface

```python
from bin_packing_3d import solve_order

result = solve_order(
    order=order,
    boxes=boxes,
    config=config,
)
```

A later FastAPI endpoint will be a thin wrapper around the same function so the packing engine remains reusable outside the API.

## Current milestone: MVP 0

The first implementation is deliberately simple:

```text
Validate request
    ↓
Expand Quantity into physical items
    ↓
For each item, test allowed orientations
    ↓
Reject cartons that fail weight or dimensions
    ↓
Choose the smallest-volume carton that fits
    ↓
Place one item per carton at x=0, y=0, z=0
    ↓
Return the packing result
```

This proves the API contract, data validation, orientation rules, carton selection and output schema before introducing multi-item geometry.

Multi-item packing, remaining empty spaces, First Fit and Best Fit come in later milestones.

## Documentation

| Document | Purpose |
| --- | --- |
| [`docs/API.md`](docs/API.md) | Request/response schemas, data types and FastAPI direction |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Package structure, module responsibilities and solver flow |
| [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) | Runtime packing rules and defaults |
| [`docs/TESTING.md`](docs/TESTING.md) | Unit-test strategy and MVP 0 cases |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | MVP 0 → multi-item geometry → First Fit vs Best Fit → improvement |
| [`src/PRODUCT_SPEC.md`](src/PRODUCT_SPEC.md) | Detailed engineering source of truth |
| [`docs/solver-approach-and-literature.md`](docs/solver-approach-and-literature.md) | Algorithm rationale and literature |
| [`docs/TERMINOLOGY.md`](docs/TERMINOLOGY.md) | Technical terms translated into plain language |
| [`docs/dataset-specification.md`](docs/dataset-specification.md) | Supplied benchmark data and fields |

## Repository structure

```text
ihubsolutions-capstone-project/
├── src/
│   ├── PRODUCT_SPEC.md
│   └── bin_packing_3d/        # reusable Python package
├── tests/                     # unit and component tests
├── docs/                      # API, architecture and project documentation
├── notebooks/                 # exploratory analysis and benchmark EDA
├── data/raw/                  # supplied development benchmark data
└── README.md
```

## Development principle

Build the smallest valid layer first, test it, then add packing intelligence without changing the public contract.

The historical iHub outputs are a benchmark rather than mathematical ground truth. A different carton arrangement is acceptable when it is valid, respects the agreed constraints and improves the stated objective.
