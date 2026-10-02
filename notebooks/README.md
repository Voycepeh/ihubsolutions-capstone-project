# packer_first_fit.py

A 3D carton-packing engine using **extreme-point placement** with **first-fit** bin
selection, plus a dataset runner that scores results against a historical
ground-truth file. Single file, standard library + pandas only.

## What it does

Given an order (a list of items, each with dimensions, weight, quantity, and
whether it can be rotated) and a box catalogue, it decides:

- which box(es) the order needs,
- where each physical item goes inside each box (x, y, z position + orientation),
- and whether anything couldn't be packed at all.

It then validates its own output against hard constraints (no overlap, stays
in bounds, respects weight/fill limits, upright-only items stay upright,
nothing floats unsupported) so a result is never just "trusted."

## Algorithm

1. **Expand** each order line's `Quantity` into individual physical units.
2. **Filter** out any unit that can never fit any box, in any orientation —
   flagged as unpacked immediately with a reason.
3. **Place** items into a candidate box using extreme-point placement
   (Crainic, Perboli, Tadei 2008): track the exposed corners left by each
   placed item, and try the next item at those corners. Four item orderings
   × four placement policies are tried per box; the first combination that
   packs everything wins.
4. **Select** a box via **first fit**: among boxes that hold the whole
   remaining set, pick the smallest one.
5. **Split** across multiple cartons when nothing holds everything: branch on
   the most promising boxes, recurse on the leftover items, and keep
   whichever full plan uses the fewest cartons (then least total volume).
6. **Validate** the final result independently before returning it.

## Requirements

- Python 3.9+
- `pandas`

```bash
pip install pandas
```

## Usage

Place your dataset JSON in the same folder as the script, then:

```bash
python packer_first_fit.py                      # looks for data_sample_v1.json here
python packer_first_fit.py path/to/file.json     # or point it at a specific file
python packer_first_fit.py --limit 100           # quick trial on the first 100 orders
python packer_first_fit.py --check-order-sensitivity   # confirm results don't depend on item input order
```

Each run prints a summary to the console and writes `results_first_fit.csv`
(one row per order) next to the script.

### Using it as a library

```python
from packer_first_fit import Item, Box, Config, pack_order, validate_result

boxes = [Box("Box5", 340, 260, 235, 20)]
items = [Item("BOOK", 210, 150, 30, 0.8, quantity=4)]

result = pack_order(items, boxes, Config())
print(result.status, result.carton_count)
print(validate_result(result, Config()))   # [] means no violations
```

## Input data format

One JSON array of order records. Each record needs at minimum:

```json
{
  "input": {
    "OrderId": 1,
    "Items": { "ItemsList": [
      { "Code": "63", "Length": 140, "Width": 80, "Height": 116,
        "Weight": 0.285, "Quantity": 1, "VerticalRotation": 1 }
    ]},
    "Bins": {
      "BinsList": [
        { "Code": "Box2", "Length": 270, "Width": 170, "Height": 115, "MaxWeight": 20 }
      ],
      "Parameters": {
        "BinMaxFillCheckMinItemQty": 6,
        "BinMaxFillPct": 70,
        "BinBuffer": { "Length": 0, "Width": 0, "Height": 6 }
      }
    }
  },
  "output": {
    "Data": { "BinsPacked": [ { "Code": "Box2", "UsedSpace": 28.99 } ] }
  },
  "latency_ms": 410.02
}
```

`output` and `latency_ms` are optional — they're only used for comparing
against a historical ground truth. If a record's `Bins.BinsList` is missing,
the script falls back to a built-in 6-box catalogue (`DEFAULT_BOXES`).

## Output columns (`results_first_fit.csv`)

| Column | Meaning |
|---|---|
| `order_id` | Order identifier |
| `item_count` | Total physical items (quantity expanded) |
| `status` | `PACKED`, `PARTIAL`, or `FAILED` |
| `cartons_ours` / `cartons_hist` | Carton count: this engine vs. historical data |
| `boxes_ours` / `boxes_hist` | Which box codes were used, each side |
| `carton_volume_ours_L` / `carton_volume_hist_L` | Total carton volume in litres |
| `avg_util_ours` / `avg_util_hist` | Average % of usable volume filled |
| `unpacked` | Items that couldn't be placed |
| `runtime_ms` | This engine's time for the order |
| `latency_hist_ms` | Historical system's recorded time, if present |
| `violations` | Rule violations found by the independent validator (should always be 0) |

## Configuration (`Config`)

| Field | Default | Meaning |
|---|---|---|
| `bin_buffer_length/width/height` | `0, 0, 6` | mm subtracted from each usable interior dimension |
| `bin_max_fill_pct` | `70.0` | Max % of usable volume a carton may fill |
| `bin_max_fill_check_min_item_qty` | `6` | Fill cap only applies above this many items in the order |
| `max_box_weight` | `20.0` | Global per-carton weight cap (kg) |
| `min_support_ratio` | `0.8` | Minimum share of an item's base that must rest on something below it |
| `use_compaction` | `True` | Slide placed items against neighbours to keep free space contiguous |
| `multi_box_branching` | `3` | How many candidate boxes the multi-carton search explores per level |
| `max_seconds_per_order` | `1.0` | After this, the search stops exploring alternatives and finishes greedily |

Per-order values for the buffer, fill %, and item-count threshold are read
from each record's own `Bins.Parameters` when present, overriding these
defaults.

## Known limitations

- **First fit and best fit currently converge.** Because box selection only
  ranks boxes that already hold the *entire* remaining set, the smallest
  box and the fullest box are mathematically the same choice — so a
  first-fit and a best-fit build of this engine will produce identical
  output on any dataset. A separate `packer_best_fit.py` exists with the
  same interface for when that assumption changes.
- **No geometric solver fallback.** Very oddly-shaped orders that are
  theoretically packable with a cleverer layout may still report `PARTIAL`
  if none of the four orderings × four placement policies finds it.
- **Runtime is bounded, not instant.** Orders needing many cartons can take
  up to `max_seconds_per_order` seconds before the search gives up on
  finding a better combination and finishes greedily.

## Validation

`validate_result()` independently re-checks every placement: bounds,
overlap, support, upright-orientation compliance, weight limits, and the
fill-percentage rule. A non-empty list means something is wrong with the
*engine*, not the input data — this should never happen on valid input.
