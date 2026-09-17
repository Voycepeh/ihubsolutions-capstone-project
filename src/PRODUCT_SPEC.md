# 3D Bin Packing Product Specification

## 1. Purpose

This document is the functional source of truth for the reusable 3D bin-packing solver used in the iHub capstone before implementation begins.

The objective is to agree exactly how each component behaves, what it receives, what it returns, what it must reject, and how it will be tested. Technical implementation must follow these contracts rather than allowing code choices to define product behavior after the fact.

The product is a reusable Python packing engine. Users interact with one public function only. Internal modules remain independently testable so the solver can be developed component by component and later exposed through an API without rewriting the packing logic.

The reusable Python package is named **`bin_packing_3d`**. iHub is the benchmark dataset and business use case, not the package identity.

## 2. Product Goal

Given an order, a configurable carton catalogue, and configurable packing rules, return a valid packing plan within a bounded runtime while minimizing carton count as the primary objective.

A one-carton solution always beats a two-carton solution when both are valid. Among solutions using the same number of cartons, prefer lower total carton volume and then higher space utilization.

Validity always comes before optimization. An invalid arrangement must never be returned merely because it uses fewer cartons.

## 3. Technical Terms Used in This Specification

The project uses a few established packing terms. They are defined here once so the rest of the specification can use simpler language.

**Empty Maximal Space** is the technical term for a useful rectangular region of empty space remaining inside a carton after items have been placed. From this point onward, this document calls it a **remaining empty space** or **empty rectangular space**.

**Extreme Point** is the technical term for a useful placement position created from carton boundaries or the faces of items already packed. From this point onward, this document calls it a **candidate position**.

A **heuristic** is a practical rule-based method that tries to find a good solution quickly without proving the mathematically best possible answer. From this point onward, this document generally uses **packing strategy**, **method**, or **approach**.

**Axis-aligned placement** means an item is kept parallel to the carton X, Y and Z axes rather than placed diagonally. From this point onward, this document generally says **allowed 90-degree orientation**.

See [`../docs/TERMINOLOGY.md`](../docs/TERMINOLOGY.md) for the repository-wide terminology guide.

## 4. Selected V1 Solver Strategy

The V1 geometric foundation is a deterministic 3D packing engine that tracks the remaining empty rectangular spaces inside a carton.

Items are tested only at useful candidate positions inside those spaces. The solver does not scan every possible XYZ coordinate and does not perform exhaustive search.

The shared geometry engine supports two placement strategies:

1. **First Fit** is the baseline strategy.
2. **Best Fit** is the comparison strategy.

Both strategies must use the same item ordering, allowed orientations, remaining empty spaces, candidate positions, overlap checks, carton rules, and final validator. This isolates the difference between placement-selection strategies rather than comparing two completely different engines.

### 4.1 First Fit baseline

First Fit checks candidate positions in a deterministic order and accepts the first valid placement.

Conceptually:

```python
for space in ordered_spaces:
    for orientation in allowed_orientations:
        for position in candidate_positions:
            if placement_is_valid(...):
                return placement
```

First Fit does not score every valid candidate before placing the item.

Its purpose is to establish the simplest fast baseline and measure how far a low-search-cost strategy can go before extra placement evaluation becomes worthwhile.

### 4.2 Best Fit comparison

Best Fit uses the same candidate generation but evaluates all valid candidates within the configured limits, scores them using a fixed priority order, and selects the preferred placement.

Conceptually:

```python
valid_candidates = []

for space in ordered_spaces:
    for orientation in allowed_orientations:
        for position in candidate_positions:
            if placement_is_valid(...):
                valid_candidates.append(score(...))

return best(valid_candidates)
```

Best Fit exists to test whether extra candidate evaluation produces better packing outcomes that justify the additional runtime.

### 4.3 Experimental question

The project must not assume Best Fit is better overall simply because it searches more placements.

The benchmark must answer:

