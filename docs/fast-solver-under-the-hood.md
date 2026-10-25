# Fast Solver: Under the Hood

**Fast builds a packing one item at a time, then tries up to three alternatives that could use fewer cartons.** It uses practical rules to make quick decisions, so it can find a valid packing without exploring every possible arrangement.

Both modes prefer **fewer cartons first, then lower total external carton volume**. Fast applies that ranking to the plans it actually finds; it cannot prove that its result is the best possible.

[Project overview](../README.md) · [How Best works](best-solver-under-the-hood.md)

## How Fast packs an order

### 1. Start with the largest items

The order has already been expanded into physical units: a quantity of three becomes three items to place.

Fast sorts those units by volume, largest first. For equal volumes, the item with the longest side goes first; an item identifier breaks any remaining tie consistently.

Large items usually have fewer places they can fit. Packing them early helps preserve useful space before small items fill it.

### 2. Try the cartons already in use

For each item, Fast checks the cartons it has already opened. It tries permitted rotations at candidate positions inside each carton.

Every candidate must satisfy the same rules:

| Check | What it means |
| --- | --- |
| Rotation | The item uses an orientation allowed by its rotation setting. |
| Boundary | The item stays inside the usable dimensions after carton clearance is removed. |
| Collision | The item does not overlap anything already packed. |
| Weight | The carton stays within its maximum weight. |
| Fill | The carton stays within the configured volume fill limit. |

If several placements work, Fast prefers the carton with the least volume left after placement. Within that preference, it chooses a compact arrangement, then uses consistent position and orientation tie breakers.

**If an open carton can accept the item, Fast uses it before considering a new carton.**

### 3. Open a new carton when needed

If no open carton works, Fast evaluates the carton catalogue. A carton must first have a valid placement for the current item.

It then estimates how many cartons of each type would be needed for the remaining items, using their combined volume and weight. The estimate accounts for the active fill limit. Fast prefers the type with the lower estimated carton count, then the smaller external volume when counts tie.

For example, suppose the remaining items have a total volume of 12 litres. With a 100% fill limit and no weight restriction, a 5 litre carton suggests three cartons, while an 8 litre carton suggests two. Fast favours the 8 litre type if the current item can be placed in it.

*This is an illustrative capacity estimate. Actual 3D fit still depends on item shapes, rotations and positions.*

Fast repeats these steps until it has placed every item or cannot place the next one.

### 4. Try up to three ways to use fewer cartons

If the initial packing is complete and uses more than one carton, Fast tries alternative carton combinations with fewer cartons.

It first skips combinations that cannot accommodate the total volume, total weight, or each item's dimensions. For combinations that pass, it repacks the items using its placement heuristic, with a preference for compact arrangements.

**At most three combinations that pass the initial checks are attempted.** This limit applies across the whole improvement stage. Screening a rejected combination does not consume an attempt.

Fast keeps the better complete plan, comparing carton count first and total external volume second. The initial packing remains the fallback. It does not systematically search alternatives with the same carton count.

## Where the positions come from

The shared placement code starts at the carton's origin. Each packed item adds candidate points immediately beside it along the length, width and height directions. The code tries allowed rotations at those points and rejects placements that break a rule.

This keeps the search manageable. It also explains Fast's limitation: it chooses among a restricted set of positions and commits to each placement as it proceeds. It does not revisit every earlier decision.

## What the result tells you

A complete Fast packing is a **heuristic result**: it is a candidate found through practical rules. The engine independently validates the selected plan before returning it.

| Result field | Meaning in Fast mode |
| --- | --- |
| `search_status="heuristic"` | Fast completed its heuristic search. |
| `optimality_proven=False` | A better packing may still exist. |
| `best_result_source="not_applicable"` | Best's exact search was not used. |
| `validation` | The independent check of the returned packing. |

Fast has no improvement-stage time deadline. The three-attempt limit bounds the number of repacking attempts, rather than guaranteeing a fixed response time. Best's default five-second search budget starts after Fast finishes.

## When Best can improve on Fast

An early placement can block a later item even when a different arrangement would fit. A quick capacity estimate can also favour a carton choice that turns out to be less efficient.

[Best](best-solver-under-the-hood.md) starts with Fast's result, then searches alternative carton combinations and item positions using an exact constraint solver.

<details>
<summary>Implementation reference: files and decision priorities</summary>

| Responsibility | Source |
| --- | --- |
| Initial packing and bounded improvement | [`FastFitSolver`](../src/bin_packing_3d/strategies/fast.py) |
| Candidate positions and placement feasibility | [`placement.py`](../src/bin_packing_3d/placement.py) |
| Rotation, clearance and fill policy | [`rules.py`](../src/bin_packing_3d/rules.py) |

The initial packing compares these priorities in order:

| Decision | Priority, highest first |
| --- | --- |
| Item order | Larger volume; longer maximum side; item identifier |
| Placement in an open carton | Less remaining usable volume; smaller occupied envelope; Z, Y, X; orientation height, width, length; carton index |
| New carton type | Fewer projected cartons; smaller external volume; less remaining usable volume; carton code |
| Completed plan | Fewer cartons; lower total external volume |

The occupied envelope is the smallest cuboid anchored at the carton origin that contains the placements. During bounded repacking, its volume is the first placement preference, followed by stable carton, position and orientation tie breakers.

The improvement loop enumerates carton combinations in catalogue order for each smaller carton count. It does not globally sort all combinations by total volume before applying the three-attempt limit.

</details>
