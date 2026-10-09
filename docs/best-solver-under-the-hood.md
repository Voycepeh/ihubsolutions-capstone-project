# Google OR-Tools CP-SAT: Under the Hood

This note expands on the **Best** solver implementation for engineers who want to understand the Google OR-Tools Constraint Programming Satisfiability (CP-SAT) integration.

For the overall solver flow, inputs, configuration, and Fast versus Best behavior, see the project README.

## Where to look

The exact-assisted implementation is:

```text
src/bin_packing_3d/strategies/best.py
```

OR-Tools is a local Python dependency:

```text
ortools==9.10.4067
```

There is no Google-hosted API call. The CP-SAT model is created and solved inside the application process.

## What Best mode actually does

Best first runs Fast and keeps that result as its fallback and upper bound:

```python
incumbent = FastFitSolver().solve(items, boxes, config)
incumbent.metadata.update({
    "optimality_proven": False,
    "search_status": "time_limit",
    "best_result_source": "fast_fallback",
})
max_count = len(incumbent.packed_boxes)
```

It then tries carton combinations starting from one carton up to the number already used by Fast.

The carton objective is handled by the order in which our Python code tests combinations:

```python
for carton_count in range(1, max_count + 1):
    choices = sorted(
        combinations_with_replacement(boxes, carton_count),
        key=lambda choice: (
            sum(box.external_volume for box in choice),
            tuple(box.code for box in choice),
        ),
    )
```

The priority is **fewest cartons, then lowest total external carton volume**. For example, 25 L + 5 L beats 20 L + 15 L at the same carton count. Equal counts and total volumes tie on the business objective; carton codes only make the iteration order deterministic.

So CP-SAT is **not choosing the carton catalogue itself**.

Our code selects one candidate carton combination. CP-SAT answers:

> Can all physical items be placed inside this exact carton combination without breaking the packing constraints?

Before building the CP-SAT model, obviously impossible combinations are skipped using volume, weight, and individual-item fit checks:

```python
if not self._passes_aggregate_checks(items, choice, config):
    continue

plan, status = self._solve_choice(items, choice, config, deadline)
```

## What we give CP-SAT

The raw order JSON is not passed to OR-Tools.

By the time `_solve_choice()` runs, the application has already converted the request into:

```text
PhysicalItem[]
candidate Box tuple
PackingConfig
deadline
```

The method then translates those objects into CP-SAT integer and Boolean variables and constraints.

### 1. XYZ position and rotated dimensions

For every physical item:

```python
x = model.NewIntVar(0, max_l, f"x{index}")
y = model.NewIntVar(0, max_w, f"y{index}")
z = model.NewIntVar(0, max_h, f"z{index}")

dx = model.NewIntVar(1, max_l, f"dx{index}")
dy = model.NewIntVar(1, max_w, f"dy{index}")
dz = model.NewIntVar(1, max_h, f"dz{index}")
```

`x, y, z` are the item's position.

`dx, dy, dz` are its dimensions after rotation.

Dimensions are multiplied by 1000 because CP-SAT works with integer variables.

### 2. Allowed rotations

The model cannot invent arbitrary rotations.

It receives only the orientations allowed by our own rotation rules:

```python
model.AddAllowedAssignments(
    [dx, dy, dz],
    [
        (
            round(orientation.length * scale),
            round(orientation.width * scale),
            round(orientation.height * scale),
        )
        for orientation in allowed_orientations(item)
    ],
)
```

This is where the application's `VerticalRotation` policy reaches the exact solver.

### 3. Which carton contains each item

For each item, one Boolean is created for each carton in the candidate combination:

```python
assigned = [
    model.NewBoolVar(f"a{index}_{box_index}")
    for box_index in range(len(choice))
]

model.AddExactlyOne(assigned)
```

Every physical item must therefore belong to exactly one carton.

### 4. Stay inside the carton

If an item is assigned to a carton, its final XYZ position plus rotated dimensions must remain within that carton's usable dimensions:

```python
model.Add(x + dx <= length).OnlyEnforceIf(assigned[box_index])
model.Add(y + dy <= width).OnlyEnforceIf(assigned[box_index])
model.Add(z + dz <= height).OnlyEnforceIf(assigned[box_index])
```

The usable dimensions already account for the configured carton buffer.

### 5. Weight and fill

Each carton receives the same weight and fill restrictions used by the application:

```python
model.Add(
    sum(
        weights[i] * assignments[i][box_index]
        for i in range(len(items))
    )
    <= round(box.max_weight * weight_scale)
)

model.Add(
    sum(
        volumes[i] * assignments[i][box_index]
        for i in range(len(items))
    ) * 100
    <= round(length * width * height * fill_pct)
)
```

The active fill percentage is calculated before this from the shared packing configuration.

### 6. Items cannot overlap

For every pair of items that may share a carton, six possible separation directions are created.

Conceptually:

```text
A left of B
B left of A

A in front of B
B in front of A

A below B
B below A
```

The implementation requires at least one of these relationships when both items are assigned to the same carton:

```python
model.Add(
    sum(directions)
    >= assignments[left][box_index]
    + assignments[right][box_index]
    - 1
)

model.Add(xs[left] + dxs[left] <= xs[right]).OnlyEnforceIf(directions[0])
model.Add(xs[right] + dxs[right] <= xs[left]).OnlyEnforceIf(directions[1])
model.Add(ys[left] + dys[left] <= ys[right]).OnlyEnforceIf(directions[2])
model.Add(ys[right] + dys[right] <= ys[left]).OnlyEnforceIf(directions[3])
model.Add(zs[left] + dzs[left] <= zs[right]).OnlyEnforceIf(directions[4])
model.Add(zs[right] + dzs[right] <= zs[left]).OnlyEnforceIf(directions[5])
```

This is the main 3D packing constraint. Volume alone is not enough. CP-SAT must find actual XYZ positions where the cuboids do not intersect.

## Calling the solver

Once the model is built:

```python
solver = cp_model.CpSolver()

remaining_seconds = deadline - perf_counter()
solver.parameters.max_time_in_seconds = max(0.001, remaining_seconds)
solver.parameters.num_search_workers = 1 if config.deterministic else 8
solver.parameters.random_seed = 0

status = solver.Solve(model)
```

Only the remaining Best-mode runtime budget is given to CP-SAT.

A feasible result is then translated back into the project's own `PackingPlan`, `Placement`, `Orientation`, and `Position` objects.

The engine validates that plan separately before returning it to the caller.

## Solver outcomes

The integration treats CP-SAT outcomes simply:

| CP-SAT outcome | What Best does |
| --- | --- |
| Feasible or optimal for this carton choice | Build and return the packing plan |
| Infeasible | Try the next carton combination |
| Unknown or time exhausted | Return the Fast fallback |

A Best timeout therefore does **not** mean packing failed. It means exact search did not finish within the configured budget.

## Important warnings

**CP-SAT runs locally.** No order payload is uploaded to a Google optimization service by this implementation.

**The runtime limit is not a hard process timeout.** The remaining budget is passed to `solver.Solve()`; Python time spent constructing the model has already occurred.

**Large orders are more expensive.** Non-overlap constraints are created for item pairs and candidate cartons, so model size grows quickly as the number of physical items increases.

**Do not bypass the final validator.** A CP-SAT feasible status is translated into a project `PackingPlan`, which is still independently validated by the engine.

**Keep OR-Tools behind this boundary.** Callers should depend on `solve_order()` and project domain objects, not CP-SAT variables or raw solver objects.
