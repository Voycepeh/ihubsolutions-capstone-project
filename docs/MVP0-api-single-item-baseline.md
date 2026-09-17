# MVP 0: API Contract and Single-Item Packing Baseline

## Purpose

MVP 0 is the smallest working version of the iHub cartonization product.

It does **not** try to pack multiple items into the same carton yet. Its purpose is to prove the public data contract, input validation, item orientation rules, smallest-fitting-carton selection, XYZ output, and response contract before introducing multi-item 3D packing.

The rule for this milestone is deliberately simple:

> **One physical item per carton. Choose the smallest-volume carton that can validly contain that item. Place the item at `x = 0`, `y = 0`, `z = 0`.**

This gives the project a working and testable API baseline without needing remaining-empty-space logic, overlap checks between multiple items, First Fit, or Best Fit.

## Why start here

This milestone proves the parts of the product that later solver versions should not need to redesign:

1. Request schema.
2. Response schema.
3. Data types and validation rules.
4. Quantity expansion.
5. Carton catalogue as runtime input.
6. Item orientation rules.
7. Weight and dimensional fit checks.
8. Smallest-fitting-carton selection.
9. XYZ placement output.
10. Explicit reporting when no carton can fit an item.

Later milestones can improve how many items share a carton while keeping the same public contract.

## Public interface

The Python entry point remains:

```python
from ihub_packing import solve_order

result = solve_order(
    order=order,
    boxes=boxes,
    config=config,
)
```

A later FastAPI endpoint should be a thin wrapper around the same function:

```python
@app.post("/pack", response_model=PackingResponse)
def pack(request: PackingRequest) -> PackingResponse:
    return solve_order(
        order=request.order,
        boxes=request.boxes,
        config=request.config,
    )
```

Using Pydantic models means the FastAPI OpenAPI/Swagger page can automatically show field names, data types, required fields, defaults, request examples, response shape, and validation errors.

## Request contract

### Item

```python
class ItemInput(BaseModel):
    code: str
    length: float
    width: float
    height: float
    weight: float
    quantity: int
    vertical_rotation: bool
    uom: str | None = None
```

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `code` | `str` | Yes | Non-empty |
| `length` | `float` | Yes | `> 0`, mm |
| `width` | `float` | Yes | `> 0`, mm |
| `height` | `float` | Yes | `> 0`, mm |
| `weight` | `float` | Yes | `> 0`, kg |
| `quantity` | `int` | Yes | `>= 1` |
| `vertical_rotation` | `bool` | Yes | Controls allowed orientations |
| `uom` | `str | None` | No | Descriptive only |

### Order

```python
class OrderInput(BaseModel):
    order_id: int | str
    order_no: str
    items: list[ItemInput]
```

`quantity > 1` is expanded internally into separate physical items so each unit receives its own carton and placement in MVP 0.

### Carton

```python
class BoxInput(BaseModel):
    code: str
    length: float
    width: float
    height: float
    max_weight: float
```

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `code` | `str` | Yes | Unique within request |
| `length` | `float` | Yes | `> 0`, mm |
| `width` | `float` | Yes | `> 0`, mm |
| `height` | `float` | Yes | `> 0`, mm |
| `max_weight` | `float` | Yes | `> 0`, kg |

The carton catalogue is provided at runtime and is not hard coded.

### Configuration

MVP 0 accepts the same configuration object shape intended for later versions, even though not every setting affects the one-item-per-carton logic yet.

```python
class BinBuffer(BaseModel):
    length: float = 0
    width: float = 0
    height: float = 6


class PackingConfig(BaseModel):
    optimization_mode: str = "bins_number"
    bin_max_fill_check_min_item_qty: int = 6
    bin_max_fill_pct: float = 70
    bin_buffer: BinBuffer = BinBuffer()
```

For MVP 0:

- `bin_buffer` affects usable carton dimensions.
- `optimization_mode` is accepted for forward compatibility.
- fill-percentage rules are accepted but do not affect a one-item-per-carton placement unless later agreed otherwise.
- First Fit and Best Fit are **not part of MVP 0**.

### Complete request

