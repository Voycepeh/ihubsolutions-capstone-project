# Source Code

`src/` contains the reusable 3D bin packing package and its functional specification.

Before changing solver behavior, update [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md). That document defines the public interface, packing rules, MVP sequence, tests and benchmark expectations.

## Package

```text
src/
  PRODUCT_SPEC.md
  bin_packing_3d/
    __init__.py
    models.py
    rules.py
    packing.py
    validate.py
```

Users call only:

```python
from bin_packing_3d import solve_order
```

The internal package stays deliberately small:

- `__init__.py` orchestrates `solve_order()`.
- `models.py` contains shared data structures.
- `rules.py` owns normalization, orientations and business constraints.
- `packing.py` owns sequencing, orientation/placement search, geometry, single-carton packing, multi-carton packing and later improvement strategies.
- `validate.py` independently checks every completed plan.

## Development order

Implementation follows four business capabilities:

1. **MVP 1 — Fit one item:** find the smallest valid carton for one physical item.
2. **MVP 2 — Pack one carton:** expand quantity into physical item instances, then use First Fit to sequence, orient and place items in one carton. Return packed items plus the remaining items.
3. **MVP 3 — Pack the whole order:** repeatedly reuse the one-carton engine until all items are packed. This is the fast validated First Fit baseline.
4. **MVP 4 — Improve the plan:** within the remaining runtime, try Best Fit and selected alternative sequences. Keep only a valid plan that uses fewer cartons, or smaller total carton volume when carton count is equal. On timeout, return the best validated plan already found.

The core packing loop is:

**sequence → orient → place → validate → retry if needed**

The First Fit baseline from MVP 3 is never discarded while improvement is running.

Do not create a new Python module for every helper function or algorithm step. Keep related logic together until there is a clear reason to split it.

Exploratory analysis belongs in `notebooks/`. Supporting research and dataset documentation belong in `docs/`.
