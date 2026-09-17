# Roadmap

Development is intentionally staged so the public package contract and simple geometry rules are proven before multi-item optimization is introduced.

## MVP 0: package contract + one item per carton

Goal: produce the first working, testable Python-library baseline.

Included:

- structured input and output models
- quantity expansion
- configurable carton catalogue
- maximum-weight check
- generation of unique allowed 90-degree orientations
- `vertical_rotation=true`: up to six unique axis assignments
- `vertical_rotation=false`: original height remains vertical on Z; length and width may swap horizontally
- dimension-by-dimension fit check using only allowed orientations
- smallest-volume fitting carton
- one physical item per carton
- placement at `x=0, y=0, z=0`
- explicit unpacked-item reporting

The rotation rule is a hard packing constraint. Later solver stages must never tip an upright-only item sideways just because doing so would improve carton utilization. Liquid containers are a typical example.

Not included:

- multiple items sharing one carton
- item-to-item overlap checks
- remaining empty-space tracking
- First Fit
- Best Fit
- web API or service layer

## MVP 1: multiple items in one carton

Add the geometry needed for more than one item to share a carton while preserving all MVP 0 constraints:

- carton-boundary checks for arbitrary XYZ positions
- item-to-item overlap checks
- remaining empty rectangular spaces
- useful candidate XYZ positions
- independent geometric validation
- orientation restrictions remain enforced for every placement

## MVP 2: First Fit vs Best Fit

Use the same geometry engine and compare only the placement-selection strategy.

Both strategies must receive the same allowed orientations. First Fit or Best Fit may choose a different valid position, but neither strategy may violate `vertical_rotation`.

Measure:

- valid packing rate
- carton count
- total carton volume
- space utilization
- median runtime
- P95 runtime
- maximum runtime

The central question is whether Best Fit reduces carton usage often enough to justify its extra search time.

## MVP 3: bounded improvement

Only after the baseline strategies are measured, consider:

- alternative fixed item orderings
- bounded repacking
- changing earlier placement decisions for difficult orders
- seeded randomized search if deterministic alternatives are insufficient
- parallel search only if runtime becomes the bottleneck

Improvement may change placements and carton assignments, but it must never relax weight, dimensional, orientation or other validity constraints.

## Release principle

Each stage should leave the public Python interface stable. Later work improves packing quality rather than redesigning how callers import the package, submit inputs or consume results.

See [`INTERFACE.md`](INTERFACE.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), and [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md) for the current contracts.
