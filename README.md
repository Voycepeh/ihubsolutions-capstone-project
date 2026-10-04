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

\`solve_order()\` is the only public solver function normal users need. Set \`trace=True\` when you want to see the shared screening decisions without changing the result:

\`\`\`python
result = solve_order(order=order, boxes=boxes, config=config, trace=True)
\`\`\`

For a single item the trace prints total item count and volume, evaluates cartons in external-volume order, explains volume and dimensional rejections, shows the allowed \`VerticalRotation\` orientations, and identifies the smallest feasible carton.

## Architecture

The reusable engine is deliberately separate from search algorithms:

```text
Engine
├── common rules and configuration
├── orchestration and solver registry
├── independent validation
└── common metrics

Solver plugins
├── First Fit
└── Best Fit
```

Solvers receive the same normalized domain objects and return a standard `PackingPlan`. The engine does not run strategies in sequence or assume how a plugin searches. It validates every proposal before returning success. First Fit and Best Fit implementations remain independently owned.

## Simplified package structure

```text
src/bin_packing_3d/
├── __init__.py
├── models.py
├── rules.py
├── solvers.py
├── engine.py
├── explain.py
├── validate.py
├── metrics.py
├── placement/
│   └── geometry.py
└── strategies/
    ├── first_fit.py
    └── best_fit.py
```

## Solver integration

```python
from bin_packing_3d import register_solver
from bin_packing_3d.models import PackingPlan

class FirstFitSolver:
    name = "first_fit"
    def solve(self, items, boxes, config):
        return PackingPlan(...)

register_solver("first_fit", FirstFitSolver())
```

First Fit and Best Fit are built-in production strategies. They share the same 3D placement primitives, rules, validator, and metrics so comparisons measure strategy choice rather than unrelated implementations.

## Key packing rules

The solver must support:

- configurable carton catalogue,
- quantity expansion into physical items,
- upright-only items through `VerticalRotation`,
- maximum carton weight,
- configurable carton buffer,
- a blanket maximum fill percentage plus a configurable stricter limit for high-item-count orders,
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
| [`notebooks/Single Item Solver Proof.ipynb`](notebooks/Single%20Item%20Solver%20Proof.ipynb) | Reproducible v1 proof of volume and geometry screening through the production API |

Exploratory findings belong in `notebooks/`. Product behavior belongs in the product spec.

## Development principle

Solvers propose packing plans; the engine validates, measures, and returns them. Historical iHub outputs are benchmarks rather than unique mathematical truth, so evaluation separates feasibility, constraint compliance, carton choice, utilization, and runtime.
