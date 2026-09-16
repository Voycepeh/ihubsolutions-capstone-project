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
from ihub_packing import solve_order
```

The package `__init__.py` is the public facade and orchestrator. The remaining modules are internal components that should be developed and tested independently.

The technical packing term **Empty Maximal Space** is defined in `PRODUCT_SPEC.md`. In the rest of the repository we describe the same idea more simply as the **remaining empty rectangular spaces inside the carton**.

`spaces.py` owns creation, splitting, pruning and candidate position generation for those remaining empty spaces. `placement.py` owns shared candidate generation and validity checks. `strategies.py` contains the deliberate experimental difference between First Fit and Best Fit.

First Fit is the baseline. Best Fit is the comparison strategy. Both must use the same candidate universe and constraints so latency and packing quality can be compared fairly.

Implementation should proceed component by component. Each module should satisfy the functional contract and required unit tests in `PRODUCT_SPEC.md` before downstream modules depend on it.

Keep exploratory analysis in `notebooks/`. Move logic into `src/` only when its intended product behavior is clear enough to specify and test.
