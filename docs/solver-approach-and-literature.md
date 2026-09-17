# Solver Approach and Literature Rationale

## Project Direction

The project will build a lightweight 3D cartonization solver that aims to find a good valid packing quickly rather than prove the mathematically best possible packing for every order.

The primary objective is to minimize the number of cartons used while respecting item dimensions, allowed rotation, carton weight, fill rules and configured clearance.

The solver separates the problem into two questions:

1. Which carton should be tried?
2. Can the items physically fit inside it without overlap?

Volume and weight can quickly reject impossible cartons, but they cannot prove that multiple rectangular items can actually be arranged inside the same carton.

## Technical Terms Used in This Page

Two packing terms are useful to name once because they appear in the literature.

**Empty Maximal Space** is the technical term for a useful rectangular region of empty space remaining inside a carton after items have been placed. From this point onward, this page calls it a **remaining empty space**.

**Extreme Point** is the technical term for a useful placement position created from carton boundaries or the faces of items already packed. From this point onward, this page calls it a **candidate position**.

A **heuristic** is a practical rule-based method that tries to find a good solution quickly without proving the mathematically best possible answer. From this point onward, this page generally uses **packing strategy** or **approach**.

See [`TERMINOLOGY.md`](TERMINOLOGY.md) for the shared repository terminology guide.

## 1. Shared 3D Placement Approach

The current product design uses one shared 3D placement engine for both First Fit and Best Fit.

The engine works with rectangular items placed only in allowed 90-degree orientations. It does not scan every possible XYZ coordinate. Instead, it keeps track of the remaining empty rectangular spaces in the carton and tests a bounded set of candidate positions around carton and packed-item boundaries.

For each item, the shared placement logic is:

1. Order harder items first.
2. List the item orientations that are allowed.
3. Look through the current remaining empty spaces.
4. Generate useful candidate positions.
5. Reject positions outside the carton.
6. Reject positions that overlap an item already packed.
7. Pass valid positions to the selected placement strategy.
8. Place the item.
9. Update the remaining empty spaces.
10. Remove duplicate, contained or unusable spaces.
11. Repeat for the next item.

This gives both strategies the same geometry and business rules so the comparison is fair.

## 2. First Fit and Best Fit

The initial experiment compares **First Fit** and **Best Fit** as placement-selection strategies, not as two different geometry engines.

### First Fit

First Fit accepts the first valid candidate position it encounters in the shared deterministic order.

Its purpose is to provide a simple low-search baseline. Because it stops once it finds a valid position, it should usually perform less work.

### Best Fit

Best Fit looks at the same valid candidate positions but continues evaluating them and chooses the preferred position using a fixed priority order.

The comparison should answer whether the additional search produces enough packing improvement to justify the added runtime.

### What is not part of the initial comparison

Worst Fit is not part of the current V1 experiment. Earlier planning considered it, but the selected product specification now focuses on First Fit versus Best Fit because that directly tests the expected speed-versus-packing-quality tradeoff.

Random search, simulated annealing, genetic algorithms, deep backtracking, parallel workers and voxel-based packing are also deferred until benchmark evidence shows that the simpler strategies are insufficient.

## 3. Why Volume Alone Is Not Enough

Total item volume is useful as a fast rejection check:

`total item volume <= allowed carton volume`

But that condition does not prove a packing exists.

For example, an item can have less volume than a carton and still be too long in every allowed orientation. Multiple items can also have enough total volume to fit while their shapes prevent a valid non-overlapping arrangement.

The solver must therefore check actual dimensions, allowed orientation and 3D placement after the volume test.

## 4. Item Ordering

Packing order matters because an early placement can make later items harder or easier to fit.

The initial deterministic order should prioritize harder items first, using the agreed product specification. The first version currently prioritizes restricted rotation, then larger volume, then larger longest dimension, with a stable item identifier as the final tie-break.

Other item orders can later be compared without changing the geometry engine, for example:

- larger volume first,
- longest dimension first,
- largest face first,
- rotation-restricted items first.

The choice should be benchmarked rather than assumed.

## 5. Packing Constraints

A placement is valid only when all required checks pass:

