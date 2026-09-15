# 3D Bin-Packing Benchmark Datasets

Sample datasets for the **NUS Industry 4.0 (i4.0) Master's project** developing a self-built **3D bin-packing / cartonization solution**. Each record is one request/response pair from iHub's existing packing service, provided as reference input/output for the team to benchmark their own solver against.

> **Data source & privacy:** Real iHub order data. `OrderId`, `OrderNo`, and item `Code` values are **masked**. No PII is included.

## Dataset Versions

| File | Records | Candidate boxes | Notes |
| --- | ---: | ---: | --- |
| `data_sample_v1.json` | 2,000 | 7 | Original benchmark with Box2 to Box9 catalogue including Box3 |
| `data_samples_v2.json` | 2,000 | 6 | Same order scenarios rerun after Box3 was removed and Box2 length increased |

See [`CHANGELOG.md`](CHANGELOG.md) for the detailed comparison between dataset versions.

## At a Glance

| Property | Value |
| --- | --- |
| Structure | JSON array; each element = one packing request/response |
| Top-level keys per record | `input`, `output`, `latency_ms` |
| Units | Dimensions in **mm**, weight in **kg** |
| Optimization mode | `bins_number` |
| Result status | All 2,000 records in both supplied versions succeeded; `NotPackedItems` is empty |

## Record Shape

```json
{
  "input":  { "OrderId": 1, "OrderNo": "1", "Items": { ... }, "Bins": { ... }, "OptimizationMode": "bins_number" },
  "output": { "StatusCode": 0, "StatusMessage": "Success", "Data": { ... } },
  "latency_ms": 232.59
}
```

## `input`

### `Items.ItemsList[]` — items to pack

| Field | Type | Notes |
| --- | --- | --- |
| `Code` | string | Masked item identifier |
| `Length`, `Width`, `Height` | number | Item dimensions in mm |
| `Weight` | number | Item weight in kg |
| `UOM` | string | Unit of measure such as `EA`, `BOX`, `SET`, `PACK`, `BTL`, `PCS` |
| `VerticalRotation` | int (`1`/`0`) | `1` = item may be laid down / rotated onto its vertical axis; `0` = must stay upright |
| `Quantity` | int | Count of this item |

### `Bins.BinsList[]` — candidate boxes

The candidate box catalogue is supplied as part of each request and must be treated as configurable solver input rather than a permanent hard-coded list.

#### v1 catalogue

| Code | Length | Width | Height |
| --- | ---: | ---: | ---: |
| Box2 | 220 | 170 | 115 |
| Box3 | 270 | 180 | 180 |
| Box4 | 340 | 260 | 150 |
| Box5 | 340 | 260 | 235 |
| Box6 | 340 | 260 | 280 |
| Box8 | 290 | 180 | 280 |
| Box9 | 440 | 345 | 280 |

#### v2 catalogue

| Code | Length | Width | Height |
| --- | ---: | ---: | ---: |
| Box2 | 270 | 170 | 115 |
| Box4 | 340 | 260 | 150 |
| Box5 | 340 | 260 | 235 |
| Box6 | 340 | 260 | 280 |
| Box8 | 290 | 180 | 280 |
| Box9 | 440 | 345 | 280 |

All supplied boxes have `MaxWeight = 20 kg` in both versions.

### `Bins.Parameters` — packing rules

| Field | Example | Meaning |
| --- | --- | --- |
| `BinMaxFillCheckMinItemQty` | 6 | Item-count threshold. If an order has six or fewer physical items, the bin may pack to full volume. The fill cap applies only when the count is greater. Should remain configurable. |
| `BinMaxFillPct` | 70 | Maximum volumetric fill percentage for larger orders. Should remain configurable. |
| `BinBuffer` | `{Length:0, Width:0, Height:6}` | Clearance reserved inside the bin in mm. The 6 mm value is Z-height headroom. Should remain configurable. |

### `OptimizationMode`

`bins_number` is used throughout both supplied datasets and represents minimizing the number of bins.

## `output`

| Field | Type | Notes |
| --- | --- | --- |
| `StatusCode` / `StatusMessage` | int / string | `0` / `Success` for all supplied records |
| `Data.OrderId`, `Data.OrderNo` | — | Echoed from input |
| `Data.BinsPacked[]` | array | One entry per box used for the order |
| `Data.NotPackedItems[]` | array | Items that could not be packed; empty in all supplied records |

### `Data.BinsPacked[]`

| Field | Type | Notes |
| --- | --- | --- |
| `Code` | string | Selected candidate box |
| `UsedSpace` | number | Volumetric fill of that box (%) |
| `Items[]` | array | Items assigned to the box; mirrors input item fields and returns `VerticalRotation` as boolean |

## `latency_ms`

Full round-trip time of the request in milliseconds.

## Notes for the Project Team

The two versions intentionally demonstrate why the solver should not assume a fixed catalogue. v2 contains the same 2,000 order and item scenarios as v1 but changes the available boxes. This causes valid reference box selections and utilization values to change without changing the underlying orders.

Every supplied record is a solved, feasible case. These are useful benchmark outputs but should not be treated as proof of mathematical optimality. The team should also design edge cases and failure cases as part of the solution.

`VerticalRotation`, `BinMaxFillCheckMinItemQty`, `BinMaxFillPct`, `BinBuffer`, box dimensions, and box weight limits are the main supplied constraints to reproduce while keeping them configurable.
