# Python Interface

The product is a reusable Python package named `bin_packing_3d`.

Users clone or install the package, import it, and call the public solver function directly.

```python
from bin_packing_3d import solve_order

result = solve_order(
    order=order,
    boxes=boxes,
    config=config,
)
```

`solve_order()` is the main public entry point. Internal modules stay private implementation details unless a later use case justifies exposing additional functions.

## Input contract

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

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `code` | `str` | Yes | Non-empty |
| `length` | `float` | Yes | `> 0`, mm |
| `width` | `float` | Yes | `> 0`, mm |
| `height` | `float` | Yes | `> 0`, mm |
| `weight` | `float` | Yes | `> 0`, kg |
| `quantity` | `int` | Yes | `>= 1` |
| `vertical_rotation` | `bool` | Yes | Controls whether the original height may move away from vertical Z |
| `uom` | `str | None` | No | Descriptive only |

### Rotation behavior

A rectangular item can have up to six unique 90-degree axis assignments when all three dimensions are different. Duplicate orientations are removed automatically when dimensions repeat.

When `vertical_rotation = true`, every unique 90-degree orientation may be tested.

When `vertical_rotation = false`, the original item height must remain on the vertical Z axis. Only the two horizontal arrangements below are allowed, subject to duplicate removal:

```text
L × W × H
W × L × H
```

This allows an item to turn around while remaining upright, but prevents tipping it onto its side. A liquid container is a typical example: a geometrically valid sideways fit must still be rejected if the item is required to stay upright.

### Order

```python
class OrderInput(BaseModel):
    order_id: int | str
    order_no: str
    items: list[ItemInput]
```

`quantity > 1` is expanded internally so every physical unit can receive its own carton and placement.

### Carton

```python
class BoxInput(BaseModel):
    code: str
    length: float
    width: float
    height: float
    max_weight: float
```

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `code` | `str` | Yes | Unique in request |
| `length` | `float` | Yes | `> 0`, mm |
| `width` | `float` | Yes | `> 0`, mm |
| `height` | `float` | Yes | `> 0`, mm |
| `max_weight` | `float` | Yes | `> 0`, kg |

### Configuration

See [`CONFIGURATION.md`](CONFIGURATION.md) for all settings and defaults.

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

## Example input

```python
order = {
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
            "vertical_rotation": True,
            "uom": "EA",
        }
    ],
}

boxes = [
    {
        "code": "Box2",
        "length": 270,
        "width": 170,
        "height": 115,
        "max_weight": 20,
    }
]

config = {
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

## Output contract

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


class PackingResult(BaseModel):
    order_id: int | str
    order_no: str
    status: str
    carton_count: int
    cartons: list[PackedCartonOutput]
    not_packed_items: list[str]
    runtime_ms: float
```

Example MVP 0 result:

```python
{
    "order_id": 1,
    "order_no": "ORDER-001",
    "status": "success",
    "carton_count": 1,
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
                    "height": 50,
                }
            ],
        }
    ],
    "not_packed_items": [],
    "runtime_ms": 4.2,
}
```

The returned `length`, `width`, and `height` are the chosen orientation used for the successful placement, not necessarily the item's original dimension order.

Items that cannot fit any supplied carton in any allowed orientation must be returned explicitly in `not_packed_items`; they must never disappear silently.

## Current MVP 0 behavior

MVP 0 deliberately uses one physical item per carton. For each item it expands quantity, checks weight, generates only the allowed orientations, applies carton clearance, selects the smallest-volume carton that physically fits the item, places it at `x=0, y=0, z=0`, and returns the chosen carton and orientation.

Multi-item packing, overlap checks, remaining empty-space tracking, First Fit and Best Fit are later milestones. See [`ROADMAP.md`](ROADMAP.md).
