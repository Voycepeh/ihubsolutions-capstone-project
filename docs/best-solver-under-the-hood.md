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

### 3. Give CP-SAT the packing problem

CP-SAT is Google's general constraint and optimization engine. We describe the choices it can make and the rules it must obey. It searches for values that satisfy those rules.

For one chosen carton combination, our application asks:

> Can these items fit inside these cartons, respecting rotation, weight, fill and clearance?

#### What exactly goes into CP-SAT?

Our code converts the order and selected cartons into a mathematical model:

| Part | What our model gives CP-SAT |
| --- | --- |
| Item information | Each physical unit's dimensions, weight and allowed rotations |
| Selected cartons | A fixed combination, such as one Box4 or two Box2 cartons |
| Unknowns to calculate | Each item's carton assignment, rotation and XYZ position |
| Rules | Every item assigned once; inside boundaries; no overlap; weight and fill limits |
| Search settings | Remaining time budget, worker count and random seed |

The item data and carton capacities become constants in the model. The choices become variables, and the packing rules become constraints. Our code builds a `CpModel`, then calls:

```python
status = solver.Solve(model)
```

The library runs locally inside the application process. Our implementation sends no request to a Google service.

#### How does it calculate the arrangement?

Consider two items measuring **60 × 40 × 30 mm** and one carton with usable dimensions **100 × 80 × 30 mm**. For this illustration, assume these orientations are allowed, weight capacity is sufficient, and the fill limit is 100%.

We let CP-SAT choose each item's position, while enforcing:

```text
x + item_length ≤ carton_length
y + item_width  ≤ carton_width
z + item_height ≤ carton_height
```

Positions must also be nonnegative. Every item must belong to exactly one carton. For each pair in the same carton, at least one separation must hold: one item is to the left, right, front, back, above or below the other.

One valid answer for this example is:

| Item | Position (x, y, z), mm | Dimensions, mm |
| --- | --- | --- |
| A | (0, 0, 0) | 60 × 40 × 30 |
| B | (0, 40, 0) | 60 × 40 × 30 |

Their combined width is 80 mm, so both fit without overlap. Their combined volume fills 60% of the usable carton. This is an illustrative arrangement, rather than a recorded solver run.

Conceptually, CP-SAT narrows possible values using the rules, explores remaining choices and abandons branches that lead to contradictions. It returns an assignment satisfying all constraints, proves that none exists, or stops without an answer when its budget expires.

CP-SAT uses integer variables. Our code multiplies dimensions by 1,000 before solving and converts the resulting positions and dimensions back afterwards.

#### Where does the optimization happen?

**Our current CP-SAT model has no `Minimize()` objective.** We use it to answer a feasibility question for each fixed carton combination.

Our Python code handles carton optimization by testing combinations in priority order:

1. Fewest cartons first.
2. Within that count, lowest total external carton volume first.
3. Ask CP-SAT whether each combination can accommodate all items.

If all earlier combinations are ruled out, the first feasible combination establishes the best carton objective. Without an objective inside the model, CP-SAT can stop at the first valid arrangement for that combination.

| Our Python code | CP-SAT |
| --- | --- |
| Chooses which carton combination to test next | Calculates item assignments, rotations and positions |
| Prioritizes fewer cartons and lower total volume | Enforces the mathematical packing constraints |
| Manages the shared deadline and Fast fallback | Reports feasible, infeasible or unresolved |

CP-SAT can optimize an objective directly. Our current design achieves carton optimization through ordered feasibility checks.

For Google's explanation of the modeling interface, see [CP-SAT variables, constraints and solver statuses](https://developers.google.com/optimization/cp/cp_solver) and [adding an optimization objective](https://developers.google.com/optimization/cp/cp_example).

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
