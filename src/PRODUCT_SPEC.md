# 3D Bin Packing Product Specification

## 1. Purpose and ownership

`bin_packing_3d` is a reusable orchestration layer for interchangeable 3D cartonization solvers. Normal users call:

```python
from bin_packing_3d import solve_order
result = solve_order(order=order, boxes=boxes, config={"strategy": "first_fit"}, trace=False)
```

The governing principle is: **solvers propose packing plans; the engine validates, measures, and returns them.** A future API must call this same function rather than duplicate packing rules.

### Engine responsibilities

The engine owns input normalization, configuration, quantity expansion, deterministic common rules, inexpensive individual-item feasibility, optional human-readable tracing, solver lookup, external runtime measurement, independent final validation, common metrics, and JSON-compatible results.

### Solver responsibilities

A registered solver receives normalized `PhysicalItem`, `Box`, and `PackingConfig` objects and returns a standard `PackingPlan`. It owns item sequencing, candidate positions, empty-space representation, placement scoring, carton choice, backtracking, and search termination. First Fit, Best Fit, and future strategies are independent plugins; this package layer neither implements nor automatically chains them.

Validity always precedes optimization. Solvers should optimize `bins_number`: fewer cartons, then lower total external carton volume, then utilization, with deterministic ties. Different valid geometry is acceptable.

## 2. Input and configuration

Each item requires `Code`, positive `Length`, `Width`, `Height` (mm), positive unit `Weight` (kg), positive integer `Quantity`, and boolean/0-or-1 `VerticalRotation`; `UOM` is optional. Preserve supplied `OrderId` and `OrderNo`. Each catalogue carton requires `Code`, positive dimensions, and positive `MaxWeight`; the catalogue is input, never hard-coded.

Defaults are:

```python
{
    "strategy": "first_fit",
    "max_fill_pct": 100,
    "high_item_count_threshold": 6,
    "high_item_count_max_fill_pct": 70,
    "bin_buffer": {"length": 0, "width": 0, "height": 6},
    "max_runtime_ms": 900,
    "deterministic": True,
}
```

`strategy` resolves exactly one registered solver. Invalid strategy names, percentages, thresholds, runtimes, negative buffers, and non-finite numeric values are errors, not values to repair. Buffer is subtracted from each corresponding carton dimension; non-positive usable dimensions are invalid. External dimensions remain unchanged for external-volume metrics.

`max_runtime_ms` is the search budget communicated to the selected solver. Search termination belongs to the plugin: the engine measures elapsed solver runtime consistently but does not forcibly interrupt plugin code. Solver implementations must observe the budget if they promise time-bounded search.

`max_fill_pct` is the blanket maximum for every carton. When the expanded physical item count is greater than `high_item_count_threshold`, the effective maximum is the smaller of `max_fill_pct` and `high_item_count_max_fill_pct`. At or below the threshold, the effective maximum is `max_fill_pct`. Thus the defaults permit up to 100% for six or fewer physical items and up to 70% for seven or more. Percentages are maximums against **usable** carton volume, not utilization targets. Quantity expansion occurs before selecting this limit, so one input row with `Quantity=7` counts as seven items.

## 3. Shared domain contract

`Quantity` is expanded deterministically into traceable instances such as `SKU123#1`. Models cover source and physical items, cartons, orientations, XYZ positions, placements, individual packed carton instances, plans, configuration, structured validation errors, metrics, and results.

A `PackingPlan` includes packed carton instances and their placements plus explicit unpacked physical-item identifiers. It contains sufficient information to validate a proposal without solver internals. Accounting validation permits explicit unpacked identifiers so failures can be diagnosed, but the normal `solve_order()` path succeeds only when every individually feasible item is packed. Until a separate partial-result contract is introduced, any unpacked item causes `InvalidPackingPlanError` rather than a misleading `status="success"`. `PackingResult.to_dict()` must be JSON serializable and includes order identifiers, status, strategy, cartons, placements, unpacked items, validation, runtime, and metrics.

## 4. Orientations and feasibility

With `VerticalRotation = true`, generate each unique axis-aligned orientation in this stable order:

```text
L × W × H, W × L × H, L × H × W,
H × L × W, W × H × L, H × W × L
```

