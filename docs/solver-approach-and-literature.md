# Research and Literature Rationale

This page records **why** the capstone uses a fast constructive packing strategy followed by optional exact optimization. It is not a second implementation specification.

For the actual solver behavior, see the [Fast implementation guide](fast-solver-under-the-hood.md), [Best implementation guide](best-solver-under-the-hood.md), and [product specification](../src/PRODUCT_SPEC.md). The [README](../README.md) covers API usage, constraint validation, and measured benchmarks.

## Problem and design choice

The primary objective is to minimize cartons while respecting the supplied dimensions, allowed 90-degree orientations, weight limits, fill caps, clearance and three-dimensional non-overlap.

A volume check is useful to reject impossible cartons, but it cannot prove geometric fit: an item may be longer than the usable carton in every permitted orientation, or multiple items may intersect even when their combined volume is small enough.

The project therefore uses two complementary approaches:

1. **Fast:** construct a valid packing by trying allowed orientations at useful candidate positions, then make a bounded attempt to reduce carton count.
2. **Best:** retain Fast as a fallback, then test alternative carton combinations with an exact three-dimensional feasibility model while the configured search budget permits.

These are **current implementation choices**, not claims that a specific research paper's algorithm was reproduced. Neither a valid heuristic result nor a feasible exact-solver result alone establishes a global optimum; proof depends on completing the relevant search.

## Research informing the approach

**Martello, Pisinger and Vigo (2000)** formalize the three-dimensional bin-packing problem and exact optimization approaches. Their work motivates separating the carton-count objective from the geometric feasibility constraints.

**Lodi, Martello and Vigo (2002)** examine heuristic algorithms for three-dimensional bin packing, supporting the practical need to compare fast constructive methods against more expensive search.

**Crainic, Perboli and Tadei (2008)** investigate *Extreme Point-Based Heuristics*. An **extreme point** is a promising candidate placement position created by carton boundaries or already packed items. Testing these positions avoids exhaustively trying every coordinate.

**Joung and Noh (2014)** present an intelligent packing method inspired by manual packing, including grouping, sequencing, orientation and loading. Their bottom-left-back placement concept is a useful conceptual reference for placing larger items early and testing low, collision-free positions. Their work handles more general CAD shapes; this capstone handles rectangular cuboids and does not copy their implementation or treat their reported runtimes as comparable.

**Xebet's 3d-packing-simulator** is a practical reference for remaining empty rectangular spaces, candidate positions, rotations and validation. **Remaining empty space** means a rectangular region still available after previous placements. The capstone does not import that implementation wholesale.

**MIT's Scalable Spectral Packing research** provides a broader comparison involving collision-free placement search for more general three-dimensional shapes. Its voxel-grid and Fast Fourier Transform techniques are not the selected approach for the rectangular-item capstone.

## What the capstone evaluates

The practical research question is whether Best's additional search reduces carton count or external carton volume often enough to justify its latency. Evaluation must compare only valid packings and report runtime budgets, timeout fallbacks and whether optimality was actually proven.

The [README benchmark section](../README.md#fast-vs-best-execution-time) contains the current performance evidence. Reference carton choices from iHub are comparison outputs, not proof of the mathematically best packing.

## References

1. Martello, S., Pisinger, D., & Vigo, D. (2000). The Three-Dimensional Bin Packing Problem. *Operations Research, 48*(2), 256–267. https://doi.org/10.1287/opre.48.2.256.12386
2. Lodi, A., Martello, S., & Vigo, D. (2002). Heuristic algorithms for the three-dimensional bin packing problem. *European Journal of Operational Research, 141*(2), 410–420. https://doi.org/10.1016/S0377-2217(02)00134-0
3. Crainic, T. G., Perboli, G., & Tadei, R. (2008). Extreme Point-Based Heuristics for Three-Dimensional Bin Packing. *INFORMS Journal on Computing, 20*(3), 368–384. https://doi.org/10.1287/ijoc.1070.0250
4. Joung, Y.-K., & Noh, S. D. (2014). Intelligent 3D packing using a grouping algorithm for automotive container engineering. *Journal of Computational Design and Engineering, 1*(2), 140–151. https://doi.org/10.7315/JCDE.2014.014
5. Xebet. *3d-packing-simulator*. https://github.com/Xebet/3d-packing-simulator
6. MIT News. *Chore of packing just got faster and easier*. 2023. https://news.mit.edu/2023/chore-packing-just-got-faster-and-easier-0706
