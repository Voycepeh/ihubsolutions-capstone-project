# Source Code

`src/` contains the reusable package and [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md), the functional source of truth.

```text
bin_packing_3d/
├── models.py      # shared domain objects and errors
├── rules.py       # normalization and deterministic business rules
├── solvers.py     # minimal plugin protocol and registry
├── engine.py      # solve_order orchestration
├── validate.py    # independent final validation
└── metrics.py     # common measurements
```

Normal users need only `from bin_packing_3d import solve_order`. The engine does not implement First Fit or Best Fit: each is a plugin receiving normalized objects and returning `PackingPlan`.

## Adding a solver

```python
from bin_packing_3d import register_solver
from bin_packing_3d.models import PackingPlan

class FirstFitSolver:
    name = "first_fit"

    def solve(self, items, boxes, config):
        # Search implementation remains owned by this plugin.
        return PackingPlan(...)

register_solver("first_fit", FirstFitSolver())
```

Registration requires no change to `engine.py`. Solver output is independently checked for accounting, orientations, coordinates, boundaries, overlap, carton identity, weight, and fill before success is returned.
