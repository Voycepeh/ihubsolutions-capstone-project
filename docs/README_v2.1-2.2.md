# Carton Selection Engine – Capstone 2.1 and 2.2

Follow-up to the v1.6 – v1.9 write-up. Version 2.0 added physical (support) rules; **v2.1 aligns the fill-cap rule with the iHub specification**, and **v2.2 adds a carton-combination search** that closes most of the gap to the exact solver while staying fast.

The solver chooses cartons for one order at a time: which items go together, which carton sizes are used, and how many cartons are needed. Priority: fewest cartons, then the smallest largest-carton, then the smallest total carton volume.

---

## Pipeline (v2.2)

```
items of ONE order
   │
   ├─ pre-screen: items that cannot fit any empty carton → "unpackable"
   │
   ├─ repeat until the pool is empty
   │     plan = volumetric planner (batches + best-fit carton, fill cap applied)
   │     3D check of each batch: carton from the assigned one upward; first carton that packs the whole batch wins;
   │     otherwise commit the carton that packs the most volume and re-plan the leftovers
   │
   └─ NEW in v2.2 – carton-combination search (refine)
         list carton combinations strictly better than the current plan, in objective order
         (count → largest carton volume → total carton volume);
         try to pack ALL items into each one with many item orderings on the "full" 3D engine;
         first success replaces the plan
```

Everything runs **per order**. Items from different orders are never combined.

---

## What changed

### v2.1 – fill-cap basis (`fill_cap_basis`)
- **Problem found:** the iHub spec says the item count of the **whole order** decides the fill cap, and the cap then applies to **every carton** of that order. Earlier notebooks applied it per carton, which is more permissive for multi-carton orders.
- **Fix:** new setting `fill_cap_basis`, default `"order"` (spec). `"carton"` reproduces v2.0 exactly.
- **Evidence the order-level reading is right:** in iHub's own results, only 1 of 119 cartons holding ≤ 6 items (inside orders with more than 6 items) goes above 70 % fill. Its 183 cap failures are all Box9.
- **Effect on the 2,000-order sample:** 13 orders changed; average cartons stayed at 1.1075 (fill 46.42 % → 46.41 %).
- **Checks:** with `fill_cap_basis="carton"` the results match v2.0 exactly in four configurations; an independent audit with the order-level cap found 0 violations in 2,215 cartons.

### v2.2 – carton-combination search (`refine`)
- **Why:** the 3D engine was able to pack most of the cartons that iHub used, but my pipeline did not try enough item orderings and carton combinations. In a test on the orders where v2.1 was weaker, the engine reproduced 6 of 94 iHub cartons by default, 16 with the stronger engine, and **67 with 100 random item orders added**.
- **How:** after the normal pipeline, `_refine_cartons` enumerates carton combinations in the same order an exact solver would, keeps only those strictly better than the current plan, and tries each one with 4 fixed + `refine_tries` random item orderings. The first feasible combination replaces the plan. Weight and fill-cap volume checks prune combinations before any 3D work.
- **New settings:** `refine` (default `True`), `refine_tries` (40), `refine_budget_ms` (120 ms per order).
- **New outputs:** result field `refined`, helper `compare_refine()`, and the `run_refine` benchmark flag.
- **Usability fix:** the data loader now searches the working folder, `data/raw/`, `data/` and parent folders, and **stops with a clear error** when the file is missing. The 2 demo orders are used only with `allow_sample=True`.
- **Checks:** with `refine=False` the results match v2.1 exactly. An independent audit of all 2,000 orders (2,213 cartons, 15,103 items) found **0 violations**.

### Carried over from v2.0 (needed to read the defaults)
- **Support rule:** `min_support_ratio=0.5` – at least 50 % of an item's base must rest on the carton floor or on items directly below it. Applied in every engine mode.
- **Fragility and load-bearing** rules exist as options but are **off** (not a concern in this application).
- Cost of the support rule on the sample at a 70 % cap: no extra cartons at 0.5; at full support (1.0) about +2.6 % carton volume and 2 orders with an extra carton.

