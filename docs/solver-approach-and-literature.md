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

## 1. Shared 3D Placement Approach

The solver first builds a fast valid plan with deterministic First Fit. Only after that complete baseline exists does it spend remaining runtime trying to improve the plan.

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

## 2. First Fit Baseline and Best Fit Improvement

### First Fit baseline

MVPs 1 to 3 use First Fit. It accepts the first valid candidate placement in deterministic order.

This gives the solver a fast, complete and validated fallback plan before any more expensive search begins.

### Best Fit improvement

MVP 4 uses Best Fit as an improvement search. It evaluates more valid placement choices using the same geometry and business rules.

An improved plan is kept only when it uses fewer cartons, or the same number of cartons with lower total external carton volume.

If the improvement search reaches the runtime limit, the solver returns the best validated plan already found. The First Fit baseline is therefore always available as a fallback.

The experiment is whether the extra runtime produces a material business improvement in carton count or carton volume.

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
2. **MVP 2 — Pack one carton:** expand quantity into physical item instances and use First Fit to pack one carton, returning packed plus remaining items.
3. **MVP 3 — Pack the whole order:** repeatedly reuse the one-carton engine to create a complete validated First Fit baseline.
4. **MVP 4 — Improve the plan:** use remaining runtime for Best Fit and selected alternative sequences; keep only a complete plan with fewer cartons or lower total carton volume at equal carton count.

This gives the solver an anytime structure: a valid baseline is available first, then extra computation is spent only on potential improvement.

## 7. Evaluation

The benchmark should compare the MVP 3 First Fit baseline with the final result after MVP 4 improvement.

| Measure | Purpose |
| --- | --- |
| Valid solution rate | Correctness baseline |
| Cartons used | Primary optimization outcome |
| Total carton volume | Secondary objective when carton count is equal |
| Space utilization | Later tie break and diagnostic |
| First Fit baseline runtime | Time to guaranteed valid fallback |
| Total runtime | Cost after improvement search |
| Orders with fewer cartons after improvement | Direct business benefit |
| Orders with smaller carton volume at equal carton count | Secondary business benefit |
| Orders with no material improvement | Extra search that did not change the business outcome |
| Timeout fallback count | How often the solver returned the existing best plan |

The main experimental question is:

> Does the additional Best Fit search time actually reduce carton count or total carton volume often enough to justify the latency?

The improvement stage should never make the system less reliable because the validated First Fit baseline is retained throughout.

## 8. Literature Rationale

Research on three-dimensional bin packing shows that exact optimization can become computationally difficult as the number of items and possible arrangements grows. Practical systems therefore often use constructive packing strategies that build a solution one item at a time.

Martello, Pisinger and Vigo describe the three-dimensional bin packing problem and exact approaches to minimizing bin count.

Lodi, Martello and Vigo study practical strategies for three-dimensional bin packing.

Crainic, Perboli and Tadei study **Extreme Point-Based Heuristics**. In the language used by this project, the useful takeaway is to test meaningful **candidate positions** rather than every coordinate in the carton.

### Joung and Noh: direct inspiration for the constructive flow

Joung and Noh (2014) developed an intelligent 3D packing method based on how experienced workers approach packing. Their method separates the problem into grouping, sequencing, orientation and loading. The sequencing logic loads larger parts before smaller parts, while the loading logic uses a Bottom-Left-Back-Fill approach that starts from a bottom corner and searches for collision-free positions.

This paper is a direct conceptual inspiration for our solver flow: order difficult or large items early, restrict the orientation search, place items from useful low corner positions, check collisions, and retry alternative placements when a placement fails.

We do **not** copy the paper's implementation. Their system handles free-form 3D CAD geometry and performs shape grouping, repeated orientation comparison, CAD movement and collision checking. Our iHub problem is materially simpler because the input objects are rectangular cuboids with explicit length, width and height. We therefore keep the constructive ideas while implementing a much lighter bounded search suitable for real-time cartonization.

The runtime results in the paper are also not a target for this project. In its SAE J1100 comparison, the proposed method reported 35 loaded pieces with 0.8138 efficiency in 27 minutes, while the compared genetic algorithm reported 21 loaded pieces with 0.6974 efficiency in 68 minutes. Those results demonstrate the tradeoff between packing quality and computation for complex CAD packing, but a 27-minute solver would be unusable for the iHub use case. Our solver must remain sub-second for representative orders, and First Fit versus Best Fit is specifically intended to quantify how much packing improvement can be purchased without sacrificing that latency requirement.

The project also reviewed `Xebet/3d-packing-simulator`, which demonstrates a practical implementation using remaining empty rectangular spaces, candidate placement positions, multiple orientations, overlap checks and independent validation. The project does not copy that implementation wholesale; it uses those established ideas as references for an independently developed Python solver with iHub-specific rules.

The MIT Scalable Spectral Packing work provides another useful conceptual comparison: order the objects, search for collision-free placements, score placement quality and repeat. Its voxel-grid and Fast Fourier Transform approach is aimed at more general 3D shapes and is therefore not selected for this rectangular-item MVP.

Together, these sources support the current design choice: build a simple First Fit solution first, retain it as a validated fallback, then spend only the remaining runtime on Best Fit or selected retries and keep them only when they materially improve carton count or total carton volume.

## References

1. Martello, S., Pisinger, D., & Vigo, D. (2000). The Three-Dimensional Bin Packing Problem. *Operations Research, 48*(2), 256 to 267. https://doi.org/10.1287/opre.48.2.256.12386
2. Lodi, A., Martello, S., & Vigo, D. (2002). Heuristic algorithms for the three-dimensional bin packing problem. *European Journal of Operational Research, 141*(2), 410 to 420. https://doi.org/10.1016/S0377-2217(02)00134-0
3. Crainic, T. G., Perboli, G., & Tadei, R. (2008). Extreme Point-Based Heuristics for Three-Dimensional Bin Packing. *INFORMS Journal on Computing, 20*(3), 368 to 384. https://doi.org/10.1287/ijoc.1070.0250
4. Xebet. *3d-packing-simulator*. GitHub repository: https://github.com/Xebet/3d-packing-simulator
5. MIT News. *Chore of packing just got faster and easier*. 2023. https://news.mit.edu/2023/chore-packing-just-got-faster-and-easier-0706
6. Joung, Y.-K., & Noh, S. D. (2014). Intelligent 3D packing using a grouping algorithm for automotive container engineering. *Journal of Computational Design and Engineering, 1*(2), 140 to 151. https://doi.org/10.7315/JCDE.2014.014
