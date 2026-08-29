# iHub Solutions Capstone Project

NUS Industry 4.0 Master's capstone project developing a self built 3D bin packing and cartonization solution for iHub.

## Project objective

The project aims to design and evaluate our own 3D bin packing solver using historical request and response examples from iHub's existing packing service as a benchmark.

The reference service receives order items, candidate cartons and configurable packing rules, then returns the cartons selected and the items assigned to each carton. The main optimization mode in the provided dataset is `bins_number`, which means minimizing the number of cartons used.

## Core packing constraints

The solution should reproduce the important operational rules present in the reference data:

1. Item dimensions in millimetres.
2. Item weight in kilograms.
3. Carton dimensions and maximum weight.
4. Item quantity.
5. `VerticalRotation`, including items that must remain upright.
6. `BinMaxFillCheckMinItemQty`, which controls when the maximum fill rule applies.
7. `BinMaxFillPct`, the configurable volumetric fill limit for larger orders.
8. `BinBuffer`, the configurable internal clearance reserved inside a carton.

## Reference dataset

The provided sample dataset contains 2,000 masked real iHub order request and response pairs.

| Property | Value |
| --- | --- |
| Records | 2,000 |
| Format | JSON array |
| Units | mm for dimensions, kg for weight |
| Candidate cartons | 7 fixed boxes, Box2 to Box9 |
| Optimization mode | `bins_number` |
| Result status | All 2,000 successful |
| Unpacked items | None in the supplied sample |
| Privacy | Order and item identifiers masked, no PII |

The dataset is useful as a reference benchmark for carton selection, number of cartons, volumetric utilization and latency. Because every supplied case is feasible and successful, the team should also create its own edge cases and failure cases.

The development dataset and its supplied README are kept together under [`data/raw/`](data/raw/). See [`docs/dataset-specification.md`](docs/dataset-specification.md) for the consolidated field and constraint reference.

## Repository structure

```text
project-root/
├── data/
│   └── raw/
├── notebooks/
├── src/
├── deployment/
├── docs/
└── README.md
```

| Folder | Purpose |
| --- | --- |
| `data/` | Development datasets used by the project. |
| `notebooks/` | Exploration, solver experiments, benchmarking and analysis. |
| `src/` | Reusable packing, validation, evaluation and utility code. |
| `deployment/` | Demo application, API, dashboard or other deployment assets. |
| `docs/` | Dataset specification, design notes, reports, presentation materials and project documentation. |

## Data handling

This capstone repository is intended to contain development data used by the team. Development datasets may therefore be committed under `data/` so everyone can work with the same reproducible inputs.

The supplied sample comes from real iHub orders, but the development copy has masked `OrderId`, `OrderNo` and item `Code` values and contains no PII.

Do not commit production data, unmasked data, confidential or restricted data, PII, credentials, secrets or any dataset that the team is not authorised to place in this repository.

## Benchmarking direction

A useful comparison against the existing service should consider at least:

1. Whether all items are packed successfully.
2. Number of cartons used.
3. Carton type selected.
4. Volumetric utilization through `UsedSpace` or an equivalent metric.
5. Compliance with rotation, weight, buffer and fill constraints.
6. Runtime or latency.

Matching the reference output exactly is not automatically the goal. A self developed solver may produce a different valid arrangement or carton combination while still meeting the project objective. Evaluation should therefore distinguish feasibility, constraint compliance and optimization quality.

## Team workflow

Local setup and contribution guidance are kept in [`CONTRIBUTING.md`](CONTRIBUTING.md).

AI agents working in this repository must follow [`AGENTS.md`](AGENTS.md).
