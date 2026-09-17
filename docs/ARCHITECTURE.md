# Architecture

The product is a reusable Python 3D bin-packing library with a thin API layer added later. FastAPI must call the same solver functions rather than duplicate packing logic.

## Package boundary

```text
src/bin_packing_3d/
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

Normal users should call only:

```python
from bin_packing_3d import solve_order
```

## End-to-end flow

```mermaid
flowchart TD
    A[Order, carton catalogue and config]
    B[Validate input and expand quantity]
    C[List allowed item orientations]
    D[Reject cartons that fail weight or dimensional checks]
    E[Try the smallest possible carton]
    F[Place items using the current packing stage]
    G{All items packed?}
    H[Try another or additional carton]
    I[Independently validate the result]
    J[Return cartons, item positions, unpacked items and runtime]

    A --> B --> C --> D --> E --> F --> G
    G -->|Yes| I --> J
    G -->|No| H --> F
```

The current implementation milestone is intentionally simpler than the full architecture: MVP 0 uses one physical item per carton and therefore does not yet need item-to-item overlap checks or remaining-empty-space tracking.

## Module responsibilities

| Module | Responsibility |
| --- | --- |
| `__init__.py` | Public `solve_order()` entry point |
| `models.py` | Shared request, internal and result models |
| `normalize.py` | Validation, defaults and quantity expansion |
| `orientation.py` | Allowed 90-degree item orientations |
| `feasibility.py` | Weight and dimension checks; carton ordering |
| `geometry.py` | Carton-boundary and item-overlap checks in later milestones |
| `spaces.py` | Remaining empty-space management in later milestones |
| `placement.py` | Shared multi-item placement candidate engine |
| `strategies.py` | First Fit and Best Fit selection rules |
| `single_box.py` | One-carton search |
| `multi_box.py` | Multiple-carton construction |
| `improve.py` | Optional bounded improvement after baseline benchmarking |
| `validate.py` | Independent final validation |
| `result.py` | Stable JSON-serializable output |

## Design rules

The package is client-neutral. iHub-specific request data is normalized at the boundary; core packing logic stays reusable.

The API layer stays thin. Pydantic/FastAPI own transport validation and documentation while `bin_packing_3d` owns packing behavior.

Each later algorithm stage must reuse the same request and response contract so packing quality can improve without breaking API consumers.

For the detailed component contracts, see [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md).
