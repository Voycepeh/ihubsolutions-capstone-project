# AGENTS.md

This repository contains an NUS Industry 4.0 Master's capstone project developing a self built 3D bin packing and cartonization solution for iHub.

## Read first

1. Read `README.md` for the project objective and repository structure.
2. Read `docs/dataset-specification.md` before changing packing logic, data interpretation, evaluation criteria or test cases.
3. Read `CONTRIBUTING.md` before adding project files.

## Repository structure

Use the existing top level folders:

1. `data/` for development datasets used by the project.
2. `notebooks/` for exploration, solver experiments and benchmarking.
3. `src/` for reusable application and solver code.
4. `deployment/` for demo, API, dashboard or deployment assets.
5. `docs/` for specifications, reports and project documentation.

Do not create new top level folders unless a human teammate explicitly asks for one.

## Data safety

Development datasets for this capstone may be committed under `data/` so the team can work with reproducible inputs.

The supplied `data/raw/data_sample_v1.json` benchmark is a development dataset. Its source documentation states that `OrderId`, `OrderNo` and item `Code` values are masked and that no PII is included.

Never commit production data, unmasked data, confidential or restricted data, PII, credentials, passwords, API keys, tokens, private keys or other secrets. Do not add any dataset that the team is not authorised to place in this repository.

## Packing rules that must not be ignored

The reference data includes these core constraints:

1. Item length, width and height in mm.
2. Item weight in kg and carton `MaxWeight`.
3. Item quantity.
4. `VerticalRotation`. A value of `0` means the item must remain upright and cannot be packed lying down.
5. `BinMaxFillCheckMinItemQty`. Orders at or below this item count may use up to 100 percent volumetric fill. The configured `BinMaxFillPct` applies only above the threshold.
6. `BinMaxFillPct`, which should remain configurable.
7. `BinBuffer`, which reserves internal carton clearance and should remain configurable.
8. `OptimizationMode = bins_number`, meaning the supplied cases optimize for number of cartons.

Do not silently remove, reinterpret or hard code configurable rules without documenting the decision.

## Reference dataset limitations

The supplied dataset contains 2,000 successful and feasible cases. `NotPackedItems` is empty for every supplied record.

Do not treat this as a complete validation suite. Create deliberate edge and failure cases for conditions such as impossible dimensions, overweight items, upright only restrictions, fill cap boundaries and multi carton orders.

## Evaluation

When comparing a new solver with the reference service, separate these concerns:

1. Feasibility and whether every required item is assigned.
2. Constraint compliance.
3. Number and type of cartons selected.
4. Volumetric utilization.
5. Runtime or latency.

Do not assume a result is wrong only because its geometric arrangement or carton combination differs from the reference output. Multiple valid packing solutions may exist.

## Repository safety

Use a separate branch for normal changes and open a pull request. Do not overwrite unrelated teammate work. Do not rewrite Git history or force push unless explicitly approved.

Do not claim code, tests, solver performance or benchmark results were executed unless they were actually run or checked.

Human teammates remain responsible for reviewing and understanding AI assisted work before submission or deployment.
