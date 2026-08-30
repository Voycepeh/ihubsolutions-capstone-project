# Feature Requirements and Interface Contract

## Purpose

This document defines the proposed MVP behaviour of the reusable 3D bin-packing / cartonization engine.

The design principle is to keep the packing engine independent from the way users call it. The same underlying Python functions should be usable from:

- a Python script
- a notebook
- a command-line workflow
- a future FastAPI endpoint

The engine should be **configuration-driven** so users can provide order data, a box catalogue and selected packing rules without changing the underlying solver code.

---

## 1. High-level interaction

```text
Order Data
(JSON / CSV)
      +
Box Catalogue
      +
Packing Configuration
      |
      v
Reusable Packing Engine
      |
      v
Packing Result
```

The API or script should act mainly as an interface. Validation, packing logic, constraints and optimization should remain inside reusable Python modules.

---

## 2. Core MVP functional requirements

### FR-01 — Accept order data

The solver must accept one or more orders containing item information required for packing.

Minimum item fields:

| Field | Required | Description |
|---|---|---|
| `Code` | Yes | Item identifier |
| `Length` | Yes | Item length in mm |
| `Width` | Yes | Item width in mm |
| `Height` | Yes | Item height in mm |
| `Weight` | Yes | Unit weight in kg |
| `Quantity` | Yes | Number of physical units |
| `VerticalRotation` | Yes | Whether vertical rotation is permitted |
| `UOM` | No for packing logic | Unit of measure / descriptive metadata |

The supplied iHub JSON format should be supported directly for the MVP.

CSV support is a proposed convenience interface. CSV rows should be normalized internally into the same item model used by JSON input.

### FR-02 — Accept a box catalogue

The solver must accept a list of candidate boxes rather than hard-code the packing algorithm to one carton set.

Minimum box fields:

| Field | Required | Description |
|---|---|---|
| `Code` | Yes | Box identifier |
| `Length` | Yes | Box length in mm |
| `Width` | Yes | Box width in mm |
| `Height` | Yes | Box height in mm |
| `MaxWeight` | Yes | Maximum permitted packed weight in kg |

The current reference dataset provides these seven boxes:

| Box | Length (mm) | Width (mm) | Height (mm) | Max Weight (kg) |
|---|---:|---:|---:|---:|
| Box2 | 220 | 170 | 115 | 20 |
| Box3 | 270 | 180 | 180 | 20 |
| Box4 | 340 | 260 | 150 | 20 |
| Box5 | 340 | 260 | 235 | 20 |
| Box6 | 340 | 260 | 280 | 20 |
| Box8 | 290 | 180 | 280 | 20 |
| Box9 | 440 | 345 | 280 | 20 |

These should be the default project benchmark catalogue, but the engine should be designed so another catalogue can be passed later.

### FR-03 — Expand quantities into packable units

`Quantity > 1` must be treated as multiple physical objects for placement and collision checking.

The input format may remain aggregated, but the internal solver should create the required physical instances.

### FR-04 — Respect dimensional feasibility

Every item placement must remain within the usable internal dimensions of its assigned box.

### FR-05 — Respect rotation constraints

Items with `VerticalRotation = 0` must remain upright.

Items with `VerticalRotation = 1` may use the permitted orientations supported by the solver.

### FR-06 — Enforce maximum weight

The total packed weight of a carton must not exceed its `MaxWeight`.

For the supplied reference boxes, this limit is 20 kg.

### FR-07 — Apply configurable bin buffer

The engine must support configurable clearance from the nominal box dimensions.

Current reference configuration:

```json
{
  "Length": 0,
  "Width": 0,
  "Height": 6
}
```

The effective packing dimensions must reflect this buffer.

### FR-08 — Apply configurable maximum fill rule

The engine should support:

```json
{
  "BinMaxFillCheckMinItemQty": 6,
  "BinMaxFillPct": 70
}
```

For orders above the configured threshold, the permitted volumetric fill should be capped according to the configured percentage.

For this project, the 70% rule is treated as a usability requirement intended to avoid extremely tight packing arrangements.

### FR-09 — Minimize number of boxes

The primary optimization objective for the MVP is:

> Minimize the total number of cartons required to pack the order while satisfying all hard constraints.

This corresponds to the supplied `bins_number` optimization mode.

### FR-10 — Support multi-box packing

If no single candidate box can feasibly contain the entire order, the engine must allocate items across multiple cartons.

The total number of cartons should still be minimized.

### FR-11 — Report unpackable items

If no feasible packing exists using the supplied box catalogue and constraints, the engine must return the items that could not be packed.

The sample dataset contains only successful cases, so additional edge and failure cases will need to be created for testing.

