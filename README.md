# 3D Bin Packing Solver

NUS Industry 4.0 Master's capstone project for practical carton recommendation using masked iHub order data.

The goal is **not** to find a mathematically perfect Tetris-like packing. The goal is to recommend a small valid carton that a ground packer can reasonably use, while leaving configurable working space for more complex orders.

## How it works

For each order, the solver follows six practical steps:

1. **Check weight**  
   Add the order weight and reject cartons that cannot carry it.

2. **Check usable volume**  
   Add the item volumes and compare them with each carton's usable volume. The fill limit is configurable. By default, orders with six or fewer physical items may use up to 100% of usable volume; orders with more than six use up to 70%. This spare space is an operational buffer so the ground packer does not need to reproduce a perfect 3D puzzle.

3. **Check whether each item can physically fit**  
   Volume alone is not enough. Each item's Length × Width × Height must fit within the carton's usable dimensions using only its allowed rotations.

4. **Try the items in XYZ space**  
   The carton is treated as a 3D coordinate space. The solver tries item positions and allowed orientations inside it.

5. **Reject impossible placements**  
   An item cannot extend outside the carton or overlap another item. The XYZ placement is a feasibility check, not a precise packing instruction for the ground packer.

6. **Recommend the carton**  
   If all items can be placed, the carton is a valid recommendation. Otherwise the solver continues searching. The objective is to use the fewest cartons and, when carton count is equal, prefer the smaller total carton volume.

## Use the solver

```python
from bin_packing_3d import solve_order

result = solve_order(
    order=order,
    boxes=boxes,
    config={"strategy": "first_fit"},
)
```

`solve_order()` is the main public interface. The supplied carton catalogue is configurable and is not hard-coded into the solver.

### See why a carton was selected

Use `trace=True` when you want a readable explanation without changing the solver result:

```python
result = solve_order(
    order=order,
    boxes=boxes,
    config={"strategy": "first_fit"},
    trace=True,
)
```

For the current single-item proof, the trace shows the item count and volume, checks cartons from smallest external volume upward, explains volume and dimension failures, shows allowed rotations, and identifies the smallest feasible carton.

## Strategies

The production package currently contains two strategies:

| Strategy | Practical behaviour |
| --- | --- |
| **First Fit** | Takes the first valid placement/carton found in deterministic search order. |
| **Best Fit** | Compares feasible choices and prefers the tighter placement according to its scoring rules. |

Both strategies use the same input rules, 3D geometry checks, independent validator, and metrics. This lets us compare strategy behaviour rather than two unrelated implementations.

## Key configurable rules

- carton catalogue and maximum carton weight
- item quantity and `VerticalRotation`
- carton Length, Width and Height buffer
- normal maximum fill percentage
- item-count threshold for a stricter fill limit
- stricter high-item-count fill percentage
- First Fit or Best Fit strategy

The current defaults allow up to **100% usable volume for six or fewer physical items** and **70% for more than six**. These are operational rules, not claims that the solver can physically achieve that utilization.

## Project structure

The production code is intentionally small. Each module has one clear job:

| Module | Simple explanation |
| --- | --- |
| `engine.py` | **Runs the whole workflow.** Contains `solve_order()`, optional `trace=True` output, runtime measurement and result metrics. |
| `models.py` | **Defines the things the solver works with.** Items, cartons, XYZ positions, placements, packing plans and returned results. |
| `rules.py` | **Holds rules shared by every strategy.** Cleans inputs, expands quantity, handles allowed rotation, carton buffers and fill limits. |
| `placement.py` | **Tries an item inside a carton.** Generates XYZ candidate positions and rejects placements that cross the carton boundary or collide with another item. |
| `validate.py` | **Checks the solver's answer independently.** Makes sure every item is accounted for and the final plan respects dimensions, rotation, collision, weight and fill rules. |
| `solvers.py` | **Provides the common strategy interface.** Lets First Fit, Best Fit, tests or future strategies plug into the same `solve_order()` workflow. |
| `strategies/first_fit.py` | **First Fit strategy.** Uses the first valid carton and placement found in deterministic search order. |
| `strategies/best_fit.py` | **Best Fit strategy.** Compares valid choices and selects the tighter option using its scoring rules. |

```text
src/bin_packing_3d/
├── __init__.py
├── engine.py
├── models.py
├── rules.py
├── placement.py
├── validate.py
├── solvers.py
└── strategies/
    ├── first_fit.py
    └── best_fit.py
```

The production package stays independent of pandas, notebooks, CSV output, charts and benchmark reporting. Those belong outside the API.

## Proof and deeper documentation

| Document | Purpose |
| --- | --- |
| [Product specification](src/PRODUCT_SPEC.md) | Detailed functional rules and API contract |
| [Solver approach and literature](docs/solver-approach-and-literature.md) | Why the packing approach was chosen |
| [Dataset specification](docs/dataset-specification.md) | Supplied benchmark data and fields |
| [Single Item Solver Proof](notebooks/Single%20Item%20Solver%20Proof.ipynb) | Reproducible proof using the production API and original v1 sample |

## Development principle

**Solvers propose; the engine validates.**

The solver's XYZ coordinates prove that a proposed arrangement does not exceed carton boundaries or collide. They should not be interpreted as exact instructions that a ground packer must reproduce.

Historical iHub carton choices are useful benchmarks, not the only correct answer.