```python
class PackingRequest(BaseModel):
    order: OrderInput
    boxes: list[BoxInput]
    config: PackingConfig
```

Example:

```json
{
  "order": {
    "order_id": 1,
    "order_no": "ORDER-001",
    "items": [
      {
        "code": "ITEM-A",
        "length": 120,
        "width": 80,
        "height": 50,
        "weight": 0.8,
        "quantity": 2,
        "vertical_rotation": true,
        "uom": "EA"
      }
    ]
  },
  "boxes": [
    {
      "code": "Box2",
      "length": 270,
      "width": 170,
      "height": 115,
      "max_weight": 20
    },
    {
      "code": "Box4",
      "length": 340,
      "width": 260,
      "height": 150,
      "max_weight": 20
    }
  ],
  "config": {
    "optimization_mode": "bins_number",
    "bin_max_fill_check_min_item_qty": 6,
    "bin_max_fill_pct": 70,
    "bin_buffer": {
      "length": 0,
      "width": 0,
      "height": 6
    }
  }
}
```

## MVP 0 packing logic

For each physical item:

1. Expand quantity so each unit is handled separately.
2. Build the allowed 90-degree orientations for that item.
3. Apply the configured carton clearance to get usable carton dimensions.
4. Reject any carton where the item weight exceeds `max_weight`.
5. Test whether at least one allowed orientation fits within the usable carton dimensions.
6. Keep every carton that passes.
7. Sort fitting cartons by external carton volume, smallest first.
8. Select the smallest fitting carton.
9. Save the chosen orientation.
10. Place the item at `x = 0`, `y = 0`, `z = 0`.
11. If no carton can contain the item, return that physical item in `not_packed_items`.

Conceptually:

```python
for item in physical_items:
    fitting = []

    for box in boxes:
        if item.weight > box.max_weight:
            continue

        for orientation in allowed_orientations(item):
            if orientation_fits_box(orientation, box, config.bin_buffer):
                fitting.append((box, orientation))
                break

    if not fitting:
        not_packed_items.append(item)
        continue

    selected_box, selected_orientation = min(
        fitting,
        key=lambda candidate: candidate[0].volume,
    )

    placements.append(
        Placement(
            item=item,
            box=selected_box,
            orientation=selected_orientation,
            x=0,
            y=0,
            z=0,
        )
    )
```

## Orientation rule

MVP 0 should solve the item-orientation rule before any multi-item geometry is introduced.

When `vertical_rotation = true`, test every unique 90-degree orientation, up to six:

```text
L × W × H
L × H × W
W × L × H
W × H × L
H × L × W
H × W × L
```

Repeated dimensions produce fewer unique orientations.

When `vertical_rotation = false`, the original item height must remain on the vertical Z axis. Length and width may swap horizontally:

```text
L × W × H
W × L × H
```

No diagonal or arbitrary-angle placement is supported.

## Important dimensional rule

Volume alone never proves that an item fits.

For a chosen orientation `(item_l, item_w, item_h)` and usable carton `(box_l, box_w, box_h)`, all three checks must pass:

```python
item_l <= box_l
item_w <= box_w
item_h <= box_h
```

If any one dimension is too large, that orientation does not fit and the solver must try another allowed orientation or another carton.

## XYZ output in MVP 0

Because each physical item has its own carton, there is no item-to-item overlap problem yet.

Every successful placement therefore starts at the carton origin:

```text
x = 0
y = 0
z = 0
```

The output still includes XYZ from day one so later multi-item versions do not need to redesign the response contract.

## Response contract

```python
class PlacementOutput(BaseModel):
    item_id: str
    code: str
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float


class PackedCartonOutput(BaseModel):
    code: str
    packed_weight_kg: float
    used_space_pct: float
    items: list[PlacementOutput]


class PackingResponse(BaseModel):
    order_id: int | str
    order_no: str
    status: str
    carton_count: int
    cartons: list[PackedCartonOutput]
    not_packed_items: list[str]
    runtime_ms: float
```

Example successful response for quantity `2`:

