# Solver Approach and Literature Rationale

## Project Direction

The project provides a lightweight 3D cartonization solver with a fast heuristic mode and an exact-assisted mode. Best proves the ordered carton objective when the configured time budget permits and otherwise returns a validated heuristic fallback without claiming proof.

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

## 1. Shared 3D Placement Approach

The solver first builds a fast valid plan with a deterministic scored-placement heuristic and bounded fixed-carton search. Best then spends the remaining budget testing carton combinations with an exact constraint model.

The shared one-carton engine works with rectangular items placed only in allowed 90-degree orientations. It tracks remaining empty rectangular spaces and tests useful candidate positions rather than scanning every XYZ coordinate.

The core placement loop is:

1. sequence physical items,
2. list allowed orientations,
3. try useful candidate XYZ positions,
4. reject boundary or overlap violations,
5. place the item,
6. update remaining empty spaces,
7. continue until the carton cannot accept more items.

The one-carton engine returns both the packed items and the remaining physical items. The full-order solver repeats this engine across cartons until nothing remains or an item is unpackable.

## 2. Fast Baseline and Exact-Assisted Best

### Fast baseline

Fast scores feasible placements in every open carton, opens the smallest suitable catalogue carton when needed, and tries promising fixed-carton combinations. The weaker first-placement-only implementation is no longer a production mode.

This gives the solver a fast, complete and validated fallback plan before any more expensive search begins.

### Best exact search

Best retains Fast, enumerates carton combinations by carton count, largest external carton volume, and total external carton volume, then uses CP-SAT to decide whether a complete orthogonal 3D packing exists.

The exact model covers allowed orientations, carton assignment, usable boundaries, pairwise non-overlap, weight, fill cap, and buffer-adjusted dimensions. The independent validator still checks every returned placement.

If the exact search reaches the runtime limit, the solver returns Fast with `optimality_proven=False` and `search_status="time_limit"`. When every better combination is proven infeasible, it returns `optimality_proven=True`.

The benchmark measures whether the additional proof time produces a material business improvement while staying within the latency target.

## 3. Why Volume Alone Is Not Enough

Total item volume is useful as a fast rejection check:

`total item volume <= allowed carton volume`

But that condition does not prove a packing exists.

For example, an item can have less volume than a carton and still be too long in every allowed orientation. Multiple items can also have enough total volume to fit while their shapes prevent a valid non-overlapping arrangement.

The solver must therefore check actual dimensions, allowed orientation and 3D placement after the volume test.

## 4. Item Ordering

Packing order matters because an early placement can make later items harder or easier to fit.

Fast currently orders by larger volume, then larger longest dimension, with a stable item identifier as the final tie-break. Best's exact model is not dependent on this item sequence.

Other item orders can later be compared without changing the geometry engine, for example:

1. larger volume first,
2. longest dimension first,
3. largest face first,
4. rotation-restricted items first.

The choice should be benchmarked rather than assumed.

## 5. Packing Constraints

A placement is valid only when all required checks pass:

1. item dimensions remain inside the usable carton dimensions,
2. the chosen item orientation is allowed,
3. the item does not overlap anything already packed,
4. carton weight stays within the maximum,
5. the configured fill rule is respected,
6. the configured carton clearance is respected.

A carton should never be treated as valid merely because enough total volume remains.

## 6. Current Solver Flow

The implementation roadmap is:

1. **MVP 1 — Fit one item:** prove orientation rules and smallest valid carton selection.
2. **MVP 2 — Pack one carton:** expand quantity into physical item instances and construct a valid 3D plan.
3. **MVP 3 — Pack the whole order:** create a complete validated heuristic baseline.
4. **MVP 4 — Improve and prove:** retain Fast, test better carton combinations with exact CP-SAT feasibility, and report proof or time-limited fallback status.

This gives the solver an anytime structure: a valid baseline is available first, then extra computation is spent only on potential improvement.

## 7. Evaluation

The benchmark compares production Fast with exact-assisted Best and the masked iHub reference results.

| Measure | Purpose |
| --- | --- |
| Valid solution rate | Correctness baseline |
| Cartons used | Primary optimization outcome |
| Total carton volume | Secondary objective when carton count is equal |
| Space utilization | Later tie break and diagnostic |
| Fast baseline runtime | Time to guaranteed valid fallback |
| Total runtime | Cost after improvement search |
| Orders with fewer cartons after improvement | Direct business benefit |
| Orders with smaller carton volume at equal carton count | Secondary business benefit |
| Orders with no material improvement | Extra search that did not change the business outcome |
| Timeout fallback count | How often the solver returned the existing best plan |

