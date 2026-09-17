# Roadmap

Development is intentionally staged so the public contract and simple geometry rules are proven before multi-item optimization is introduced.

## MVP 0: API contract + one item per carton

Goal: produce the first working, testable API/library baseline.

Included:

- Pydantic-style request and response models
- quantity expansion
- configurable carton catalogue
- maximum-weight check
- allowed 90-degree orientations
- `VerticalRotation` rule
- dimension-by-dimension fit check
- smallest-volume fitting carton
- one physical item per carton
- placement at `x=0, y=0, z=0`
- explicit unpacked-item reporting

Not included:

- multiple items sharing one carton
- item-to-item overlap checks
- remaining empty-space tracking
- First Fit
- Best Fit

## MVP 1: multiple items in one carton

Add the geometry needed for more than one item to share a carton:

- carton-boundary checks for arbitrary XYZ positions
- item-to-item overlap checks
- remaining empty rectangular spaces
- useful candidate XYZ positions
- independent geometric validation

## MVP 2: First Fit vs Best Fit

Use the same geometry engine and compare only the placement-selection strategy.

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

## Release principle

Each stage should leave the public API contract stable. Later work improves packing quality rather than redesigning how callers submit orders or consume results.

See [`API.md`](API.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), and [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md) for the current contracts.
