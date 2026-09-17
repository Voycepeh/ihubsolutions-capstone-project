# Configuration

Packing rules are runtime inputs. They must not be hard coded into `bin_packing_3d` because carton catalogues and operational rules can change independently of the solver.

## Current configuration shape

```json
{
  "optimization_mode": "bins_number",
  "bin_max_fill_check_min_item_qty": 6,
  "bin_max_fill_pct": 70,
  "bin_buffer": {
    "length": 0,
    "width": 0,
    "height": 6
  }
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

The carton catalogue is part of each request rather than configuration stored in code.

```json
{
  "code": "Box2",
  "length": 270,
  "width": 170,
  "height": 115,
  "max_weight": 20
}
```

MVP 0 sorts all cartons that can validly contain an item by external carton volume and selects the smallest.

## Rotation rule

`vertical_rotation` is an item-level rule.

When `true`, the solver may test every unique 90-degree orientation of the item's length, width and height.

When `false`, the original height remains on the vertical Z axis. Length and width may still swap horizontally.

No diagonal or arbitrary-angle rotation is supported.

## Fill rule

The current business rule is:

- six or fewer physical items: up to full volumetric fill is allowed;
- more than six physical items: default maximum fill is 70%.

The threshold and percentage remain configurable. The rule becomes materially relevant when multiple items can share one carton; MVP 0 uses one physical item per carton.

## Buffer rule

Configured buffer reduces the usable internal carton dimensions before fit checks are performed. The exact interpretation of the supplied 6 mm height buffer must remain consistent across the API contract, implementation and benchmark tests.

See [`API.md`](API.md) for the request schema and [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md) for detailed behavior.
