# Source Code

`src/` contains the reusable 3D bin-packing product and its functional specification.

Before implementing or changing solver behavior, update [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md). The specification defines the public interface, module boundaries, functional behavior, objective ordering, unit test requirements and acceptance gates.

The repository terminology guide is [`../docs/TERMINOLOGY.md`](../docs/TERMINOLOGY.md). Technical packing terms are defined once there and in the product spec; normal documentation should then use the simpler wording.

## Planned Package

```text
src/
  PRODUCT_SPEC.md
  bin_packing_3d/
    __init__.py
    models.py
    normalize.py
    orientation.py
    feasibility.py
    geometry.py
    spaces.py
    placement.py
    strategies.py
    single_box.py
    multi_box.py
    improve.py
    validate.py
    result.py
```

Users should call only:

```python
from bin_packing_3d import solve_order
```

The package `__init__.py` is the public facade and orchestrator. The remaining modules are internal components that should be developed and tested independently.

The technical term **Empty Maximal Space** means a useful rectangular region of empty space remaining inside a carton. After that definition, this repository simply calls these **remaining empty spaces**.

The technical term **Extreme Point** means a useful placement position created from carton or already-packed item boundaries. After that definition, this repository simply calls these **candidate positions**.

`spaces.py` owns creation, splitting, cleanup and candidate-position generation for the remaining empty spaces. `placement.py` owns shared candidate generation and validity checks. `strategies.py` contains the deliberate experimental difference between First Fit and Best Fit.

First Fit is the baseline. Best Fit is the comparison strategy. Both must use the same candidate options and constraints so runtime and packing quality can be compared fairly.

Implementation should proceed component by component. Each module should satisfy the functional contract and required unit tests in `PRODUCT_SPEC.md` before downstream modules depend on it.

Keep exploratory analysis in `notebooks/`. Move logic into `src/` only when its intended product behavior is clear enough to specify and test.
