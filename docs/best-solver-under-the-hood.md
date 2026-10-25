# Best Solver: Under the Hood

**Best completes Fast first, then searches for a better packing using Google OR-Tools CP-SAT.** It keeps Fast's result as its fallback while checking alternative carton combinations and item arrangements.

The objective is **fewer cartons first, then lower total external carton volume**. Best can prove that objective when it finishes the required search. A time limit can stop it before proof is available.

[Project overview](../README.md) · [How Fast works](fast-solver-under-the-hood.md)

## How Best searches an order

### 1. Keep Fast's packing as the baseline

Best runs the full [Fast process](fast-solver-under-the-hood.md), including its bounded improvement stage. That gives it a packing to return if the additional search runs out of time.

The baseline also sets the maximum carton count to search. If Fast used three cartons, Best checks combinations using one, two and three cartons.

### 2. Try carton combinations in priority order

The application selects the carton combinations. It starts with the fewest cartons, then sorts combinations of that count by total external volume, smallest first.

For example, at the same carton count, 25 L + 5 L outranks 20 L + 15 L because the total is 30 L rather than 35 L. Carton codes break ties consistently when count and total volume are equal.

Before doing detailed geometry work, Best skips combinations that lack enough total usable volume or weight capacity, or that cannot fit an individual item in any chosen carton. Passing these checks means the combination is worth investigating; it does not establish a valid packing.

### 3. Ask whether each combination really fits

For one chosen combination, CP-SAT answers:

> Can every physical item be assigned a carton, an allowed rotation and an XYZ position while satisfying all packing rules?

CP-SAT is a constraint solver: we describe the allowed choices and rules, and it searches for values that satisfy them. It runs locally inside the application process.

| Choice or rule | What the solver must establish |
| --- | --- |
| Carton assignment | Each physical item belongs to exactly one carton. |
| Rotation | Each item uses an allowed orientation, including upright restrictions. |
| Position | Each item has an XYZ position inside its assigned carton's usable dimensions. |
| Weight | Items assigned to a carton stay within its weight limit. |
| Fill | Their combined volume stays within the active fill limit. |
| No overlap | Items sharing a carton remain separated in at least one axis direction. |

For example, two items may fit side by side, one in front of the other, or one above the other. At least one such separation must hold for every pair sharing a carton. Having enough total volume alone does not establish that their shapes fit together.

### 4. Return a packing or move to the next combination

| Search outcome | What Best does |
| --- | --- |
| A valid arrangement is found | Converts it to a project packing plan; returns it if its carton objective is equal to or better than Fast's. |
| The combination is proven impossible | Tries the next combination. |
| Search ends without an answer, or the deadline is reached | Returns the Fast baseline without claiming optimality. |

The first feasible combination can establish the best carton objective because earlier, higher-priority combinations have already been ruled out. The Python search order establishes that objective; CP-SAT solves the geometry for each fixed choice.

The engine independently validates the selected plan before returning it to the caller.

## What the five-second budget means

By default, Best has **five seconds of additional search after Fast finishes**. All candidate combinations share that budget; each combination does not receive a fresh five seconds.

```python
result = solve_order(
    order=order,
    boxes=boxes,
    mode="best",
    max_runtime_ms=5_000,
)
```

A caller can change `max_runtime_ms` or set it to `None` to remove the search deadline.

This is a search budget, rather than a hard process timeout. Fast completes first, and Python work such as enumerating combinations and constructing models can make total API time longer. Each CP-SAT call receives the time remaining after earlier search work.

A timeout can still produce a valid recommendation: Best returns its Fast baseline. It means the additional search did not finish, rather than that the order cannot be packed.

## What “optimal” means here

**Optimality concerns carton count and total external carton volume.** It does not mean that the solver found a unique arrangement or the easiest arrangement for a person to pack.

| Result field | How to read it |
| --- | --- |
| `optimality_proven=True` | Best completed the search needed to prove the selected carton objective. |
| `optimality_proven=False` | The returned packing has no completed optimality proof. |
| `best_result_source="best_calculation"` | The returned arrangement came from the exact search; it may tie Fast's objective. |
| `best_result_source="fast_fallback"` | The returned arrangement came from Fast. Check the proof and status fields separately. |
| `search_status="time_limit"` | Search returned the baseline without completing proof. This also covers an unknown solver outcome. |
| `validation` | The independent check of the returned packing. |

In the implementation's completed-search path, Best can retain Fast's arrangement and mark its objective as proven. The source field describes where the arrangement came from; the proof field describes what the search established.

## Why Best takes longer

Best does all of Fast's work, then explores alternatives. More carton types create more combinations to check. More physical items create more assignments, rotations, positions and pairs that must be kept apart.

That extra work lets Best escape choices that trap a greedy heuristic. The time budget gives callers control over how long to spend on that search.

<details>
<summary>Implementation reference: CP-SAT model and source files</summary>

The integration is in [`BestFitSolver`](../src/bin_packing_3d/strategies/best.py). It uses the local `ortools==9.10.4067` dependency; this implementation sends no order payload to a Google optimization service.

The application passes normalized physical items, a fixed carton combination, packing configuration and a shared deadline into `_solve_choice()`.

| Model element | Implementation |
| --- | --- |
| Position | Integer variables `x`, `y`, `z` for each item |
| Rotated dimensions | `dx`, `dy`, `dz`, restricted with `AddAllowedAssignments()` to permitted orientations |
| Assignment | One Boolean per item and candidate carton, with `AddExactlyOne()` |
| Boundary | Position plus rotated dimension cannot exceed the assigned carton's usable size |
| Capacity | Assignment-weighted sums enforce carton weight and fill limits |
| Separation | Six Boolean directions per item pair and carton; at least one holds when both items share that carton |

Dimensions are multiplied by 1,000 and weights by 10,000 to represent them with integers. Extracted positions and dimensions are converted back to project units.

The deterministic setting uses one search worker; otherwise the integration uses eight. The random seed is zero. `FEASIBLE` and `OPTIMAL` both establish a feasible arrangement for a fixed carton choice; global carton ranking comes from the outer search order.

Solver values are translated into `PackingPlan`, `PackedBox`, `Placement`, `Orientation` and `Position` objects. Callers continue to use `solve_order()` and the project's result objects.

</details>
