# Source Code

`src/` contains the reusable cartonization product and its functional specification.

Before implementing or changing solver behavior, update [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md). The specification defines the public interface, module boundaries, functional behavior, objective ordering, unit test requirements and acceptance gates.

## Planned Package

```text
src/
  PRODUCT_SPEC.md
  ihub_packing/
    __init__.py
    models.py
    normalize.py
    orientation.py
    feasibility.py
    geometry.py
    placement.py
    single_box.py
    multi_box.py
    improve.py
    validate.py
    result.py
```

Users should call only:

```python
from ihub_packing import solve_order
```

The package `__init__.py` is the public facade and orchestrator. The remaining modules are internal components that should be developed and tested independently.

Implementation should proceed component by component. Each module should satisfy the functional contract and required unit tests in `PRODUCT_SPEC.md` before downstream modules depend on it.

Keep exploratory analysis in `notebooks/`. Move logic into `src/` only when its intended product behavior is clear enough to specify and test.