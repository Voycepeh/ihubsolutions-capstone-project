# Raw Dataset Changelog

This changelog records changes between the iHub benchmark datasets stored under `data/raw/`.

## v2 — `data_samples_v2.json`

The v2 dataset contains the same 2,000 masked order scenarios as v1, rerun against an updated candidate box catalogue.

### What changed

| Area | v1 | v2 |
| --- | --- | --- |
| Orders | 2,000 | 2,000 |
| Order and item inputs | Same | Same |
| Candidate box types | 7 | 6 |
| Box2 | 220 × 170 × 115 mm | 270 × 170 × 115 mm |
| Box3 | 270 × 180 × 180 mm | Removed |
| Box4, Box5, Box6, Box8, Box9 | Unchanged | Unchanged |
| Maximum weight | 20 kg per box | 20 kg per box |
| Fill threshold | More than 6 physical items | More than 6 physical items |
| Maximum fill above threshold | 70% | 70% |
| Bin buffer | 0 × 0 × 6 mm | 0 × 0 × 6 mm |
| Optimization mode | `bins_number` | `bins_number` |

### Benchmark output impact

All 2,000 orders remain successful and no orders contain unpacked items. The number of cartons used per order is unchanged between v1 and v2.

The item grouping across cartons is also unchanged. The output differences are driven by the revised catalogue, particularly removal of Box3 and the larger Box2.

Across the 2,000 records:

| Change | Records |
| --- | ---: |
| Selected box code changed | 366 |
| Output JSON changed, including utilization changes | 702 |
| Box3 uses in v1 | 366 |
| Box3 uses in v2 | 0 |

Every v1 Box3 use was replaced in v2:

| v1 → v2 | Orders |
| --- | ---: |
| Box3 → Box4 | 277 |
| Box3 → Box2 | 59 |
| Box3 → Box8 | 21 |
| Box9 + Box3 → Box9 + Box4 | 8 |
| Box9 + Box3 → Box9 + Box8 | 1 |
| Total | 366 |

Box usage therefore shifts as follows:

| Box | v1 uses | v2 uses | Difference |
| --- | ---: | ---: | ---: |
| Box2 | 336 | 395 | +59 |
| Box3 | 366 | 0 | -366 |
| Box4 | 221 | 506 | +285 |
| Box5 | 258 | 258 | 0 |
| Box6 | 180 | 180 | 0 |
| Box8 | 303 | 325 | +22 |
| Box9 | 470 | 470 | 0 |

`UsedSpace` also changes for existing Box2 selections because its volume increased. These utilization changes do not indicate different order inputs.

### Project implication

The box catalogue must be treated as request configuration rather than a fixed solver constant. The same order workload can produce different valid carton choices when the catalogue changes.

Both versions are retained so the team can benchmark solver behaviour against catalogue changes without losing the original reference run.

## v1 — `data_sample_v1.json`

Original 2,000-record iHub benchmark supplied to the project. It contains seven candidate box types and successful reference outputs for every order.
