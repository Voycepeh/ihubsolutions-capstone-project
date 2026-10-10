# Fast Solver: Under the Hood

This note expands on the **Fast** solver for engineers who want to understand how the greedy heuristic produces a valid 3D packing.

For the overall solver flow, inputs, configuration, and Fast versus Best behavior, see the project README.

## Where to look

The Fast implementation is:

```text
src/bin_packing_3d/strategies/fast.py
```

Shared 3D placement generation is in:

```text
src/bin_packing_3d/placement.py
```

Fast does not use OR-Tools. It is deterministic heuristic search built from the project's own placement rules.

## What Fast actually does

Fast builds a greedy candidate, then makes a tightly bounded attempt to improve carton count. Among evaluated valid candidates, the comparison is **fewest cartons first, then lowest total external carton volume**:

\`\`\`python
baseline = self._build_candidate(items, boxes, config)
return baseline
\`\`\`

Fast places larger items first, preferring already-open cartons. If necessary, it opens the smallest feasible carton. It then tries at most 3 feasible carton combinations regardless of order size, with no improvement-stage time limit. The baseline is always the fallback. Benchmark runs are uncapped so the measured cost of the three attempts is visible. Best starts from Fast and performs further exact search. By default, Best has **5,000 milliseconds (5 seconds)** for its additional exact search after Fast completes. This is not a time limit on Fast itself. Fast does not exhaustively explore same-count carton combinations; its three attempts are limited to fewer-carton choices.

## Greedy packing

### 1. Place difficult items first

Items are ordered from larger to smaller:

```python
ordered = sorted(
    items,
    key=lambda item: (
        -item.volume,
        -max(
            item.source_item.length,
            item.source_item.width,
            item.source_item.height,
        ),
        item.instance_id,
    ),
)
```

Larger items normally have fewer valid spaces, so placing them earlier reduces the chance that small items fragment useful space first.

The final `instance_id` keeps ties deterministic.

### 2. Try cartons that are already open

For the next item, Fast asks `feasible_placements()` for every valid placement in every currently open carton:

```python
for box_index, (packed_box, box) in enumerate(opened):
    feasible = feasible_placements(
        item,
        packed_box,
        box,
        item_by_id,
        config,
    )
```

A returned placement has already passed the shared placement checks for orientation, carton boundary, collision, weight, and fill.

Fast scores every feasible position:

```python
score = (
    remaining,
    placement_envelope_volume(packed_box, candidate),
    candidate.position.z,
    candidate.position.y,
    candidate.position.x,
    candidate.orientation.height,
    candidate.orientation.width,
    candidate.orientation.length,
    box_index,
)
```

The important behavior is:

1. prefer less remaining carton volume
2. prefer a tighter occupied envelope
3. use stable XYZ, orientation, and carton tie breakers

The minimum score wins.

### 3. Open a carton only when required

If none of the open cartons can accept the item, Fast evaluates every carton type:

```python
for box in boxes:
    packed_box = PackedBox(
        box.code,
        instance_id,
        usable_dimensions(box, config),
    )

    candidates = feasible_placements(
        item,
        packed_box,
        box,
        item_by_id,
        config,
    )
```

For a new carton, the score is:

```python
score = (
    box.external_volume,
    remaining,
    box.code,
)
```

So Fast opens the smallest carton that has a valid 3D placement for the item.

This continues until every physical item is placed or the heuristic cannot produce a complete plan.

## Where the 3D placement comes from

Fast itself chooses among placements. The shared `placement.py` module generates the placements that are actually legal.

Conceptually, for each item it:

```text
takes the allowed orientations
finds candidate XYZ positions
rejects positions outside the usable carton
rejects collisions with already placed items
rejects weight or fill violations
returns the remaining feasible placements
```

Fast then ranks those valid options.

This separation is important: `fast.py` controls the heuristic search, while `placement.py` owns reusable placement feasibility.

## Fast versus Best

The key implementation difference is small:

| Fast | Best |
| --- | --- |
| Uses `feasible_placements()` and scoring | Uses CP-SAT for fixed-carton feasibility |
| Commits to heuristic placements | Solver can search alternative XYZ arrangements |
| Bounded greedy improvement | Enumerates candidates until proof or timeout |
| Does not prove optimality | Can prove the selected carton objective |
| No OR-Tools dependency | Uses local OR-Tools CP-SAT |
| Used as Best's fallback | Starts from the Fast result |

Best can repair greedy carton-choice or geometry traps that Fast cannot.

## Important warnings

**Fast is deterministic but not exact.** The same input and configuration should follow the same decisions, but a valid result is not proof that no better packing exists.

**A locally good placement can block a better later arrangement.** Fast commits as it progresses and does not backtrack through every possible XYZ arrangement.

**Fast only attempts a small number of alternative carton combinations.** Best performs further exact carton-count optimization.

**Do not duplicate placement rules in Fast.** Rotation, collision, boundary, fill, and weight feasibility belong in the shared placement and rule layers.

**Do not bypass the final validator.** The engine independently validates the completed `PackingPlan` before returning it.

## Ranking valid packing plans

For valid candidates, Fast compares `(carton_count, total_external_carton_volume)`. A two-carton solution using 25 L + 5 L (30 L total) outranks 20 L + 15 L (35 L total), even though its largest individual carton is bigger. Equal counts and equal totals tie. This ranking applies to candidates Fast actually evaluates; it does **not** mean Fast searches every same-count combination.
