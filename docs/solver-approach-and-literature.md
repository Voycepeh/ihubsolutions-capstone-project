# Solver Approach and Literature Rationale

## Project Direction

The project will build a lightweight heuristic 3D cartonization solver.

The primary objective is to minimize the number of cartons used while ensuring that every returned packing is physically valid and satisfies the supplied operational constraints.

Rather than treating cartonization as a volume only problem, the solver separates the problem into two decisions:

1. Which carton should be tried?
2. Can the items physically fit inside that carton?

This distinction is important because the available cartons have different dimensions and aspect ratios. A carton may have sufficient total volume but still be unable to contain an item or group of items geometrically.

## 1. Bin Selection Strategy

The project will initially compare three simple bin selection heuristics.

### First Fit

Try existing cartons in order and place the item into the first carton where a valid 3D placement can be found.

If no existing carton can accept the item, open a suitable new carton.

### Best Fit

Evaluate the cartons where a valid placement exists and choose the carton that leaves the least remaining usable capacity.

This aims to improve carton utilization.

### Worst Fit

Evaluate the cartons where a valid placement exists and choose the carton that leaves the most remaining usable capacity.

This spreads items across available space and provides a useful comparison against First Fit and Best Fit.

The three strategies will use the same constraint and geometry engine so their results can be compared fairly.

## 2. 3D Placement Strategy

Bin selection alone is not enough.

For every candidate carton, the solver must determine whether the items can actually be positioned inside it without overlap.

A practical constructive approach is:

**Largest or hardest item first → lowest available placement position → try permitted orientations → validate → place → repeat**

Instead of checking every possible XYZ coordinate, the solver will test meaningful candidate positions generated from previously placed items.

For example, when an item is placed, new candidate positions may be created beside or above its exposed faces.

This keeps the search finite while still producing a genuine 3D packing.

## Volume Is a Filter, Not the Solver

Total volume is useful as an inexpensive rejection test.

However:

`total item volume <= carton volume`

does not prove that a packing exists.

For example, a long thin item may have very low volume but still be too long for every orientation of a particular carton.

The solver must therefore check actual dimensions, orientation and spatial placement after the volume test.

Similarly, two remaining spaces with the same volume may have very different usefulness because their shapes are different.

## Item Ordering

A common constructive heuristic is to place difficult items before easier items.

The initial baseline can use decreasing item volume because it is simple and reproducible.

However, volume alone may not represent packing difficulty well. A long thin item can be more difficult to place than a compact item with greater volume.

The project can therefore compare alternative ordering strategies such as:

* Volume descending
* Longest dimension descending
* Largest face area descending
* Rotation restricted items first

These strategies can be evaluated empirically against the supplied orders rather than assuming one definition of "largest" is always best.

## Packing Constraints

A placement is valid only when all relevant constraints pass:

* 3D dimensions and carton boundaries
* Permitted item orientation
* No overlap with already packed items
* Maximum carton weight
* Configurable carton fill limit
* Configurable carton buffer or clearance

The bin selection heuristic should never consider a carton feasible merely because sufficient volume remains.

## Initial Solver Flow

```text
Order
  ↓
Expand quantities
  ↓
Order items
  ↓
Try candidate carton
  ↓
Generate candidate 3D positions
  ↓
Try permitted orientations
  ↓
Validate geometry and constraints
  ↓
Place item
  ↓
Repeat
```

The carton selection step can independently use:

```text
First Fit
Best Fit
Worst Fit
```

while all three strategies share the same 3D placement engine.

## Evaluation

The supplied solved orders allow the project to compare the different strategies using the same benchmark.

The initial experiment should compare:

* Largest First + First Fit
* Largest First + Best Fit
* Largest First + Worst Fit

Key measures include:

| Measure | Purpose |
| --- | --- |
| Packing success | Whether all items can be packed |
| Cartons used | Primary optimization objective |
| Reference carton count | Comparison with supplied iHub result |
| Space utilization | Secondary packing quality |
| Constraint violations | Packing correctness |
| Runtime | Practical performance |

Further experiments can change the item ordering while keeping the placement engine unchanged.

This gives the project a modular experimental framework where individual heuristics can be compared without rewriting the complete solver.

## Literature Rationale

Research on 3D bin packing shows that exact optimization is computationally difficult and that constructive heuristics are widely used to obtain practical feasible solutions.

Martello, Pisinger and Vigo describe the three dimensional bin packing problem and exact approaches to minimizing bin count.

Lodi, Martello and Vigo demonstrate heuristic approaches for three dimensional bin packing.

Crainic, Perboli and Tadei show the importance of candidate placement locations through extreme point based heuristics.

These works support the project's decision to use a constructive geometric packing approach while experimentally comparing simple carton selection and item ordering heuristics.

The project does not claim that the resulting packing is globally optimal for every possible instance. Instead, it aims to produce valid, fast and explainable packing decisions and measure their quality against the supplied benchmark.

## References

1. Martello, S., Pisinger, D., & Vigo, D. (2000). The Three-Dimensional Bin Packing Problem. *Operations Research, 48*(2), 256 to 267. https://doi.org/10.1287/opre.48.2.256.12386
2. Lodi, A., Martello, S., & Vigo, D. (2002). Heuristic algorithms for the three-dimensional bin packing problem. *European Journal of Operational Research, 141*(2), 410 to 420. https://doi.org/10.1016/S0377-2217(02)00134-0
3. Crainic, T. G., Perboli, G., & Tadei, R. (2008). Extreme Point-Based Heuristics for Three-Dimensional Bin Packing. *INFORMS Journal on Computing, 20*(3), 368 to 384. https://doi.org/10.1287/ijoc.1070.0250
