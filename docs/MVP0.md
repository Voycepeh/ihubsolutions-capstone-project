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
3. generate allowed 90-degree orientations,
4. apply carton clearance,
5. reject cartons that fail weight or dimensional checks,
6. choose the smallest-volume carton that fits,
7. place the item at `x=0, y=0, z=0`,
8. return the chosen carton and orientation,
9. report the item explicitly if no carton fits.

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
- `VerticalRotation` is respected,
- weight and dimension checks work,
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