### FR-12 — Return explainable packing output

For each selected carton, the result should include enough information to validate the solution.

Suggested output fields:

- box code
- packed items
- quantity / physical item identifier
- item orientation
- item position where available
- packed weight
- used-space percentage
- constraint status
- unpacked items
- solver runtime

---

## 3. Configuration-driven design

The objective is to allow users to change common packing behaviour without editing the solver itself.

### Proposed configuration categories

| Configuration | Example | MVP |
|---|---|---|
| Optimization mode | `bins_number` | Yes |
| Max fill threshold | `6` items | Yes |
| Maximum fill | `70%` | Yes |
| Bin buffer | `0, 0, 6 mm` | Yes |
| Box catalogue | supplied list | Yes |
| Allow rotation | item-level | Yes |
| Runtime / search limit | configurable seconds | Later / optional |
| Secondary objective | smaller carton volume | Later / optional |
| Heuristic strategy | largest-first, etc. | Internal initially |

### Example configuration

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

The API, command-line interface and Python functions should all ultimately pass this configuration into the same packing engine.

---

## 4. Proposed normalized input contract

The current iHub JSON should remain a supported input format, but internally we should normalize inputs to a simple common structure.

### Example JSON request

```json
{
  "order_id": "ORDER-001",
  "items": [
    {
      "code": "ITEM-A",
      "length": 140,
      "width": 80,
      "height": 116,
      "weight": 0.285,
      "quantity": 2,
      "vertical_rotation": true
    }
  ],
  "boxes": [
    {
      "code": "Box3",
      "length": 270,
      "width": 180,
      "height": 180,
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

---

## 5. Proposed CSV interface

CSV should be treated as an input convenience layer rather than a different solver implementation.

Example:

```csv
OrderId,Code,Length,Width,Height,Weight,Quantity,VerticalRotation
ORDER-001,ITEM-A,140,80,116,0.285,2,1
ORDER-001,ITEM-B,55,55,110,0.130,1,1
```

The loader should convert this into the same normalized order and item objects used by JSON input.

The box catalogue and configuration can be supplied separately, for example through JSON, Python dictionaries or API fields.

---

## 6. Proposed output contract

Example result:

```json
{
  "order_id": "ORDER-001",
  "status": "success",
  "bins_used": 1,
  "bins": [
    {
      "code": "Box3",
      "used_space_pct": 48.2,
      "packed_weight_kg": 1.15,
      "items": [
        {
          "code": "ITEM-A",
          "instance": 1,
          "orientation": [140, 80, 116],
          "position": [0, 0, 0]
        }
      ]
    }
  ],
  "not_packed_items": [],
  "runtime_ms": 205
}
```

Exact output fields may evolve as the packing algorithm is implemented, but the service should remain easy to inspect and validate.

---

## 7. Reusable Python interface

The core design should resemble a reusable Python package rather than an API-first application.

Conceptually:

```python
result = solve_order(
    order=order,
    boxes=boxes,
    config=config,
)
```

Possible supporting functions:

```python
load_order_json(...)
load_order_csv(...)
validate_order(...)
validate_boxes(...)
generate_orientations(...)
pack_single_box(...)
solve_order(...)
evaluate_solution(...)
```

The FastAPI layer should call these functions rather than contain the packing algorithm itself.

---

## 8. Future FastAPI interface

Once the Python engine is stable, a thin API wrapper can expose it as a service.

Example endpoint:

```text
POST /pack
```

Request:

```text
Order + Boxes + Config
```

Response:

```text
Packing Result
```

This keeps the engine reusable while allowing another application, UI or integration to call it over HTTP.

---

## 9. MVP versus later enhancements

### MVP

- iHub-compatible JSON input
- optional CSV loader
- configurable box catalogue
- configurable buffer
- configurable maximum fill rule
- quantity handling
- item rotation rules
- maximum weight constraint
- single-box and multi-box packing
- minimize number of cartons
- unpackable-item reporting
- explainable result
- runtime measurement
- reusable Python function / script interface

### Later enhancements

- FastAPI service wrapper
- authentication
- persistent storage
- web user interface
- additional optimization modes
- configurable heuristic strategies
- visualization of 3D placements
- parallel processing / scaling
- production deployment and monitoring

---

## 10. Design principle

The packing engine should own the complexity.

Users should mainly provide:

1. **What needs to be packed** — order / item data
2. **What it can be packed into** — box catalogue
3. **How packing should behave** — configuration

The engine then validates the inputs, applies the rules, searches for a feasible packing and returns an explainable result.

This approach keeps the solution reusable and slightly customizable without requiring users to understand or modify the underlying 3D packing algorithm.
