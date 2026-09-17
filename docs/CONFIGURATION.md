# Configuration

Packing rules are runtime inputs. They must not be hard coded into `bin_packing_3d` because carton catalogues and operational rules can change independently of the solver.

## Current configuration shape

```python
{
    "optimization_mode": "bins_number",
    "bin_max_fill_check_min_item_qty": 6,
    "bin_max_fill_pct": 70,
    "bin_buffer": {
        "length": 0,
        "width": 0,
        "height": 6,
    },
}
```

## Settings

| Setting | Current default | Meaning |
| --- | ---: | --- |
| `optimization_mode` | `bins_number` | Minimize carton count |
| `bin_max_fill_check_min_item_qty` | `6` | Fill cap applies above this physical item count |
| `bin_max_fill_pct` | `70` | Maximum carton volume fill once threshold applies |
| `bin_buffer.length` | `0 mm` | Reserved length clearance |
| `bin_buffer.width` | `0 mm` | Reserved width clearance |
| `bin_buffer.height` | `6 mm` | Reserved height clearance |

Later milestones add search settings such as `placement_strategy`, `max_runtime_ms`, `max_empty_spaces`, and `max_candidate_positions_per_space`. Those settings should not affect MVP 0 unless explicitly introduced into that milestone.

## Carton catalogue

The carton catalogue is supplied when calling the package rather than stored in solver code.

```python
{
    "code": "Box2",
    "length": 270,
    "width": 170,
    "height": 115,
    "max_weight": 20,
}
```

MVP 0 sorts all cartons that can validly contain an item by external carton volume and selects the smallest.

## Rotation rule

`vertical_rotation` is an item-level hard packing constraint.

When `true`, the solver may test every unique 90-degree assignment of the item's original length, width and height to X, Y and Z, up to six unique orientations.

When `false`, the original height must remain on the vertical Z axis. Length and width may still swap horizontally:

```text
L × W × H
W × L × H
```

Repeated dimensions are deduplicated, so symmetric items naturally have fewer unique orientations.

A fit that requires a forbidden orientation is not valid even when the item would physically fit after tipping. This matters for upright-only products such as bottles or liquid containers where laying the item on its side could cause leakage or damage.

This rule must remain enforced in every later solver stage, including multi-item placement, First Fit, Best Fit and bounded improvement.

No diagonal or arbitrary-angle rotation is supported.

## Fill rule

The current business rule is:

- six or fewer physical items: up to full volumetric fill is allowed;
- more than six physical items: default maximum fill is 70%.

The threshold and percentage remain configurable. The rule becomes materially relevant when multiple items can share one carton; MVP 0 uses one physical item per carton.

## Buffer rule

Configured buffer reduces the usable internal carton dimensions before fit checks are performed. The exact interpretation of the supplied 6 mm height buffer must remain consistent across the package interface, implementation and benchmark tests.

See [`INTERFACE.md`](INTERFACE.md) for the input contract and [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md) for detailed behavior.
