# Dataset Specification

## Purpose

`data_sample_v1.json` is the reference dataset for the NUS Industry 4.0 Master's project developing a self built 3D bin packing and cartonization solution for iHub.

Each record contains one request to iHub's existing packing service, the corresponding response and the measured round trip latency. The dataset is intended to help the team understand the existing service behaviour and benchmark its own solver.

## Data source and privacy

The dataset contains real iHub order data with `OrderId`, `OrderNo` and item `Code` values masked. No PII is included.

The actual JSON data must remain local under `data/raw/` and should not be committed to GitHub.

## Dataset summary

| Property | Value |
| --- | --- |
| Records | 2,000 |
| Structure | JSON array |
| Top level keys | `input`, `output`, `latency_ms` |
| Dimension unit | mm |
| Weight unit | kg |
| Candidate cartons | 7 fixed boxes |
| Optimization mode | `bins_number` |
| Result status | All successful |
| `NotPackedItems` | Empty for all supplied records |

## Record structure

```json
{
  "input": {
    "OrderId": 1,
    "OrderNo": "1",
    "Items": {},
    "Bins": {},
    "OptimizationMode": "bins_number"
  },
  "output": {
    "StatusCode": 0,
    "StatusMessage": "Success",
    "Data": {}
  },
  "latency_ms": 232.59
}
```

## Input items

Items are stored under `input.Items.ItemsList[]`.

| Field | Type | Meaning |
| --- | --- | --- |
| `Code` | string | Masked item identifier |
| `Length` | number | Item length in mm |
| `Width` | number | Item width in mm |
| `Height` | number | Item height in mm |
| `Weight` | number | Item weight in kg |
| `UOM` | string | Unit of measure such as `EA`, `BOX`, `SET`, `PACK`, `BTL`, `PCS` |
| `VerticalRotation` | int | `1` allows the item to be laid down or rotated onto its vertical axis; `0` means it must remain upright |
| `Quantity` | int | Number of units of that item |

## Candidate cartons

The same seven candidate cartons appear in every supplied record. All have `MaxWeight = 20 kg`.

| Code | Length | Width | Height | MaxWeight |
| --- | ---: | ---: | ---: | ---: |
| Box2 | 220 | 170 | 115 | 20 |
| Box3 | 270 | 180 | 180 | 20 |
| Box4 | 340 | 260 | 150 | 20 |
| Box5 | 340 | 260 | 235 | 20 |
| Box6 | 340 | 260 | 280 | 20 |
| Box8 | 290 | 180 | 280 | 20 |
| Box9 | 440 | 345 | 280 | 20 |

Dimensions are in mm and maximum weight is in kg.

## Packing parameters

The request includes configurable packing rules under `input.Bins.Parameters`.

### `BinMaxFillCheckMinItemQty`

Example value: `6`.

If the order contains no more than this number of items, a carton may pack to 100 percent volumetric fill. `BinMaxFillPct` applies only when the order item count is greater than this threshold.

This parameter should remain configurable.

### `BinMaxFillPct`

Example value: `70`.

This is the maximum volumetric fill percentage allowed for orders above the item count threshold.

This parameter should remain configurable.

### `BinBuffer`

Example value:

```json
{
  "Length": 0,
  "Width": 0,
  "Height": 6
}
```

The buffer reserves clearance inside the carton. In the supplied dataset the 6 mm height buffer represents Z axis headroom for physical packing.

The buffer should remain configurable.

## Optimization mode

Every supplied record uses:

```text
bins_number
```

For this dataset, the optimization objective is to minimize the number of cartons used. No other optimization modes are relevant to the supplied sample.

## Output

The reference response contains:

| Field | Meaning |
| --- | --- |
| `StatusCode` | `0` for all supplied records |
| `StatusMessage` | `Success` for all supplied records |
| `Data.OrderId` | Echoed masked order identifier |
| `Data.OrderNo` | Echoed masked order number |
| `Data.BinsPacked[]` | Cartons selected and items assigned to them |
| `Data.NotPackedItems[]` | Items the service could not pack |

`Data.NotPackedItems[]` is empty for every supplied record.

## Packed carton output

Each entry in `Data.BinsPacked[]` contains:

| Field | Meaning |
| --- | --- |
| `Code` | Selected carton code |
| `UsedSpace` | Volumetric fill percentage for the carton |
| `Items[]` | Items assigned to the carton |

The item fields mirror the request fields. `VerticalRotation` is returned as a boolean in the response.

## Latency

`latency_ms` records the full round trip time for the request in milliseconds.

Latency can be used as one benchmark when comparing the team's implementation with the existing service, while recognizing that local execution conditions may differ from the reference environment.

## How the dataset should be used

The supplied responses can act as reference targets for:

1. Feasible packing.
2. Number of cartons used.
3. Carton selection.
4. Item assignment across cartons.
5. Volumetric utilization.
6. Approximate runtime behaviour.

A new solver does not necessarily need to reproduce the exact same geometric arrangement. Multiple valid 3D packing arrangements may satisfy the same constraints.

Evaluation should therefore distinguish whether a solution is valid from whether it exactly matches the reference response.

## Dataset limitations

All 2,000 supplied records are successful and feasible. There are no examples of items that cannot be packed.

The team should deliberately design additional edge and failure cases, including examples that test:

1. Items larger than every available carton.
2. Orders exceeding carton weight limits.
3. Upright only items where orientation prevents packing.
4. Orders around the `BinMaxFillCheckMinItemQty` threshold.
5. Orders around the `BinMaxFillPct` boundary.
6. Buffer values that materially change feasibility.
7. Orders requiring multiple cartons.
8. Cases where one or more items remain unpacked.

These additional cases are needed to validate solver behaviour beyond the successful reference sample.