```json
{
  "order_id": 1,
  "order_no": "ORDER-001",
  "status": "success",
  "carton_count": 2,
  "cartons": [
    {
      "code": "Box2",
      "packed_weight_kg": 0.8,
      "used_space_pct": 13.1,
      "items": [
        {
          "item_id": "ITEM-A#1",
          "code": "ITEM-A",
          "x": 0,
          "y": 0,
          "z": 0,
          "length": 120,
          "width": 80,
          "height": 50
        }
      ]
    },
    {
      "code": "Box2",
      "packed_weight_kg": 0.8,
      "used_space_pct": 13.1,
      "items": [
        {
          "item_id": "ITEM-A#2",
          "code": "ITEM-A",
          "x": 0,
          "y": 0,
          "z": 0,
          "length": 120,
          "width": 80,
          "height": 50
        }
      ]
    }
  ],
  "not_packed_items": [],
  "runtime_ms": 4.2
}
```

If one physical item cannot fit any carton, it must not disappear silently. It must be returned explicitly in `not_packed_items`, and the response status must distinguish a complete success from a partial or failed packing.

## First unit tests

The first automated tests should be intentionally small and easy to reason about manually.

| Test | Input | Expected result |
| --- | --- | --- |
| Simple cube fits | Item `10×10×10`, box `20×20×20` | Box selected, XYZ `0,0,0` |
| One dimension too large | Item `30×10×10`, box `20×20×20` | Box rejected |
| Fall back to larger box | Same item plus box `40×20×20` | Larger box selected |
| Rotation makes fit possible | Item only fits after an allowed 90-degree turn | Packing succeeds |
| Rotation restriction blocks fit | Same item with `vertical_rotation=false` | Current box rejected; another box selected or item returned unpacked |
| Weight too high | Item weight exceeds smaller box limit | Smaller box rejected |
| Quantity expansion | Quantity `2` | Two physical placements and two cartons |
| Smallest fitting carton | Two cartons both fit | Smaller external-volume carton selected |
| Rectangular dimensions | Non-cube item and non-cube carton | Dimension-by-dimension fit works correctly |
| No carton fits | Item too large for every orientation/carton | Item appears in `not_packed_items` |

The key geometry assertion for MVP 0 is simple:

> If any required X, Y, or Z extent of an allowed orientation is larger than the usable carton extent on that axis, that orientation must be rejected.

## Suggested implementation modules for MVP 0

Only a small subset of the final architecture is needed:

```text
src/ihub_packing/
  __init__.py      public solve_order()
  models.py        request/internal/result models
  normalize.py     input validation and quantity expansion
  orientation.py   allowed 90-degree orientations
  feasibility.py   weight + dimension checks and smallest-box ordering
  single_item.py   one physical item -> one selected carton
  result.py        stable response formatting
```

Initial tests:

```text
tests/
  test_models.py
  test_normalize.py
  test_orientation.py
  test_feasibility.py
  test_single_item.py
  test_solve_order.py
```

No `spaces.py`, multi-item overlap engine, First Fit, Best Fit, or multi-carton optimization is required to complete MVP 0.

## What comes after MVP 0

### MVP 1: multiple items in one carton

Add:

- remaining empty-space tracking,
- candidate XYZ positions,
- overlap checks,
- multiple item placements in one carton.

### MVP 2: First Fit vs Best Fit

Run both strategies through the same multi-item geometry engine and compare:

- carton count,
- total carton volume,
- space utilization,
- median runtime,
- P95 runtime.

### MVP 3: smarter multi-carton improvement

Only after the baseline is measured, consider alternative item ordering, bounded repacking, backtracking, or other more expensive search approaches.

## Definition of done

MVP 0 is complete when:

1. The request and response Pydantic models are defined and visible through FastAPI/OpenAPI when the thin API layer is added.
2. Invalid field values are rejected clearly.
3. Quantity expansion works.
4. Allowed orientation generation works.
5. The smallest-volume fitting carton is selected for every physical item.
6. Item weight and usable carton dimensions are respected.
7. Every successful item has an orientation and XYZ placement of `0,0,0`.
8. Items that cannot fit any carton are reported explicitly.
9. The small manually-verifiable unit-test set passes.
10. No multi-item packing logic is required for this milestone.