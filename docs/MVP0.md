# MVP 0: Single-Item Packing Baseline

MVP 0 is the smallest working version of `bin_packing_3d`.

The package is used directly from Python:

```python
from bin_packing_3d import solve_order
```

## Goal

Prove the public package contract and the simplest valid carton-selection logic before introducing multi-item 3D packing.

For every physical item:

1. validate the input,
2. expand quantity,
3. generate the allowed 90-degree orientations while respecting `vertical_rotation`,
4. apply carton clearance,
5. reject cartons that fail weight or dimensional checks,
6. choose the smallest-volume carton that fits,
7. place the item at `x=0, y=0, z=0`,
8. return the chosen carton and orientation,
9. report the item explicitly if no carton fits.

## Rotation is already part of MVP 0

For a rectangular item with three different dimensions, there are up to six unique ways to assign its original length, width and height to the carton X, Y and Z axes. Repeated dimensions naturally produce fewer unique orientations.

`vertical_rotation` limits which of those orientations are allowed:

- `vertical_rotation = true`: test every unique 90-degree axis assignment, up to six.
- `vertical_rotation = false`: the item's original height must remain on the vertical Z axis. Length and width may swap horizontally, so only `L × W × H` and `W × L × H` are allowed after duplicate removal.

This is a real packing constraint, not just an optimization setting. For example, a bottle or liquid container may need to remain upright so its contents do not leak. The solver must never choose a carton fit that requires an orientation forbidden by this rule.

## Deliberate limitation

MVP 0 uses **one physical item per carton**.

That means it does not yet need:

- item-to-item overlap checks,
- remaining empty-space tracking,
- multiple items in one carton,
- First Fit,
- Best Fit,
- multi-carton optimization,
- a web API or service layer.

## Definition of done

MVP 0 is complete when:

- package inputs and outputs are defined and validated,
- quantity expansion works,
- all unique allowed orientations are generated without duplicates,
- `vertical_rotation=false` always preserves the original height on Z,
- weight and dimension checks work against each allowed orientation,
- the smallest fitting carton is selected,
- every successful placement is returned at `0,0,0`,
- unpackable items are reported explicitly,
- the manually verifiable unit-test set passes.

## Detailed docs

- [`INTERFACE.md`](INTERFACE.md) — Python input and output contract
- [`CONFIGURATION.md`](CONFIGURATION.md) — configurable packing rules
- [`TESTING.md`](TESTING.md) — MVP 0 unit tests
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — package structure and future modules
- [`ROADMAP.md`](ROADMAP.md) — later solver stages
- [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md) — detailed engineering specification
