# iHub Solutions Capstone Project

NUS Industry 4.0 Master's capstone project developing a reusable 3D bin packing and cartonization solver for iHub.

## Project Goal

Build a lightweight Python solver that accepts **order data**, a **configurable box catalogue** and **configurable packing rules**, then returns a valid packing result while minimizing the number of cartons used.

The supplied 2,000 iHub request and response records are used as a benchmark. The goal is not to reproduce every historical output exactly or guarantee a mathematically global optimum for every 3D packing problem. The goal is to build a practical heuristic solver that is fast, explainable and measurable.

The Python library is the MVP. FastAPI can later be added as a thin service layer over the same packing engine.

The detailed functional source of truth is [`src/PRODUCT_SPEC.md`](src/PRODUCT_SPEC.md). Functional behavior should be agreed there before technical implementation changes it.

## How the Solver Works

Users should interact with one public entry point only:

```python
from ihub_packing import solve_order

result = solve_order(
    order=order,
    boxes=boxes,
    config=config,
)
```

Internally, the solver is deliberately modular so each part can be developed and unit tested independently.

```mermaid
flowchart LR
    A[solve_order API]
    B[Normalize and Validate]
    C[Feasibility Filter]
    D[Single Carton Solver]
    E[Multi Carton Solver]
    F[Bounded Improvement]
    G[Independent Validation]
    H[Result]

    A --> B --> C --> D
    D -->|one carton found| F
    D -->|no one carton solution| E --> F
    F --> G --> H

    classDef focal fill:#fff4ef,stroke:#eb6c36,stroke-width:2px,color:#2d3142;
    classDef standard fill:#ffffff,stroke:#2d3142,stroke-width:1px,color:#2d3142;
    classDef input fill:#f3f5f7,stroke:#9aa1ac,stroke-width:1px,color:#2d3142;

    class A focal;
    class B,C,D,E,F,G standard;
    class H input;
```

### 1. Normalize and Validate

The external order is converted into stable internal models. `Quantity > 1` becomes individual physical item instances, configuration defaults are resolved, and malformed items or cartons are rejected before any packing search begins.

### 2. Feasibility Filter

Cheap checks remove cartons that are definitely impossible based on effective dimensions after buffer, weight, active fill limit and whether every individual item has at least one legal orientation that can fit.

Passing these checks does not prove that all items fit together. It only means the carton is worth trying in the 3D placement engine.

### 3. Single Carton Solver

Because minimizing carton count is the primary objective, the solver tries to pack the whole order into one carton first. Viable cartons are attempted from smallest to largest.

The core XYZ placement engine uses legal item orientations and a small set of meaningful candidate positions rather than scanning arbitrary coordinates. Candidate points begin at `(0, 0, 0)` and new points are created from the positive X, Y and Z faces of successfully placed items.

Every candidate placement must remain inside the carton and must not overlap an existing item.

### 4. Multi Carton Solver

If no one carton solution exists, the solver constructs a multiple carton plan. Difficult items are handled first, existing open cartons are reused where the full XYZ placement still works, and a new carton is opened only when required.

### 5. Bounded Improvement

Once a valid plan exists, a small deterministic set of alternative item orderings or carton elimination attempts can be tested while runtime remains.

The solver always retains the best known valid plan. Improvement is never allowed to turn a working plan into an invalid result.

### 6. Independent Validation

The final result is checked independently from the solver that created it. The validator confirms item accounting, legal orientations, carton boundaries, non overlap, weight, fill and buffer compliance before success is returned.

## Why Volume Alone Is Not Enough

Total volume and weight are useful early filters, but they cannot prove that items physically fit.

For example, an item measuring `30 x 10 x 20` has less volume than a `20 x 20 x 20` carton, but it still cannot fit because one dimension is too long in every legal orientation.

For multiple items, the solver must determine whether they can occupy different XYZ positions in the same carton without overlap. This geometric placement is the central packing problem.

## Planned Solver Modules

| Module | Functional responsibility |
| --- | --- |
| `__init__.py` | Public `solve_order()` orchestrator |
| `models.py` | Shared internal data structures |
| `normalize.py` | Input validation, defaults and quantity expansion |
| `orientation.py` | Legal item orientations |
| `feasibility.py` | Cheap carton pruning |
| `geometry.py` | Bounds and collision primitives |
| `placement.py` | One carton XYZ placement engine |
| `single_box.py` | Smallest valid one carton search |
| `multi_box.py` | Multiple carton construction |
| `improve.py` | Runtime bounded improvement |
| `validate.py` | Independent final plan validation |
| `result.py` | Stable serializable output |

The module contracts and their required unit tests are defined in [`src/PRODUCT_SPEC.md`](src/PRODUCT_SPEC.md).

## Testing Principle

Unit tests are part of the implementation of each module, not a final cleanup step.

