# 3D Bin Packing Solver

NUS Industry 4.0 Master's capstone project for practical carton recommendation using masked iHub order data.

The goal is **not** to find a mathematically perfect Tetris-like packing. The goal is to recommend a small valid carton that a ground packer can reasonably use, while leaving configurable working space for more complex orders.

The solver follows the iHub source contract and uses **millimetres (mm)** as
its single canonical dimension unit for items, cartons, buffers, packed
coordinates, and visualization axes. Derived volumes are in cubic millimetres
(`mm^3`), while weight and maximum carton weight are in kilograms (`kg`).

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
   If all items can be placed, the carton is a valid recommendation. Otherwise the solver continues searching. The objective is to use the fewest cartons; ties prefer the smaller largest carton, then the smaller total carton volume.

## Use the solver

```python
from bin_packing_3d import solve_order

result = solve_order(
    order=order,
    boxes=boxes,
    mode="fast",
    dimension_unit="mm",
    logs=False,
    visualize=False,
)

# Print a concise summary with carton choices and XYZ placements.
print(result)
```

`solve_order()` is the main public interface. The supplied carton catalogue is configurable and is not hard-coded into the solver.
`PackingResult.to_dict()` remains available when an API or application needs structured JSON-compatible data instead of text.

### Optional 3D view

Ask the same solver call for a view when a notebook or demo needs an inspectable
picture of the validated cuboids, carton boundaries and intentional free space:

```python
result = solve_order(order, boxes, mode="fast", visualize=True)
```

The default camera places the `(0, 0, 0)` packing corner away from the viewer.
For another angle, use `visualization_kwargs` without changing any item coordinates:

```python
result = solve_order(
    order,
    boxes,
    mode="fast",
    visualize=True,
    visualization_kwargs={"elevation": 30, "azimuth": 210},
)
```

Visualization is optional and does not change packing. Independent validation
remains the authoritative boundary and collision check because a 3D projection
can visually hide overlap.

### See why a carton was selected

Use `logs=True` when you want a readable explanation without changing the solver result:

```python
result = solve_order(
    order=order,
    boxes=boxes,
    mode="fast",
    logs=True,
)
```

The log shows the initial weight, volume, and single-item dimension screening,
then reports the actual 3D search decisions. For each attempted item/carton pair
it records whether placement failed because of weight, fill, usable boundaries,
or collisions. It finishes with the selected cartons and every item's packed
orientation and XYZ position.

### Configure the quantity threshold and fill percentage

The user-configurable packing rules are explicit keyword parameters on
`solve_order()`:

```python
result = solve_order(
    order,
    boxes,
    mode="fast",
    high_item_count_threshold=6,       # BinMaxFillCheckMinItemQty
    high_item_count_max_fill_pct=70,   # BinMaxFillPct
    max_fill_pct=100,
    bin_buffer={"length": 0, "width": 0, "height": 6},
    dimension_unit="mm",
    logs=True,
    visualize=True,
)
```

With this configuration, orders containing up to six physical items may use
up to 100% of usable carton volume. Orders containing more than six are capped
at 70%. `logs` and `visualize` require Python booleans: `True` or `False`, not
the strings `"Yes"` or `"No"`.

## Strategies

The public API exposes two simple modes. Internally they map to the two production strategies:

| Strategy | Practical behaviour |
| --- | --- |
| **Fast** | Default. Uses the strong deterministic placement heuristic and bounded fixed-carton search that previously powered Best. |
| **Best** | Retains Fast as a validated fallback, then uses exact CP-SAT feasibility checks in objective order: carton count, largest carton volume, then total carton volume. The result reports whether optimality was proven or the time budget returned Fast. |

Both modes use the same input rules, 3D geometry checks, independent validator, and metrics. This lets us compare strategy behaviour rather than two unrelated implementations.

### Benchmark Fast, Best, and iHub

Run both modes over the same masked v2 orders with:

```bash
python notebooks/benchmark_solver_modes.py
```

Use `--limit N` for a quick trial or `--csv path/to/results.csv` for per-order
results. The report separates feasibility, carton count, selected carton types,
total external carton volume, and runtime. Fast, Best, and the recorded iHub
values are treated as warm latency measurements.

Best always retains the Fast plan as its baseline. It returns a different plan
only when the lexicographic objective improves: fewer cartons first, then a
smaller largest carton, then lower total external carton volume. Exact search
tests carton combinations in that order. `PackingResult.optimality_proven`
distinguishes a completed proof from a safe `time_limit` fallback.

## Key configurable rules

- carton catalogue and maximum carton weight
- item quantity and `VerticalRotation`
- carton Length, Width and Height buffer
- normal maximum fill percentage
- item-count threshold for a stricter fill limit
- stricter high-item-count fill percentage
- Fast or Best mode

The current defaults allow up to **100% usable volume for six or fewer physical items** and **70% for more than six**. These are operational rules, not claims that the solver can physically achieve that utilization.

## Project structure

The production code is intentionally small. Each module has one clear job:

| Module | Simple explanation |
| --- | --- |
| `engine.py` | **Runs the whole workflow.** Contains `solve_order()`, optional logging/visualization output, runtime measurement and result metrics. |
| `models.py` | **Defines the things the solver works with.** Items, cartons, XYZ positions, placements, packing plans and returned results. |
| `rules.py` | **Holds rules shared by every strategy.** Cleans inputs, expands quantity, handles allowed rotation, carton buffers and fill limits. |
| `placement.py` | **Tries an item inside a carton.** Generates XYZ candidate positions and rejects placements that cross the carton boundary or collide with another item. |
| `validate.py` | **Checks the solver's answer independently.** Makes sure every item is accounted for and the final plan respects dimensions, rotation, collision, weight and fill rules. |
| `display.py` | **Provides notebook tables.** Renders input records and packing summaries as safe HTML tables without requiring pandas. |
| `visualize.py` | **Optionally draws the validated result.** Shows each carton, item cuboid, coordinates and intentional free space. |
| `solvers.py` | **Provides the common strategy interface.** Lets Fast, Best, tests or future strategies plug into the same `solve_order()` workflow. |
| `strategies/best_fit.py` | **Fast strategy.** Scores feasible placements and tries fixed-carton combinations without exact backtracking. |
| `strategies/exact_fit.py` | **Best strategy.** Uses a bounded exact 3D constraint model and falls back to the validated Fast plan on timeout. |

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
    ├── best_fit.py
    └── exact_fit.py
```

The package stays independent of pandas. IPython supports the optional notebook table helpers, and Matplotlib is used only when optional 3D visualization is requested.

## Proof and deeper documentation

| Document | Purpose |
| --- | --- |
| [Product specification](src/PRODUCT_SPEC.md) | Detailed functional rules and API contract |
| [Solver approach and literature](docs/solver-approach-and-literature.md) | Why the packing approach was chosen |
| [Dataset specification](docs/dataset-specification.md) | Supplied benchmark data and fields |
| [Solver Demo](notebooks/Solver%20Demo.ipynb) | Guided proof of the full solver flow, configurable constraints, explainable placements, Fast/Best/iHub wins and losses, and the reproducible 2,000-order benchmark. |

## Development principle

**Solvers propose; the engine validates.**

The solver's XYZ coordinates prove that a proposed arrangement does not exceed carton boundaries or collide. They should not be interpreted as exact instructions that a ground packer must reproduce.

Historical iHub carton choices are useful benchmarks, not the only correct answer.
