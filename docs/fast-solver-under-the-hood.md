# Fast Solver: Under the Hood

This note expands on the **Fast** solver for engineers who want to understand how the bounded heuristic produces a valid 3D packing.

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

Fast builds a normal greedy candidate first and then makes a bounded attempt to use fewer cartons:

```python
baseline = self._build_candidate(items, boxes, config)

candidates = [
    baseline,
    self._search_fewer_cartons(
        items,
        boxes,
        config,
        len(baseline.packed_boxes),
    ),
]
```

Both paths use the same 3D placement generator. The difference is whether cartons are opened greedily as needed or pre-opened as a candidate combination.

Fast compares the completed candidates and keeps the better one:

```python
def score(plan):
    return (
        len(plan.unpacked_item_ids),
        len(plan.packed_boxes),
        max(carton_volumes),
        sum(carton_volumes),
    )
```

This means Fast prioritizes a complete packing, then fewer cartons, then smaller carton volume.

It remains a heuristic. It does not prove that a better arrangement is impossible.

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

## Bounded fewer-carton attempt

A purely greedy decision can create a trap.

For example, opening the smallest carton for an early item may later force a second carton even though one slightly larger carton could have held the whole order.

Fast therefore performs one additional bounded search:

```python
for carton_count in range(1, baseline_count):
    combinations = sorted(
        combinations_with_replacement(boxes, carton_count),
        ...
    )
```

It tries carton combinations with fewer cartons than the greedy baseline.

Before attempting 3D placement, combinations that fail total usable volume or weight capacity are skipped.

For each surviving combination, the cartons are pre-opened and the same large-first item sequence is placed greedily using `feasible_placements()`.

If a complete plan is found, it becomes a candidate.

This improves Fast without turning it into exhaustive search.

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
| Bounded fewer-carton improvement | Enumerates candidates until proof or timeout |
| Does not prove optimality | Can prove the selected carton objective |
| No OR-Tools dependency | Uses local OR-Tools CP-SAT |
| Used as Best's fallback | Starts from the Fast result |

This is why Best can repair a greedy geometry trap that Fast cannot, while Fast remains substantially cheaper.

## Important warnings

**Fast is deterministic but not exact.** The same input and configuration should follow the same decisions, but a valid result is not proof that no better packing exists.

**A locally good placement can block a better later arrangement.** Fast commits as it progresses and does not backtrack through every possible XYZ arrangement.

**The fewer-carton pass is still heuristic.** Pre-opening a promising carton combination helps with carton-choice traps, but item placement inside those cartons remains greedy.

**Do not duplicate placement rules in Fast.** Rotation, collision, boundary, fill, and weight feasibility belong in the shared placement and rule layers.

**Do not bypass the final validator.** The engine independently validates the completed `PackingPlan` before returning it.