With `VerticalRotation = false`, original height stays on Z and only `L × W × H` and `W × L × H` are allowed. Duplicates are removed. The exact visual is in [`../docs/images/exact_vertical_rotation_orientations.png`](../docs/images/exact_vertical_rotation_orientations.png).

Before solver invocation, every physical item must pass weight and oriented-dimension checks against at least one usable carton. Total order volume or weight cannot prove failure because multiple cartons are allowed. For example, `30 × 10 × 20` cannot fit a `20 × 20 × 20` carton despite any misleading aggregate-volume reasoning. Multi-item feasibility remains the solver's job.

## 5. Plugin architecture and flow

```text
raw request → normalize and validate → expand quantity → individual feasibility
→ resolve registered strategy → time and call solver → receive PackingPlan
→ independently validate → calculate common metrics → return PackingResult
```

The minimal protocol is:

```python
class PackingSolver(Protocol):
    name: str
    def solve(self, items: list[PhysicalItem], boxes: list[Box],
              config: PackingConfig) -> PackingPlan: ...
```

Registration is explicit and duplicate names are rejected unless replacement is deliberately requested. The package currently provides built-in `first_fit` and `best_fit` strategies. Both use the shared axis-aligned 3D candidate-placement functions in `placement.py`; strategy code decides how candidates are selected.

### Explainability trace

`solve_order(..., trace=True)` prints the normalized screening path while still returning the normal validated result. Tracing must never change solver decisions.

For a single physical item, candidate cartons are inspected in ascending external-volume order. The trace shows total item count and volume, usable carton dimensions after buffer, effective volume cap, weight eligibility, each allowed orientation, dimensional failures by L/W/H, and the first feasible carton. This makes the smallest-feasible-carton behavior directly inspectable.

For multiple physical items, aggregate volume is only a necessary condition. A trace must not claim that volume alone proves the items can coexist. Detailed multi-item placement tracing is a separate layer.

## 6. Independent final validation

The validator independently checks:

1. every expanded item appears exactly once as packed or explicitly unpacked;
2. unknown, missing, duplicated, and conflicting item states;
3. item code and allowed orientation, including upright-only behavior;
4. non-negative XYZ coordinates and usable carton boundaries;
5. axis-aligned cuboid non-overlap (touching faces, edges, or corners is allowed);\n6. summed item weight against carton `MaxWeight`;
7. the threshold-dependent fill cap against usable carton volume;\n8. unique carton instances, valid catalogue types, placement references, and configured usable dimensions.

It does not trust a solver validity flag or reuse solver placement-acceptance logic. A rejected plan cannot be returned as success.

A manually understandable valid geometry is a `20 × 20 × 20` carton with two `15 × 10 × 10` items side by side along the width. Overlapping them must fail; placing an item exactly on a boundary may pass, while crossing it must fail.

## 7. Metrics and runtime

The engine uses a monotonic high-resolution timer around the plugin call. This measurement is consistent across plugins; `max_runtime_ms` remains a solver search budget rather than an engine-enforced interruption deadline. Metrics include carton count, packed and unpacked counts, total packed item volume, total **external** carton volume, overall packed-volume/external-volume utilization, runtime milliseconds, and per-carton packed weight, volume, and usable-volume utilization. Benchmark aggregation stays outside `solve_order()`.

Later benchmarks may compare validity rate, carton count, volume, utilization, packed counts, median/P95 runtime, ties, improvement frequency, and overhead. Historical iHub layouts are reference results, not unique geometric truth. Do not claim First Fit versus Best Fit conclusions until both real plugins exist.

## 8. Package and testing

```text
src/bin_packing_3d/
  __init__.py  engine.py  models.py  rules.py
  placement.py validate.py solvers.py strategies/
```

Engine tests use test-only fake solvers, never disguised production heuristics. Tests cover malformed inputs/configuration, quantity IDs, rotations, buffers, threshold boundaries, individual infeasibility, overlap/touching/boundaries, weight, fill, accounting, registry behavior, orchestration, invalid proposals, metrics, serialization, and a reusable solver contract. Built-in First Fit and Best Fit strategy tests must prove valid 3D plans and distinct selection semantics. Benchmark conclusions remain outside the production API and belong in notebooks or benchmark tooling.