1. Is First Fit materially faster at median and P95 runtime?
2. How often does Best Fit reduce carton count relative to First Fit?
3. When carton count is equal, does Best Fit select lower total carton volume?
4. Does Best Fit improve space utilization?
5. On which order-complexity bands do the strategies diverge?
6. Is any improvement large enough to justify the added search cost?

The default production strategy should be selected only after these results are measured.

### 4.4 V1 boundary

Included in V1:

1. Remaining empty rectangular spaces as the search-space representation.
2. Allowed 90-degree item orientations.
3. Useful candidate positions inside each remaining empty space.
4. Exact carton-boundary and item-overlap checks.
5. Deterministic First Fit placement.
6. Deterministic Best Fit placement for comparison.
7. Updating and removing unusable empty spaces after every placement.
8. Deterministic item ordering.
9. Independent final validation.
10. Strategy-level benchmarking.

Deferred until benchmark evidence shows they are needed:

1. Trying several starting orders.
2. Simulated annealing or genetic algorithms.
3. Large-neighborhood search.
4. Going back to change earlier placements through depth-first search or backtracking.
5. Physical support ratio or center-of-gravity constraints.
6. Parallel search workers.
7. 3D-grid or voxel-based arbitrary-shape packing, including Fast Fourier Transform approaches.

The design is inspired by established 3D packing techniques while remaining an independently implemented Python solver adapted to iHub-specific rules.

## 5. Performance Goal

The engineering target is a P95 runtime below 1,000 ms per representative order. In plain terms, the target is for 95% of representative orders to finish within one second.

The solver does not need to prove the mathematically best possible packing for every order. It should find a valid plan quickly, then use any remaining runtime budget for bounded improvement only when configured.

| Metric | Initial target |
| --- | ---: |
| Median runtime | below 250 ms |
| P95 runtime | below 1,000 ms |
| Validity | 100% of returned packed solutions pass independent validation |
| Repeatability | Same inputs, configuration, and strategy return the same result |
| Optimization priority | Minimize carton count first |

First Fit and Best Fit runtime must be reported independently.

## 6. Public Interface

```python
from bin_packing_3d import solve_order

result = solve_order(
    order=order,
    boxes=boxes,
    config=config,
)
```

`solve_order()` is the only function normal users need to call.

The package `__init__.py` is the public facade and orchestrator. Internal modules are implementation details and are directly imported only by tests and developers.

A later FastAPI endpoint should call the same function rather than create another solver implementation.

The strategy should be configurable without changing solver code:

```python
config = {
    "placement_strategy": "first_fit"
}
```

Supported V1 values are `first_fit` and `best_fit`.

## 7. Public Input Contract

The solver receives three logical inputs: order, carton catalogue, and configuration.

### 7.1 Order

Minimum required item information:

| Field | Meaning |
| --- | --- |
| `OrderId` | Order identifier |
| `OrderNo` | External order reference |
| `Code` | Item identifier |
| `Length`, `Width`, `Height` | Item dimensions in mm |
| `Weight` | Unit weight in kg |
| `Quantity` | Number of physical units |
| `VerticalRotation` | Whether the item may be laid onto another axis |
| `UOM` | Optional descriptive unit |

`Quantity > 1` is expanded so every physical unit receives its own placement.

### 7.2 Carton catalogue

| Field | Meaning |
| --- | --- |
| `Code` | Carton identifier |
| `Length`, `Width`, `Height` | Carton dimensions in mm before configured clearance |
| `MaxWeight` | Maximum packed weight in kg |

The carton catalogue is input and must not be hard coded.

### 7.3 Configuration