- item dimensions remain inside the usable carton dimensions,
- the chosen item orientation is allowed,
- the item does not overlap anything already packed,
- carton weight stays within the maximum,
- the configured fill rule is respected,
- the configured carton clearance is respected.

A carton should never be treated as valid merely because enough total volume remains.

## 6. Current Solver Flow

```text
Order + carton catalogue + configuration
  ↓
Validate and expand quantities
  ↓
List allowed item orientations
  ↓
Reject cartons that are definitely impossible
  ↓
Try one carton first, smallest suitable carton first
  ↓
Track remaining empty rectangular spaces
  ↓
Generate useful candidate positions
  ↓
Check boundaries and overlap
  ↓
First Fit: take first valid position
or
Best Fit: compare valid positions and choose preferred one
  ↓
Update remaining empty spaces
  ↓
Repeat until all items are packed
  ↓
If one carton fails, construct a multiple-carton plan
  ↓
Independently validate the result
```

## 7. Evaluation

The supplied solved iHub orders provide a common benchmark for the two strategies.

The initial experiment should run First Fit and Best Fit independently with later improvement logic disabled so the strategy difference is measured cleanly.

| Measure | Purpose |
| --- | --- |
| Valid solution rate | Whether all required items are packed correctly |
| Cartons used | Primary optimization outcome |
| Orders where one strategy uses fewer cartons | Direct strategy comparison |
| Total carton volume | Compare carton size when carton count is equal |
| Space utilization | Percentage of carton volume occupied by packed items |
| Median runtime | Typical speed |
| P95 runtime | Time within which 95% of orders finish |
| Maximum runtime | Difficult-case behavior |
| Runtime difference | Additional time paid for Best Fit |

The main experimental question is:

> How much additional runtime does Best Fit require, and how often does that additional search reduce carton count or carton volume compared with First Fit?

## 8. Literature Rationale

Research on three-dimensional bin packing shows that exact optimization can become computationally difficult as the number of items and possible arrangements grows. Practical systems therefore often use constructive packing strategies that build a solution one item at a time.

Martello, Pisinger and Vigo describe the three-dimensional bin packing problem and exact approaches to minimizing bin count.

Lodi, Martello and Vigo study practical strategies for three-dimensional bin packing.

Crainic, Perboli and Tadei study **Extreme Point-Based Heuristics**. In the language used by this project, the useful takeaway is to test meaningful **candidate positions** rather than every coordinate in the carton.

The project also reviewed `Xebet/3d-packing-simulator`, which demonstrates a practical implementation using remaining empty rectangular spaces, candidate placement positions, multiple orientations, overlap checks and independent validation. The project does not copy that implementation wholesale; it uses those established ideas as references for an independently developed Python solver with iHub-specific rules.

The MIT Scalable Spectral Packing work provides another useful conceptual comparison: order the objects, search for collision-free placements, score placement quality and repeat. Its voxel-grid and Fast Fourier Transform approach is aimed at more general 3D shapes and is therefore not selected for this rectangular-item MVP.

These sources support the current design choice: use a simple, explainable shared geometry engine first, compare First Fit and Best Fit experimentally, and add more complex search only when measured results justify it.

## References

1. Martello, S., Pisinger, D., & Vigo, D. (2000). The Three-Dimensional Bin Packing Problem. *Operations Research, 48*(2), 256 to 267. https://doi.org/10.1287/opre.48.2.256.12386
2. Lodi, A., Martello, S., & Vigo, D. (2002). Heuristic algorithms for the three-dimensional bin packing problem. *European Journal of Operational Research, 141*(2), 410 to 420. https://doi.org/10.1016/S0377-2217(02)00134-0
3. Crainic, T. G., Perboli, G., & Tadei, R. (2008). Extreme Point-Based Heuristics for Three-Dimensional Bin Packing. *INFORMS Journal on Computing, 20*(3), 368 to 384. https://doi.org/10.1287/ijoc.1070.0250
4. Xebet. *3d-packing-simulator*. GitHub repository: https://github.com/Xebet/3d-packing-simulator
5. MIT News. *Chore of packing just got faster and easier*. 2023. https://news.mit.edu/2023/chore-packing-just-got-faster-and-easier-0706
