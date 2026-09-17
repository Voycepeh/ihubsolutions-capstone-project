# Joung and Noh (2014): Intelligent 3D Packing

## Source

Youn-Kyoung Joung and Sang Do Noh (2014), **“Intelligent 3D packing using a grouping algorithm for automotive container engineering”**, *Journal of Computational Design and Engineering*, 1(2), 140–151.

DOI: https://doi.org/10.7315/JCDE.2014.014

This paper is included as a design reference for the iHub capstone solver. It is not treated as a direct implementation specification because its problem setting is broader and substantially more computationally expensive than the cuboid cartonization problem used in this project.

## Why it is useful to this project

The paper separates 3D packing into distinct concerns: grouping, sequencing, orientation, and loading. Its practical packing logic also reflects how human packers work: place larger objects first, use smaller objects to fill remaining space, keep similar objects in similar orientations where possible, and begin from a bottom corner.

For placement, the paper uses a **Bottom-Left-Back-Fill** approach. The first object begins at the bottom-left-rear corner and later objects are moved toward useful faces created by previously loaded objects while avoiding collisions.

These ideas support three design choices in our solver:

1. **Deterministic item sequencing.** Harder or larger items should be considered before easier or smaller items rather than relying on arbitrary input order.
2. **Bounded candidate positions.** The solver should test useful XYZ positions created by carton boundaries and already packed items rather than scan every possible coordinate.
3. **Simple placement first.** A fast constructive placement strategy should be the baseline before introducing more expensive search or optimization.

## What we deliberately do differently

The paper solves a much harder geometry problem involving free-form 3D CAD objects. It performs shape grouping, repeated orientation comparisons, collision checks on CAD geometry, and loading simulation. Its reported SAE J1100 comparison required **27 minutes** for the proposed method and **68 minutes** for the genetic algorithm.

That runtime is not acceptable for iHub's operational use case.

Our supplied benchmark data shows the existing iHub service operating in the sub-second range, commonly around a few hundred milliseconds. The capstone solver therefore keeps a hard real-time engineering target:

| Metric | Initial project target |
| --- | ---: |
| Median runtime | below 250 ms |
| P95 runtime | below 1,000 ms |
| Validity | 100% of returned successful plans pass independent validation |
| Primary objective | minimize carton count |

The project therefore borrows the paper's **constructive packing principles**, not its CAD-heavy implementation.

## Adapted solver logic

For our rectangular items and cartons, the practical adaptation is:

```text
Order items deterministically
    ↓
Generate only allowed 90-degree orientations
    ↓
Try useful XYZ candidate positions from the bottom / left / back first
    ↓
Reject carton-boundary, overlap, weight, fill, buffer or rotation violations
    ↓
First Fit: stop at the first valid placement
or
Best Fit: score valid placements within the configured search limits
    ↓
Update remaining empty rectangular spaces
    ↓
Continue until packed, then independently validate
```

The important performance rule is that **First Fit remains the low-search baseline**. Best Fit is only justified if benchmark evidence shows that its extra candidate evaluation materially reduces carton count or total carton volume without breaking the latency target.

## Relationship to the current MVP roadmap

The paper does not change the staged development plan.

**MVP 0** still proves the package contract and single-item geometry first.

**MVP 1** introduces multi-item XYZ placement, overlap checks, remaining empty spaces, and bottom-left-back biased candidate ordering.

**MVP 2** compares First Fit and Best Fit on exactly the same geometry engine and item ordering. This isolates the speed-versus-packing-quality tradeoff instead of comparing two unrelated implementations.

More expensive techniques such as genetic algorithms, simulated annealing, deeper backtracking, or arbitrary-shape CAD processing remain deferred unless benchmark results show they are needed.

## Credit and use

The design inspiration taken from Joung and Noh is explicitly limited to the high-level constructive concepts described above: larger-first sequencing, restricted orientation search, bottom-left-back placement bias, collision-aware incremental loading, and retrying alternative placement decisions when necessary.

The implementation in this repository is independently developed for configurable cuboid cartonization and iHub-specific constraints.