---

## Configuration (`Config`, defaults as of v2.2)

| Field | Default | Meaning |
|---|---|---|
| `bin_max_fill_pct` | `70.0` | Fill cap in % of usable volume. User-defined; must be in (0, 100]. |
| `bin_max_fill_check_min_item_qty` | `6` | The cap applies when the order has more items than this. |
| `bin_buffer_h` | `6.0` | Height buffer subtracted from every carton (mm). |
| `fill_cap_basis` | `"order"` | `"order"` (iHub spec) or `"carton"` (earlier behaviour). |
| `orientation_mode` | `"tall_first"` | Rotation preference: `legacy`, `original_first`, `low_height`, `tall_first`. |
| `item_order` | `"multi"` | Item order fed to the 3D engine: `volume`, `height`, `multi`. |
| `ep_mode` | `"auto"` | Candidate points: `basic`, `full`, `auto` (basic, retried with full on forced splits). |
| `backfill` | `False` | Fill an open carton's free space with remaining items (negligible gain). |
| `min_support_ratio` | `0.5` | Minimum supported share of an item's base. `0` = off, `1` = full support. |
| `enforce_fragility` / `enforce_load_bearing` | `False` / `False` | Optional rules, unused here. |
| `auto_stack_factor` | `2.5` | Used only when load-bearing is on. |
| `refine` | `True` | Carton-combination search (v2.2). |
| `refine_tries` | `40` | Random item orderings per carton combination. |
| `refine_budget_ms` | `120.0` | Time cap per order for the search. |

Invalid values raise `ValueError`.

---

## Usage

```python
config = Config()                                   # or Config(bin_max_fill_pct=80.0, refine=False, ...)
result = solve_order_best_fit(order, DEFAULT_BOXES, config, return_layout=True)
# result: status, total_cartons, cartons_used, total_items, unpacked_items, average_fill_pct, carton_volume,
#         planner_status, planner_cartons, box_upgrades, forced_splits, rounds, backfilled_items,
#         refined, runtime_ms, layout (x, y, z, l, w, h per item)

run_benchmark_and_print("data_samples_v2.json")     # summary + sweeps + experiments (takes a few minutes)
```

`status` is `single_box_fit`, `multi_box_split`, `unpackable` or `empty`.

**Data file:** the notebook looks for the dataset in the working folder, `data/raw/`, `data/` and the parent folders. If it cannot find it, it raises an error that shows the current folder and its files. Pass a full path if needed. The dataset is not part of this repository.

**Benchmark flags** of `run_benchmark_and_print`: `run_sweep`, `run_orientation`, `run_backfill`, `run_engines` (off), `run_item_orders` (off), `run_engine_sweep`, `run_physical`, `run_refine`, `allow_sample`.

---

## Results on the 2,000-order sample

Reference: the iHub results contained in the dataset. 183 of its results exceed the fill cap (all Box9), so quality is compared on the **1,817 cap-compliant orders**, using the objective *(cartons, largest carton volume, total carton volume)*. Latency of all solvers was measured on the same single-core machine.

| Solver | Objective vs iHub (better / equal / worse) | Cartons vs iHub (fewer / same / more) | Carton volume vs iHub | Latency median / P95 / mean (ms) |
|---|---|---|---|---|
| Exact solver "Best" (CP-SAT, separate repo) | 67 / 1750 / **0** | 2 / 1815 / 0 | −1.73 % | 24.5 / 410 / 76 |
| **Mine v2.2** | 49 / 1735 / 33 | 1 / 1811 / 5 | −0.66 % | **0.55 / 15.6 / 3.2** |
| Mine v2.1 | 28 / 1699 / 90 | 1 / 1809 / 7 | +1.12 % | 0.24 / 1.0 / 0.4 |
| Heuristic "Fast" (separate repo) | 18 / 1514 / 285 | 1 / 1779 / 37 | +5.98 % | 2.4 / 33.7 / 6.2 |