| Setting | Initial default | Functional meaning |
| --- | ---: | --- |
| `optimization_mode` | `bins_number` | Minimize number of cartons |
| `placement_strategy` | `first_fit` | Baseline or comparison placement strategy |
| `bin_max_fill_check_min_item_qty` | 6 | Fill cap activates above this physical item count |
| `bin_max_fill_pct` | 70 | Maximum volume fill after the threshold |
| `bin_buffer.length` | 0 mm | Reserved length clearance |
| `bin_buffer.width` | 0 mm | Reserved width clearance |
| `bin_buffer.height` | 6 mm | Reserved height clearance |
| `max_runtime_ms` | 900 ms | Solver search deadline |
| `max_empty_spaces` | 200 | Initial safety cap on retained empty rectangular spaces |
| `max_candidate_positions_per_space` | 8 | Initial safety cap on positions checked inside each empty space |
| `deterministic` | true | Same input and settings should return the same result |

The safety caps are tunable and must be benchmarked before being treated as stable defaults.

## 8. Conceptual Package Structure

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

tests/
  test_normalize.py
  test_orientation.py
  test_feasibility.py
  test_geometry.py
  test_spaces.py
  test_placement.py
  test_strategies.py
  test_single_box.py
  test_multi_box.py
  test_improve.py
  test_validate.py
  test_solve_order.py
  fixtures/
```

`spaces.py` owns creation, splitting, candidate-position generation, and cleanup of the remaining empty spaces.

`placement.py` owns shared placement-candidate generation and validity checks.

`strategies.py` owns the difference between First Fit and Best Fit so geometry is not duplicated.

## 9. End-to-End Functional Flow

```mermaid
flowchart TD
    A[Order + carton catalogue + configuration]
    B[Normalize and validate input]
    C[List allowed item orientations]
    D[Reject cartons that are definitely impossible]
    E[Try one carton first, smallest possible first]
    F[Track remaining empty rectangular spaces]
    G[Generate useful candidate positions]
    H[Check carton boundaries and item overlap]
    I{Placement strategy}
    J[First Fit: take first valid position]
    K[Best Fit: compare valid positions and choose preferred one]
    L[Place item and update remaining empty spaces]
    M{All items packed?}
    N[Try next possible single carton]
    O[Build multiple-carton plan]
    P[Independently validate final plan]
    Q[Return result]

    A --> B --> C --> D --> E --> F --> G --> H --> I
    I --> J --> L
    I --> K --> L
    L --> M
    M -->|No, next item| G
    M -->|Item cannot be placed| N
    N -->|Another carton available| E
    N -->|No single carton works| O
    M -->|Yes| P
    O --> P --> Q
