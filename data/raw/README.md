# 3D Bin-Packing Sample Dataset (`data_sample_v1.json`)

Sample dataset for the **NUS Industry 4.0 (i4.0) Master's project** developing a self-built **3D bin-packing / cartonization solution**. Each record is one request/response pair from iHub's existing packing service, provided as reference input/output for the team to benchmark their own solver against.

> **Data source & privacy:** Real iHub order data. `OrderId`, `OrderNo`, and item `Code` values are **masked**. No PII is included.

---

## At a Glance

| Property | Value |
|---|---|
| Records | 2,000 |
| Structure | JSON array; each element = one packing request/response |
| Top-level keys per record | `input`, `output`, `latency_ms` |
| Units | Dimensions in **mm**, weight in **kg** |
| Candidate bins | 7 fixed boxes (`Box2`–`Box9`), identical across all records |
| Optimization mode | `bins_number` (all records) |
| Result status | All 2,000 succeeded; `NotPackedItems` empty in every record |

---

## Record Shape

```json
{
  "input":  { "OrderId": 1, "OrderNo": "1", "Items": { ... }, "Bins": { ... }, "OptimizationMode": "bins_number" },
  "output": { "StatusCode": 0, "StatusMessage": "Success", "Data": { ... } },
  "latency_ms": 232.59
}
```

---

## `input`

### `Items.ItemsList[]` — items to pack
| Field | Type | Notes |
|---|---|---|
| `Code` | string | Masked item identifier |
| `Length`, `Width`, `Height` | number | Dimension of items in mm |
| `Weight` | number | Weight of items in kg |
| `UOM` | string | Unit of measure: `EA`, `BOX`, `SET`, `PACK`, `BTL`, `PCS` |
| `VerticalRotation` | int (`1`/`0`) | `1` = item may be laid down / rotated onto its vertical axis; `0` = **must stay upright** (cannot be packed lying down) |
| `Quantity` | int | Count of this item |

### `Bins.BinsList[]` — candidate boxes
Fixed set of 7 boxes (same in every record). `MaxWeight` = 20 kg for all.

| Code | Length | Width | Height |
|---|---|---|---|
| Box2 | 220 | 170 | 115 |
| Box3 | 270 | 180 | 180 |
| Box4 | 340 | 260 | 150 |
| Box5 | 340 | 260 | 235 |
| Box6 | 340 | 260 | 280 |
| Box8 | 290 | 180 | 280 |
| Box9 | 440 | 345 | 280 |

*(mm; MaxWeight 20 kg each)*

### `Bins.Parameters` — packing rules
| Field | Example | Meaning |
|---|---|---|
| `BinMaxFillCheckMinItemQty` | 6 | Item-count threshold. If an order has **≤ this many** items, the bin may pack to **100%**. Only when the count is **greater** does `BinMaxFillPct` apply. **Should be configurable.** |
| `BinMaxFillPct` | 70 | Max volumetric fill (%) allowed for larger orders. **Should be configurable.** |
| `BinBuffer` | `{Length:0, Width:0, Height:6}` | Clearance reserved inside the bin, in mm. The 6 mm here is **Z-height** headroom for physical packing. **Should be configurable.** |

### `OptimizationMode`
Always `bins_number` in this dataset (minimize number of bins). No other modes are relevant here.

---

## `output`

| Field | Type | Notes |
|---|---|---|
| `StatusCode` / `StatusMessage` | int / string | `0` / `Success` for all records |
| `Data.OrderId`, `Data.OrderNo` | — | Echoed from input (masked) |
| `Data.BinsPacked[]` | array | One entry per box used for the order |
| `Data.NotPackedItems[]` | array | Items that could not be packed (empty across this dataset) |

### `Data.BinsPacked[]`
| Field | Type | Notes |
|---|---|---|
| `Code` | string | Chosen box (one of Box2–Box9) |
| `UsedSpace` | number | Volumetric fill of that box (%). Fill limit is governed by the configurable `Parameters` above. |
| `Items[]` | array | Items assigned to the box. Mirrors input item fields; `VerticalRotation` is returned as boolean (`true`/`false`). |

---

## `latency_ms`
Full round-trip time of the request (ms).

---

## Notes for the Project Team
- Bins and their dimensions are constant across all 2,000 records, so a solver can treat the box catalog as fixed.
- Every record is a solved, feasible case (all `Success`, nothing left unpacked) — useful as ground-truth targets when comparing box selection and fill against a self-developed solver.
- Do design your own edge and fail cases as part of the solution
- `VerticalRotation`, `BinMaxFillCheckMinItemQty`, `BinMaxFillPct`, and `BinBuffer` are the key constraints to reproduce; buffers and fill caps are intended to be configurable.