A component is only ready for the next development phase when its functional contract and tests pass. The normal CI suite should cover pure unit tests, component tests, end to end solver tests and regression fixtures. Historical iHub dataset benchmarking should run separately because it measures solution quality and runtime rather than basic correctness.

The final validator is intentionally independent from the placement heuristic so a bug in the solver cannot silently approve its own invalid geometry.

## Performance Direction

The solver should find a valid plan quickly and spend only the remaining runtime budget on improvements.

The initial engineering target is **P95 below 1 second per representative order**, with a target median below 250 ms. The runtime target does not weaken validity requirements.

The optimization priority is:

1. valid plan,
2. fewer cartons,
3. lower total carton volume,
4. higher utilization,
5. deterministic tie break.

## Configurable Packing Rules

The box catalogue is input to the solver and must not be hard coded. The supplied benchmark has already changed between dataset versions: v1 contains seven candidate cartons, while v2 contains six after Box3 was removed and Box2 was lengthened.

The packing rules are also configurable. Current benchmark defaults include:

| Rule | Default |
| --- | --- |
| Optimization objective | Minimize number of cartons |
| Fill threshold | 6 physical items |
| Maximum fill above threshold | 70% |
| Bin buffer | 0 mm length, 0 mm width, 6 mm height |
| Maximum weight | From the supplied box catalogue |
| Rotation | Item level `VerticalRotation` |

Under the current fill rule, orders with six or fewer physical items may use up to full carton volume. Orders with more than six physical items are limited to 70% volumetric fill per carton. Both values remain configurable.

## MVP Solver Capabilities

The solver should minimize carton count as the primary objective, support configurable box catalogues and packing rules, respect dimensions, permitted orientations, weight, buffer and fill constraints, handle quantity as physical items, support single and multiple carton packing, report unpacked items, return explicit XYZ placements, independently validate successful results, and expose runtime for benchmarking.

## Optimization Approach

Three dimensional bin packing is computationally difficult. Exact methods exist, but the literature also contains established constructive heuristics, local search, tabu search and geometric placement heuristics.

This project therefore uses a **lightweight deterministic heuristic approach**. It optimizes carton count under a practical computational budget rather than requiring proof of global optimality for every instance.

The XYZ engine follows a corner or extreme point style placement concept. It evaluates legal orientations at a small collection of candidate positions created from already placed cuboids. This makes the geometric search understandable and bounded while still testing actual physical placement rather than relying on volume alone.

Solution quality will be measured rather than assumed. The main evaluation areas are feasibility, carton count, utilization, constraint compliance and runtime. The historical iHub outputs are a benchmark rather than mathematical ground truth.

See [`docs/solver-approach-and-literature.md`](docs/solver-approach-and-literature.md) for the literature review and design rationale.

## Reference Dataset

The supplied development benchmark contains 2,000 masked iHub order request and response pairs. Two versions are retained under [`data/raw`](data/raw/) so catalogue changes can be compared without losing the original reference run.

| Version | Records | Candidate cartons | Notes |
| --- | ---: | ---: | --- |
| v1 | 2,000 | 7 | Original catalogue |
| v2 | 2,000 | 6 | Same orders rerun after Box3 removal and Box2 resize |

Across both versions:

| Property | Value |
| --- | --- |
| Units | mm for dimensions, kg for weight |
| Optimization mode | `bins_number` |
| Result status | All 2,000 successful |
| Unpacked items | None in the supplied sample |

The historical outputs are useful for comparing carton count, carton choice, utilization and latency. The team should also create edge cases and failure cases because the supplied sample contains only successful packings.

See [`data/raw/README.md`](data/raw/README.md) for the dataset specification and [`data/raw/CHANGELOG.md`](data/raw/CHANGELOG.md) for version differences.

## Key Project Files

| Artifact | Purpose |
| --- | --- |
| [`src/PRODUCT_SPEC.md`](src/PRODUCT_SPEC.md) | Functional source of truth for modules, solver behavior, tests and acceptance gates |
| [`notebooks/Inital EDA.ipynb`](notebooks/Inital%20EDA.ipynb) | Initial v1 analysis and benchmark understanding |
| [`notebooks/Inital EDA v2.ipynb`](notebooks/Inital%20EDA%20v2.ipynb) | Rerun of the initial EDA against the v2 benchmark with chart labels and written insights |
| [`docs/MVP Plan.md`](docs/MVP%20Plan.md) | Higher level project features, architecture, evaluation and sprint plan |
| [`docs/solver-approach-and-literature.md`](docs/solver-approach-and-literature.md) | Literature review and solver rationale |
| [`docs/dataset-specification.md`](docs/dataset-specification.md) | Dataset fields and packing rules |
| [`data/raw/CHANGELOG.md`](data/raw/CHANGELOG.md) | Raw benchmark dataset version history |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Team workflow |
| [`AGENTS.md`](AGENTS.md) | Instructions for AI agents working in the repository |