- Average cartons per order (all 2,000): Best 1.1035, **v2.2 1.1065**, v2.1 1.1075.
- **v2.2 vs Best on all 2,000 orders:** better / equal / worse = 2 / 1883 / 115; cartons fewer / same / more = 0 / 1994 / 6.
- The search replaced the plan in **168 orders**; 0 orders are unpackable.
- Best proved optimality for 1,981 of 2,000 orders on this machine (1,900 in the saved notebook of the other repo, run on slower hardware).

### Physical realism of the solvers (independent audit of the returned layouts)

| Solver | Rule violations | Items under 50 % base support | Orders with at least one such item |
|---|---|---|---|
| Mine (v2.0 – v2.2) | none | **0 %** | 0 % |
| Fast | none | 3.0 % | 16.9 % |
| Best | none | **24.4 %** | **72.8 %** |

The separate repo's current Fast / Best contain **no support or gravity rule**; its earlier first-fit prototype did (`min_support_ratio = 0.8`). With the support rule switched off, v2.1 compares as 30 / 1707 / 80 against iHub, so the rule accounts for only about 10 of the weaker orders.

### Other reference points
- The repo's historical first-fit prototype: 1.1070 average cartons, +0.75 % carton volume vs iHub (support 0.8).
- Where v2.2 is still weaker than iHub (33 orders): mostly Box5 → Box6 (16) and Box8 → Box5 (10).

---

## Validation

Checked on all 2,000 orders (and on every changed order for the search), **0 violations**:
no overlapping items, every item inside the carton (including the 6 mm buffer), carton weight ≤ max weight, fill cap respected (order-level rule), upright-only items keep their height, support ≥ `min_support_ratio`, and every item is either placed or reported as unpacked.

These checks were run as scripts and are **not yet automated tests in the repository**. The iHub results are a reference, not ground truth: 183 of them break the cap and they contain no coordinates, so their layouts cannot be re-checked.

---

## Known limitations

- **Heuristic search.** A carton combination that `refine` does not find is not proven infeasible. The exact solver proves optimality for 1,981 of 2,000 orders.
- **One data sample.** Defaults were chosen on the same 2,000 orders. There is no separate hold-out sample yet.
- **Search settings not tuned.** `refine_tries = 40` and `refine_budget_ms = 120` were not swept.
- **Simple support rule.** It checks base area only: no centre-of-gravity or stacking-weight check (those rules are off).
- **Sample properties.** About 74 orders sit between 70 % and 75 % of Box9's usable volume (65 at exactly 71.1 %), which makes results change sharply between a 70 % and a 75 % cap. Check whether this cluster is real before tuning the cap to it.
- **Latency** was measured in a sandbox and covers solving only.
- Missing or zero dimensions get volume 0 and pack silently; the per-order `Bins` list is ignored (all orders use the same six cartons); only the `bins_number` optimisation mode is handled.

## Next steps

1. Sweep `refine_tries` and `refine_budget_ms` to find where the gains flatten.
2. Add best-fit placement scoring to the 3D engine (score all feasible placements instead of taking the first) and measure it.
3. Hold-out evaluation on orders not used for tuning.
4. Turn the validation scripts into automated tests; add input validation (zero or missing dimensions).
5. Test whether a gravity-drop repair of the exact solver's layouts can satisfy the support rule, for a like-for-like comparison.

## Files

| File | Content |
|---|---|
| `capstone2_0.ipynb` | Physical constraints (support, fragility, load bearing) – background |
| `capstone2_1.ipynb` | Fill-cap basis aligned with the iHub specification |
| `capstone2_2.ipynb` | Carton-combination search, robust data loader |

Notebook cell order: imports → data classes, `Config`, `DEFAULT_BOXES` → volumetric planner → 3D engine → unified pipeline + carton-combination search → benchmark and experiments.
