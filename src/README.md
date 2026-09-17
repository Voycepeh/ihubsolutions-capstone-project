# Source Code

`src/` contains the reusable 3D bin packing package and its single functional specification.

Before changing solver behavior, update [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md). That document defines the public interface, required rules, packing logic, MVP sequence, tests and benchmark expectations.

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

- `__init__.py` orchestrates the solver and exposes `solve_order()`.
- `models.py` contains shared data structures.
- `rules.py` owns input normalization, orientations and business constraints.
- `packing.py` owns geometry, empty spaces, First Fit, Best Fit, single carton and multiple carton packing.
- `validate.py` independently checks every completed plan.

Do not create a new Python module for every helper function or algorithm step. Keep related logic together until there is a clear reason to split it.

Exploratory analysis belongs in `notebooks/`. Supporting research and dataset documentation belong in `docs/`.