The main experimental question is:

> Does the additional exact Best search reduce carton count or carton volume often enough to justify the latency, and how often does it complete a proof?

The improvement stage should never make the system less reliable because the validated Fast baseline is retained throughout.

## 8. Literature Rationale

Research on three-dimensional bin packing shows that exact optimization can become computationally difficult as the number of items and possible arrangements grows. Practical systems therefore often use constructive packing strategies that build a solution one item at a time.

Martello, Pisinger and Vigo describe the three-dimensional bin packing problem and exact approaches to minimizing bin count.

Lodi, Martello and Vigo study practical strategies for three-dimensional bin packing.

Crainic, Perboli and Tadei study **Extreme Point-Based Heuristics**. In the language used by this project, the useful takeaway is to test meaningful **candidate positions** rather than every coordinate in the carton.

### Joung and Noh: direct inspiration for the constructive flow

Joung and Noh (2014) developed an intelligent 3D packing method based on how experienced workers approach packing. Their method separates the problem into grouping, sequencing, orientation and loading. The sequencing logic loads larger parts before smaller parts, while the loading logic uses a Bottom-Left-Back-Fill approach that starts from a bottom corner and searches for collision-free positions.

This paper is a direct conceptual inspiration for our solver flow: order difficult or large items early, restrict the orientation search, place items from useful low corner positions, check collisions, and retry alternative placements when a placement fails.

We do **not** copy the paper's implementation. Their system handles free-form 3D CAD geometry and performs shape grouping, repeated orientation comparison, CAD movement and collision checking. Our iHub problem is materially simpler because the input objects are rectangular cuboids with explicit length, width and height. We therefore keep the constructive ideas while implementing a much lighter bounded search suitable for real-time cartonization.

The runtime results in the paper are also not a target for this project. In its SAE J1100 comparison, the proposed method reported 35 loaded pieces with 0.8138 efficiency in 27 minutes, while the compared genetic algorithm reported 21 loaded pieces with 0.6974 efficiency in 68 minutes. Those results demonstrate the tradeoff between packing quality and computation for complex CAD packing, but a 27-minute solver would be unusable for the iHub use case. Fast versus exact-assisted Best quantifies how much packing improvement and proof can be purchased without sacrificing the sub-second target for representative orders.

The project also reviewed `Xebet/3d-packing-simulator`, which demonstrates a practical implementation using remaining empty rectangular spaces, candidate placement positions, multiple orientations, overlap checks and independent validation. The project does not copy that implementation wholesale; it uses those established ideas as references for an independently developed Python solver with iHub-specific rules.

The MIT Scalable Spectral Packing work provides another useful conceptual comparison: order the objects, search for collision-free placements, score placement quality and repeat. Its voxel-grid and Fast Fourier Transform approach is aimed at more general 3D shapes and is therefore not selected for this rectangular-item MVP.

Together, these sources support the current design choice: build a strong heuristic plan first, retain it as a validated fallback, then spend only the remaining runtime proving or finding a better carton objective with exact constraint search.

## References

1. Martello, S., Pisinger, D., & Vigo, D. (2000). The Three-Dimensional Bin Packing Problem. *Operations Research, 48*(2), 256 to 267. https://doi.org/10.1287/opre.48.2.256.12386
2. Lodi, A., Martello, S., & Vigo, D. (2002). Heuristic algorithms for the three-dimensional bin packing problem. *European Journal of Operational Research, 141*(2), 410 to 420. https://doi.org/10.1016/S0377-2217(02)00134-0
3. Crainic, T. G., Perboli, G., & Tadei, R. (2008). Extreme Point-Based Heuristics for Three-Dimensional Bin Packing. *INFORMS Journal on Computing, 20*(3), 368 to 384. https://doi.org/10.1287/ijoc.1070.0250
4. Xebet. *3d-packing-simulator*. GitHub repository: https://github.com/Xebet/3d-packing-simulator
5. MIT News. *Chore of packing just got faster and easier*. 2023. https://news.mit.edu/2023/chore-packing-just-got-faster-and-easier-0706
6. Joung, Y.-K., & Noh, S. D. (2014). Intelligent 3D packing using a grouping algorithm for automotive container engineering. *Journal of Computational Design and Engineering, 1*(2), 140 to 151. https://doi.org/10.7315/JCDE.2014.014
