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

Implementation should follow the business capability rather than individual algorithm names:

1. **MVP 0**: fit one item into the smallest valid carton.
2. **MVP 1**: pack multiple items into one carton.
3. **MVP 2**: solve the full order using the fewest cartons and then the smallest carton combination.
4. **MVP 3**: improve the valid result with controlled retries such as First Fit vs Best Fit, alternative sequences and carton consolidation.

The core packing loop is:

**sequence → orient → place → validate → retry if needed**

Do not create a new Python module for every helper function or algorithm step. Keep related logic together until there is a clear reason to split it.

Exploratory analysis belongs in `notebooks/`. Supporting research and dataset documentation belong in `docs/`.