```

The strategy changes how a valid placement is selected. It does not change the business rules or the geometry checks.

## 10. Component Specifications

### 10.1 `__init__.py`: Public Orchestrator

Responsibility: expose `solve_order()` and coordinate the complete solver flow without implementing geometry.

Functional behavior:

1. Start runtime measurement and establish the deadline.
2. Normalize external input.
3. Validate input structures.
4. Run quick carton rejection checks.
5. Resolve the configured placement strategy.
6. Attempt the single-carton solver first.
7. Call the multiple-carton solver only when no valid one-carton solution exists.
8. Run bounded improvement only when configured and runtime remains.
9. Independently validate the final plan.
10. Format and return the result.
11. Never return an invalid plan as success.

Tests must verify call ordering, strategy propagation, single-carton short-circuiting, multiple-carton fallback, deadline propagation, validation before success, repeatable output, and failure propagation.

### 10.2 `models.py`: Internal Data Models

Responsibility: define shared data structures such as `Item`, `Box`, `Orientation`, `Position`, `Placement`, `EmptySpace`, `PackedBox`, `PackingPlan`, `PackingConfig`, and `PackingResult`.

Models contain data and small derived properties only. Solver decisions do not belong in model classes.

Tests cover volume calculations, usable carton dimensions, serialization, equality required for repeatable comparison, and invalid values.

### 10.3 `normalize.py`: Input Normalization

Functional behavior:

1. Validate dimensions and weight are positive numeric values.
2. Validate quantity is a positive integer.
3. Expand `Quantity > 1` into physical item instances.
4. Preserve source traceability.
5. Normalize `VerticalRotation` to boolean.
6. Apply defaults only when settings are missing.
7. Reject cartons whose usable dimensions become zero or negative after clearance is applied.
8. Reject duplicate carton codes.
9. Reject unknown placement strategies.

Tests cover valid input, quantity expansion, malformed dimensions, invalid quantity, missing fields, boolean normalization, duplicate carton codes, strategy normalization, defaults, and invalid clearance effects.

### 10.4 `orientation.py`: Allowed Item Orientations

For `VerticalRotation = true`, generate every unique 90-degree orientation formed by permuting length, width, and height, up to six orientations.

For `VerticalRotation = false`, the original height remains the vertical Z dimension. Length and width may swap horizontally, producing one or two unique orientations.

Duplicate orientations must be removed and results must have a stable order. Orientation results may be cached by item dimensions and rotation rule because equivalent items reuse the same orientation set.

Tests cover six-orientation rectangular items, repeated dimensions, cubes, upright-only items, horizontal swaps, duplicate removal, caching equivalence, and stable ordering.

### 10.5 `feasibility.py`: Quick Carton Rejection Checks

For each candidate carton:

1. Calculate usable dimensions after clearance.
2. Check total order weight for a one-carton attempt.
3. Calculate the active fill limit from physical item count.
4. Reject when total item volume exceeds allowed usable volume.
5. Confirm every physical item can individually fit in at least one allowed orientation.
6. Keep only cartons passing all quick checks.
7. Sort surviving cartons by usable carton volume ascending with stable carton-code tie break.

Passing these checks does not prove the items fit together. It only proves the carton is worth attempting in the 3D placement engine.

Tests cover weight, fill, clearance, item dimensional fit, rotation restrictions, carton ordering, and the six-item threshold rule.

### 10.6 `geometry.py`: Boundary and Overlap Checks

Required concepts:

```python
fits_inside_box(...)
boxes_overlap(...)
placement_collides(...)
```

`fits_inside_box()` confirms a placement remains within usable carton boundaries.

`boxes_overlap()` treats items as rectangular 3D boxes. Two items overlap only when their occupied ranges overlap on X, Y, and Z simultaneously. Touching faces, edges, or corners are valid and are not overlap.

No soft deformation, diagonal placement, or free-angle rotation is supported in V1.

Tests cover containment, boundary touching, separation on each axis, true overlap, face and edge contact, negative coordinates, and clearance-adjusted boundaries.

### 10.7 `spaces.py`: Remaining Empty Space Management

Responsibility: maintain the remaining usable rectangular spaces after each placement.

Functional behavior:

1. Start with one empty rectangular space equal to the entire usable carton.
2. When an item is placed, identify empty spaces intersected by that placement.
3. Replace affected spaces with the remaining rectangular subspaces created around the placement.
4. Discard zero- or negative-volume spaces.
5. Remove duplicate spaces.
6. Remove spaces fully contained inside another retained space.
7. Remove spaces that cannot fit any remaining item in any allowed orientation.
8. Sort spaces in a stable order, preferring lower positions and then stable coordinate order.
9. Apply `max_empty_spaces` only after safe cleanup.
10. Generate candidate positions from useful space corners and boundaries formed by already placed items.
11. Remove duplicate candidate positions and discard positions that cannot hold the tested orientation inside the current empty space.

Tests must cover initial space creation, splitting after a placement, duplicate removal, contained-space removal, fit-based removal, stable ordering, candidate-position generation, and safety-cap behavior.

### 10.8 `placement.py`: Shared 3D Placement Engine

Responsibility: generate valid placement candidates using shared geometry and remaining-empty-space behavior.

Functional behavior:

1. Create the initial empty rectangular space through `spaces.py`.
2. Sort difficult items first. V1 priority is restricted rotation, then larger volume, then larger longest dimension, then stable item ID.
3. For the current item, iterate retained empty spaces in a stable order.
4. For each space, iterate allowed orientations in a stable order.
5. Generate bounded candidate positions in a stable order.
6. Reject candidates outside the usable carton.
7. Reject candidates overlapping placed items.
8. Pass valid candidate placements to the configured strategy.
9. Place the strategy-selected candidate.
10. Update and clean up remaining empty spaces.
11. Continue until every item is placed or no valid candidate exists.
12. Return failure for the current packing attempt when an item cannot be placed.

The shared engine must not contain strategy-specific shortcuts that make First Fit and Best Fit receive different candidate options.

Required placement fixtures:

1. One item fits at origin.
2. Two `15 x 10 x 10` items fit in a `20 x 20 x 20` carton without overlap.
3. One `30 x 10 x 20` item fails in a `20 x 20 x 20` carton regardless of spare volume.
4. A case requiring rotation succeeds when rotation is allowed.
5. The same case fails when upright-only rules prohibit the required rotation.
6. Repeated execution with the same strategy returns identical placements.

### 10.9 `strategies.py`: First Fit and Best Fit

Responsibility: select one placement from the valid candidates exposed by `placement.py`.

#### First Fit

1. Consume candidates in the shared stable order.
2. Return immediately on the first valid candidate.
3. Do not continue searching after a valid candidate is accepted.
4. Do not calculate Best Fit scoring fields unless required for diagnostics.

Tests must prove that First Fit stops after the first valid candidate, preserves stable ordering, and does not evaluate later candidates unnecessarily.

#### Best Fit

1. Consume all valid candidates within configured limits.
2. Compare each candidate using the agreed priority order.
3. Choose the preferred candidate.

Initial Best Fit preference order:

1. lower resulting top height,
2. greater contact with carton boundaries or already placed items,
3. smaller wasted remainder in the chosen empty space,
4. lower vertical coordinate,
5. lower depth coordinate,
6. lower horizontal coordinate,
7. stable orientation and position tie break.

Tests must prove that Best Fit evaluates the same candidate set First Fit could encounter, selects the expected candidate in constructed cases, and returns the same result for repeated runs with the same input.

#### Strategy equivalence contract

For a given packing state, item, configuration, and remaining-empty-space set:

1. Both strategies use the same ordered candidate generator.
2. Both use the same validity checks.
3. Both use the same business constraints.
4. The only intended difference is when candidate evaluation stops and how a valid candidate is selected.

This contract is essential for a fair benchmark.

### 10.10 `single_box.py`: Single-Carton Solver

1. Receive only cartons that passed quick rejection checks.
2. Try cartons from smallest usable volume to largest.
3. Call the shared placement engine using the configured strategy.
4. Stop at the first valid carton because any one-carton solution satisfies the primary carton-count objective.
5. Return failure only after all viable one-carton candidates fail.

First Fit and Best Fit must be runnable independently against the same order and carton catalogue.

Tests prove smallest valid carton selection, geometric fallback to the next carton, strategy propagation, and multiple-carton avoidance when a one-carton result exists.

### 10.11 `multi_box.py`: Multiple-Carton Construction

1. Process difficult items first.
2. Try to insert remaining items into existing open cartons before opening another carton.
3. Repack an affected carton through the shared placement engine with the configured strategy after a proposed insertion rather than trusting volume alone.
4. When no open carton accepts an item, open the smallest possible carton that can accept it.
5. Continue until all items are packed or an item cannot fit any candidate carton.
6. Return unpacked items explicitly.
7. Enforce weight, fill, clearance, rotation, and geometry rules for every carton.

Tests cover two-carton success, reuse of an open carton, weight-driven split, fill-driven split, geometry-driven split, unpackable items, strategy propagation, and stable carton assignment.

### 10.12 `improve.py`: Optional Bounded Improvement

Improvement starts only after a valid plan exists and must remain optional during the First Fit versus Best Fit baseline comparison.

For the initial strategy benchmark, improvement should be disabled so placement-strategy effects are not hidden by later optimization.

After the baseline comparison is complete, allowed bounded improvements may include:

1. a small fixed set of alternative item orders,
2. trying to remove the least-used carton by repacking its items into remaining cartons,
3. accepting a candidate only when it improves the shared objective order,
4. stopping immediately at the deadline,
5. always retaining the best already validated plan.

Tests verify that improvement never worsens the objective, deadline checks stop attempts, invalid candidates are rejected, carton elimination works on a constructed fixture, and tie resolution is stable.

### 10.13 `validate.py`: Independent Final Validator

For every final plan:

1. Every physical item appears exactly once across packed and unpacked outputs.
2. No unknown item appears.
3. Every packed orientation is permitted.
4. Every placement remains inside usable carton boundaries.
5. No two placements overlap.
6. Packed weight is at or below maximum weight.
7. Volume fill respects the configured threshold rule.
8. Clearance-adjusted dimensions are respected.
9. Carton count and result status are internally consistent.

The validator must not trust assumptions made by the placement or strategy modules. A plan failing validation cannot be returned with success status.

Each rule requires one passing test and one deliberately corrupted failing test.

### 10.14 `result.py`: Output Formatting

Required public result information:

| Level | Required fields |
| --- | --- |
| Order | order identifier, status, carton count, runtime, objective, placement strategy |
| Carton | code, usable dimensions, packed weight, used-space percentage |
| Placement | item identifier, source code, chosen orientation, x, y, z |
| Failure | unpacked physical items and reason where known |

Output must be JSON serializable without FastAPI or another framework.

Tests verify serialization, coordinate preservation, quantity traceability, strategy reporting, stable field names, no internal-object leakage, and correct runtime/status output.

## 11. Objective Ordering

All modules comparing complete plans use the same priority order.

| Priority | Comparison |
| ---: | --- |
| 1 | Valid plan beats invalid plan |
| 2 | Fewer cartons |
| 3 | Lower total external carton volume |
| 4 | Higher space utilization |
| 5 | Stable tie break by carton codes and placements |

## 12. Unit Testing Strategy

Unit tests are part of the product contract rather than final cleanup.

| Layer | Purpose | Normal CI |
| --- | --- | --- |
| Pure unit tests | One function or module contract | Yes |
| Component tests | Multiple internal functions within one component | Yes |
| End-to-end tests | `solve_order()` through full internal flow | Yes |
| Strategy-parity tests | Prove both strategies share the same candidate options and constraints | Yes |
| Regression fixtures | Known edge cases that previously failed | Yes |
| Benchmark comparison | Historical iHub records and runtime metrics | Separate benchmark job |

Required cross-cutting tests:

1. Same input and strategy produce the same output.
2. No returned successful placement contains overlap.
3. No placement exceeds carton boundaries.
4. Upright-only items preserve their vertical axis.
5. Packed weight never exceeds carton maximum.
6. Fill policy uses physical item count after quantity expansion.
7. One carton is always preferred over two valid cartons.
8. Unpackable items are reported rather than dropped.
9. Deadline exhaustion returns the best valid plan already found.
10. Final validation rejects a deliberately corrupted solver result.
11. Empty-space cleanup never leaves duplicate or fully contained spaces in constructed fixtures.
12. Placement search remains bounded by configured empty-space and candidate-position limits.
13. First Fit stops on the first valid candidate.
14. Best Fit evaluates the available valid candidates before selection.
15. Both strategies apply identical geometry and business constraints.

## 13. Development Sequence and Acceptance Gates

| Phase | Components | Acceptance gate |
| --- | --- | --- |
| 1 | models, normalize | Internal data contracts stable and normalization tests pass |
| 2 | orientation, geometry | Rotation, bounds, and overlap fully tested |
| 3 | feasibility | Impossible cartons safely removed |
| 4 | spaces | Empty-space creation, update, candidate-position generation, and cleanup tested |
| 5 | placement | Shared candidate engine passes constructed geometry fixtures |
| 6 | strategies | First Fit and Best Fit pass parity and selection tests |
| 7 | single_box | Smallest valid one carton selected reliably under both strategies |
| 8 | multi_box | Multiple-carton construction and failure handling work under both strategies |
| 9 | validate, result | Independent validation and stable output work |
| 10 | `solve_order()` | Full orchestrator and end-to-end tests pass |
| 11 | strategy benchmark | First Fit versus Best Fit runtime and packing tradeoff documented |
| 12 | improve | Bounded improvement added only after baseline strategy comparison |
| 13 | final benchmark | Historical comparison and runtime profile documented |

No phase is complete only because code exists. Its functional contract and tests must pass first.

## 14. Benchmarking Against iHub

The historical iHub output is a reference benchmark rather than mathematical ground truth.

For every benchmark order, run First Fit and Best Fit independently with bounded improvement disabled.

Record:

| Metric | Purpose |
| --- | --- |
| Valid solution rate | Correctness baseline |
| Carton count | Primary optimization outcome |
| Average cartons per order | Overall carton consumption |
| Orders where Best Fit uses fewer cartons | Direct strategy benefit |
| Orders where First Fit uses fewer cartons | Detect regressions and unexpected behavior |
| Exact historical carton count match | Reference comparison |
| Total external carton volume | Secondary packing efficiency |
| Space utilization | Percentage of carton volume occupied by packed items |
| Median runtime | Typical speed |
| P95 runtime | Time within which 95% of orders finish |
| Maximum runtime | Difficult-case behavior |
| Runtime difference | Extra time paid for Best Fit |
| Item-count band | Identify where strategies diverge |
| Failure reason | Diagnose unsolved orders |

### 14.1 Primary comparison

The strategy comparison should answer:

> How much additional runtime does Best Fit require, and how often does that additional work reduce carton count or carton volume compared with First Fit?

Do not select the default strategy before this evidence exists.

### 14.2 Complexity bands

At minimum, compare outcomes by physical item count:

1. 1 to 3 items.
2. 4 to 6 items.
3. 7 to 10 items.
4. 11 to 15 items.
5. More than 15 items.

Additional bands may be added based on the observed v2 distribution.

### 14.3 Benchmark-led escalation rule

Do not add complex search techniques because they sound sophisticated. Add them only when benchmark evidence identifies a meaningful failure mode.

Escalation order:

1. Compare First Fit and Best Fit cleanly.
2. Tune deterministic item ordering.
3. Tune Best Fit scoring.
4. Tune candidate-position generation and safe empty-space limits.
5. Try several fixed starting orders only if needed.
6. Consider seeded randomized trials if fixed alternatives are insufficient.
7. Consider changing earlier placements through backtracking only for a clearly identified difficult subset.
8. Consider parallel search only if search quality is good but runtime is the bottleneck.

Every escalation requires its own tests and benchmark comparison.

## 15. MVP Boundaries

Included: rectangular items, configurable carton catalogue, quantity expansion, orientation restrictions, carton clearance, weight limits, fill limits, remaining-empty-space-based placement, First Fit baseline, Best Fit comparison, multiple-carton packing, explicit XYZ coordinates, repeatable rule-based strategies, independent validation, and benchmark measurement.

Not included initially: arbitrary-angle rotation, deformable products, center-of-gravity optimization, support ratio, crush resistance, fragile-item stacking rules, load-bearing physics, robotic insertion planning, 3D-grid arbitrary-shape packing, randomized search, or guaranteed mathematically best packing.

## 16. Definition of Done

The MVP is functionally complete when `solve_order()` can process the agreed iHub-shaped inputs, run either First Fit or Best Fit through the same shared geometry engine, produce repeatable and independently validated single- or multiple-carton results, return XYZ placements and unpacked items where appropriate, pass the full automated test suite, and document the measured First Fit versus Best Fit tradeoff on the representative benchmark dataset.

Implementation decisions that change any functional behavior described here must update this specification first, then update tests, then update code.
